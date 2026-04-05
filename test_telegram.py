import requests

TOKEN = "8307807433:AAHiqxHi1YUdwuBqIURxrr-Cl-CCBuZU6ro"
ID_CHAT = "6943567087"
mensaje = "🧪 Prueba de mensaje desde BVC Master Trader"

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
response = requests.post(url, data={
    "chat_id": ID_CHAT, 
    "text": mensaje, 
    "parse_mode": "Markdown"
}, timeout=5)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
