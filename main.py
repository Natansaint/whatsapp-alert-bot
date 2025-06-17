import os
import requests
import time
from twilio.rest import Client
from flask import Flask

# Carrega variáveis de ambiente
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM")
TWILIO_WHATSAPP_TO = os.getenv("TWILIO_WHATSAPP_TO")
BETSAPI_TOKEN = os.getenv("BETSAPI_TOKEN")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

app = Flask(__name__)

# Rota simples para garantir que o servidor Flask esteja funcionando
@app.route('/')
def health_check():
    return "Servidor funcionando!"

def send_whatsapp_alert(message):
    client.messages.create(
        from_=TWILIO_WHATSAPP_FROM,
        body=message,
        to=TWILIO_WHATSAPP_TO
    )


def get_live_matches():
    url = f"https://api.betsapi.com/v1/bet365/inplay?token={BETSAPI_TOKEN}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get("results", [])
    return []


def analyze_match(match):
    match_id = match.get("id")
    odds_url = f"https://api.betsapi.com/v3/bet365/prematch?token={BETSAPI_TOKEN}&FI={match_id}"
    stats_url = f"https://api.betsapi.com/v1/event/view?token={BETSAPI_TOKEN}&EID={match_id}"

    odds_response = requests.get(odds_url)
    stats_response = requests.get(stats_url)

    if odds_response.status_code == 200 and stats_response.status_code == 200:
        odds_data = odds_response.json()
        stats_data = stats_response.json()

        # Checa odds acima de 1.60
        goal_odds_ok = "goal" in str(odds_data).lower() and "1.6" in str(odds_data)
        corner_odds_ok = "corner" in str(odds_data).lower() and "1.6" in str(odds_data)

        # Sinais de pressão (exemplo: ataques perigosos ou finalizações)
        pressure = False
        events = stats_data.get("results", {}).get("event", {}).get("stats", {})
        if events:
            attacks = int(events.get("dangerous_attacks_home", 0)) + int(events.get("dangerous_attacks_away", 0))
            shots = int(events.get("on_target_home", 0)) + int(events.get("on_target_away", 0))
            pressure = attacks >= 10 or shots >= 5

        if (goal_odds_ok or corner_odds_ok) and pressure:
            team1 = match.get("home")
            team2 = match.get("away")
            return f"⚽ Pressão em {team1} x {team2}! Odds de gols/escanteios acima de 1.60 e pressão detectada."

    return None


def main_loop():
    while True:
        try:
            matches = get_live_matches()
            for match in matches:
                alert = analyze_match(match)
                if alert:
                    send_whatsapp_alert(alert)
            print("🔄 Rodada finalizada. Aguardando 7 minutos...")
            time.sleep(420)  # 7 minutos
        except Exception as e:
            print(f"Erro: {e}")
            time.sleep(420)

# Executa o loop principal em segundo plano
import threading
threading.Thread(target=main_loop, daemon=True).start()

# Rodando o servidor Flask na porta fornecida pela plataforma de nuvem (ex: Render.com)
if __name__ == "__main__":
    # A variável 'PORT' é definida pela nuvem
    port = int(os.environ.get("PORT", 5000))  # Padrão para 5000 caso a variável não esteja definida
    app.run(host="0.0.0.0", port=port)
