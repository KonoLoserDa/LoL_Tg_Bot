import os
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

load_dotenv()
RIOT_API_KEY = os.getenv("RIOT_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

REGION_ROUTING = {
    'euw1': 'europe',
    'na1': 'americas',
    'kr': 'asia',
    # puoi aggiungere altre regioni
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ciao! Inviami il summoner name e la regione nel formato:
/nome regione
Esempio: /faker euw1")

async def get_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Formato non valido. Usa: /nome regione (es. /faker euw1)")
        return

    summoner_name = context.args[0]
    region = context.args[1].lower()

    url = f"https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-name/{summoner_name}"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        await update.message.reply_text("Errore nel trovare il summoner.")
        return

    summoner = res.json()
    puuid = summoner["puuid"]

    routing = REGION_ROUTING.get(region, 'europe')
    match_url = f"https://{routing}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=10"
    match_res = requests.get(match_url, headers=headers)
    match_ids = match_res.json()

    result = f"Ultime 10 partite di {summoner_name}:
"

    for match_id in match_ids:
        match_data_url = f"https://{routing}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        match_data = requests.get(match_data_url, headers=headers).json()

        participants = match_data["info"]["participants"]
        player_data = next(p for p in participants if p["puuid"] == puuid)

        win = "VITTORIA" if player_data["win"] else "SCONFITTA"
        champ = player_data["championName"]
        kills = player_data["kills"]
        deaths = player_data["deaths"]
        assists = player_data["assists"]

        result += f"{champ}: {kills}/{deaths}/{assists} - {win}\n"

    await update.message.reply_text(result)

app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("nome", get_matches))
app.run_polling()
