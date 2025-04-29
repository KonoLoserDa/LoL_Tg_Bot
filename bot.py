import os
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

load_dotenv()

RIOT_API_KEY = os.getenv("RIOT_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Mapping per platform routing in match-v5
REGION_ROUTING = {
    "euw1": "europe",
    "eun1": "europe",
    "tr1": "europe",
    "ru": "europe",
    "na1": "americas",
    "br1": "americas",
    "la1": "americas",
    "la2": "americas",
    "oc1": "americas",
    "kr": "asia",
    "jp1": "asia"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Ciao! Usa il comando /risultati GAME_NAME#TAG_LINE (es. /risultati Caps#EUW)")

async def get_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if len(context.args) != 1:
        await update.message.reply_text("Formato non valido. Usa: /risultati GAME_NAME#TAG_LINE (es. /risultati Caps#EUW)")
        return

    riot_id_full = context.args[0]
    
    if "#" not in riot_id_full:
        await update.message.reply_text("Formato Riot ID non valido. Usa GAME_NAME#TAG_LINE (es. /risultati Caps#EUW)")
        return
    
    # Separare il game_name e il tag_line
    game_name, tag_line = riot_id_full.split("#")
    tag_line = tag_line.upper()  # Per uniformare

    riot_id = f"{game_name}#{tag_line}"

    print(f"Richiesta per Riot ID: '{riot_id}'")

    headers = {"X-Riot-Token": RIOT_API_KEY}
    account_url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"

    try:
        res = requests.get(account_url, headers=headers)
        print("Status code account API:", res.status_code)
        if res.status_code == 404:
            await update.message.reply_text("Riot ID non trovato.")
            return
        res.raise_for_status()
        data = res.json()
        puuid = data["puuid"]
    except Exception as e:
        print("Errore nella richiesta Riot ID:", e)
        await update.message.reply_text("Errore nel recuperare il Riot ID.")
        return

    # Ottieni regione a partire dal tag_line
    # Per semplicità usiamo hardcoded mapping: puoi migliorarlo se vuoi
    inferred_region = None
    for short, platform in REGION_ROUTING.items():
        if tag_line.lower() in short:
            inferred_region = short
            platform_routing = platform
            break

    # fallback: europe
    if not inferred_region:
        platform_routing = "europe"

    matchlist_url = f"https://{platform_routing}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=5"  # Qui cambio il numero delle partite da 10 a 5
    try:
        match_ids = requests.get(matchlist_url, headers=headers).json()
    except Exception as e:
        print("Errore nel recuperare le partite:", e)
        await update.message.reply_text("Errore nel recuperare le partite.")
        return

    result = f"Ultime 5 partite di {riot_id}:\n"  # Modifica il testo di risposta
    for match_id in match_ids:
        match_url = f"https://{platform_routing}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        match_data = requests.get(match_url, headers=headers).json()
        try:
            participants = match_data["info"]["participants"]
            player = next(p for p in participants if p["puuid"] == puuid)
            win = "VITTORIA" if player["win"] else "SCONFITTA"
            result += f"- {player['championName']} | {win} | {player['kills']}/{player['deaths']}/{player['assists']}\n"
        except Exception as e:
            print(f"Errore nella partita {match_id}:", e)
            continue

    await update.message.reply_text(result)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("risultati", get_matches))
    print("Bot avviato.")
    app.run_polling()
