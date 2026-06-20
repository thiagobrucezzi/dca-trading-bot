"""Prueba la conexion con Telegram y ayuda a obtener tu CHAT_ID.

Uso:
  1. Habla con @BotFather en Telegram -> /newbot -> copia el token.
  2. export TELEGRAM_BOT_TOKEN="..."  (o ponelo en .env)
  3. Mandale CUALQUIER mensaje a tu bot nuevo desde tu Telegram.
  4. Corre este script: te muestra tu CHAT_ID y manda un mensaje de prueba.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.notifier import TelegramNotifier

token = os.environ.get("TELEGRAM_BOT_TOKEN")
if not token:
    print("Falta TELEGRAM_BOT_TOKEN. export TELEGRAM_BOT_TOKEN='...' y reintenta.")
    sys.exit(1)

chat_id = os.environ.get("TELEGRAM_CHAT_ID")
if not chat_id:
    print("Buscando tu CHAT_ID (mandale un mensaje al bot primero)...")
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    with urllib.request.urlopen(url, timeout=15) as r:
        data = json.loads(r.read().decode())
    ids = {u["message"]["chat"]["id"] for u in data.get("result", []) if "message" in u}
    if not ids:
        print("No encontre mensajes. Mandale algo al bot desde Telegram y reintenta.")
        sys.exit(1)
    print(f"CHAT_ID(s) encontrados: {ids}")
    print("Agregalos a .env como TELEGRAM_CHAT_ID y reintenta para probar el envio.")
    sys.exit(0)

n = TelegramNotifier(token, chat_id)
res = n.send("✅ <b>Bot conectado.</b> Telegram funcionando correctamente.")
print("Enviado:", res is not None and res.get("ok"))
