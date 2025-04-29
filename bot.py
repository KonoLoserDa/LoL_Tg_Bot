import os
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

load_dotenv()

RIOT_API_KEY = os.getenv("RIOT_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

REGION_ROUTING = {
    "europe": "europe.api.riotgames.com",
    "americas": "americas.api.riotgames.com",
    "asia": "asia.api.riotgames.com"
}

GAME_MODE_MAP = {
    "CLASSIC": "Ranked/Normal",
    "ARAM": "ARAM",
    "URF": "URF",
    "PRACTICETOOL": "Practice Tool",
    "ONEFORALL": "One for All",
    "CHERRY": "Arena",
    "TUTORIAL_MODULE_1": "Tutorial",
    "TUTORIAL_MODULE_2": "Tutorial",
    "TUTORIAL_MODULE_3": "Tutorial",
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Hi! Use the command /games GAME_NAME#TAG_LINE (es. /games Fusco#Euwz)")

async def get_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if len(context.args) != 1:
        await update.message.reply_text("Invalid format. Use: /games GAME_NAME#TAG_LINE (es. /games Fusco#Euwz)")
        return

    riot_id_full = context.args[0]
    
    if "#" not in riot_id_full:
        await update.message.reply_text("Riot ID format invalid. Use GAME_NAME#TAG_LINE (es. /games Fusco#Euwz)")
        return
    
    game_name, tag_line = riot_id_full.split("#")
    tag_line = tag_line.upper()
    riot_id = f"{game_name}#{tag_line}"

    print(f"Requests for Riot ID: '{riot_id}'")

    headers = {"X-Riot-Token": RIOT_API_KEY}

    # Cycles global regions (europe, americas, asia)
    for global_region, region_url in REGION_ROUTING.items():
        account_url = f"https://{region_url}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"

        try:
            res = requests.get(account_url, headers=headers)
            print(f"Status code for region {global_region}: {res.status_code}")
            if res.status_code == 200:
                data = res.json()
                puuid = data["puuid"]
                platform_routing = global_region  # Assigns the global region to the platform routing
                break
        except Exception as e:
            print(f"Error for region {global_region}: {e}")
            continue
    else:
        await update.message.reply_text("Riot ID not found in any region.")
        return

    # Finding matches
    matchlist_url = f"https://{region_url}/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=5"
    try:
        match_ids = requests.get(matchlist_url, headers=headers).json()
    except Exception as e:
        print("Error in finding the games:", e)
        await update.message.reply_text("Error in finding the games.")
        return

    result = f"🎮 Last 5 games of {riot_id}:\n"
    result += "```\n"  # Start of monospace block

    result += f"{'Champion':<12}\t{'Result':<10}\t{'K/D/A':<9}\t{'Time':<6}\t{'Mode'}\n"
    result += f"{'-'*54}\n"

    for match_id in match_ids:
        match_url = f"https://{region_url}/lol/match/v5/matches/{match_id}"
        match_data = requests.get(match_url, headers=headers).json()
        try:
            info = match_data["info"]
            participants = info["participants"]
            player = next(p for p in participants if p["puuid"] == puuid)
            win = "✅" if player["win"] else "❌"
            champ = player["championName"]
            kda = f"{player['kills']}/{player['deaths']}/{player['assists']}"
            duration = f"{int(info['gameDuration']) // 60}m"
            mode_raw = info["gameMode"]
            mode = GAME_MODE_MAP.get(mode_raw, mode_raw)

            result += f"{champ:<12} {win:<8} {kda:<9} {duration:<6} {mode}\n"
        except Exception as e:
            print(f"Error in the match {match_id}:", e)
            continue

    result += "```"  # End of monospace block
    await update.message.reply_text(result, parse_mode="Markdown")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("games", get_matches))
    print("Bot started.")
    app.run_polling()
