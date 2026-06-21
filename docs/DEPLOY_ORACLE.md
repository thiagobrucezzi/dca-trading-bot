# Deploy en Oracle Cloud (Always Free) — Paso a Paso

Guía para correr el bot 24/7 gratis en una VM ARM Ampere A1 de Oracle.
Region recomendada: **Japan East (Tokyo)** o **Osaka/Singapur** si no hay cupo ARM.

> ⚠️ Mientras estemos en Fase 0-2 (backtest / paper trading) la VM **no toca
> plata real**. Recién en Fase 3 se cargan las API keys de Binance.

---

## 1. Crear la VM (Compute Instance)

En la consola de Oracle: **Menu → Compute → Instances → Create Instance**

| Campo | Valor |
|---|---|
| Name | `crypto-bot` |
| Image | **Canonical Ubuntu 24.04** |
| Shape | **VM.Standard.A1.Flex** (Always Free) |
| OCPUs / RAM | 1 OCPU / 6 GB (sobra; el free tier da hasta 4/24) |
| SSH keys | **Generar par nuevo** y descargar la clave privada |

Si sale **"Out of capacity"** del ARM: probá otra Availability Domain (AD-1/2/3),
otra región (Osaka), o reintentá más tarde (el free tier ARM es muy demandado).

Anotá la **IP pública** que aparece cuando la instancia queda en estado *Running*.

---

## 2. Conectarte por SSH (desde tu Mac)

```bash
# permisos correctos a la clave descargada
chmod 600 ~/Downloads/ssh-key-*.key

# conectar (usuario por defecto en Ubuntu de Oracle = ubuntu)
ssh -i ~/Downloads/ssh-key-*.key ubuntu@TU_IP_PUBLICA
```

Si da timeout: en la consola de Oracle, **VCN → Security List → Ingress Rules**,
asegurate de que el puerto 22 (SSH) esté permitido desde `0.0.0.0/0`.
(No necesitamos abrir ningún otro puerto: el bot hace conexiones *salientes*, nadie
se conecta *hacia* el bot.)

---

## 3. Preparar el servidor

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.12 python3.12-venv git
```

(Ubuntu 24.04 trae Python 3.12, perfecto. No hace falta 3.14.)

---

## 4. Traer el código

**Opción A — git (recomendada, una vez que el repo esté en GitHub):**
```bash
git clone https://github.com/TU_USUARIO/crypto-trading-bot.git
cd crypto-trading-bot
```

**Opción B — copiarlo desde tu Mac sin GitHub:**
```bash
# (corriendo ESTE comando en tu Mac, no en la VM)
scp -i ~/Downloads/ssh-key-*.key -r ~/Git/crypto-trading-bot \
    ubuntu@TU_IP_PUBLICA:~/
```

---

## 5. Instalar dependencias

```bash
cd ~/crypto-trading-bot
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Verificá que todo corre:
```bash
.venv/bin/python scripts/download_data.py
.venv/bin/python scripts/daily_report.py     # imprime la señal de hoy
```

---

## 6. Configurar secretos (.env)

```bash
cp .env.example .env
nano .env     # pegar TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID
```

Para cargar el `.env` automáticamente, los scripts ya leen de variables de
entorno. En el cron/servicio las inyectamos (paso 7-8).

---

## 7. Reporte diario automático (cron)

Lo más simple para empezar: un cron que manda el reporte de señales 1x/día.

```bash
crontab -e
```
Agregar (DCA todos los días a las 09:05 — solo aporta cuando toca el período;
y un reporte de estado los lunes 09:10):
```cron
5  9 * * *  cd /home/ubuntu/dca-trading-bot && set -a && . ./.env && set +a && timeout 300 .venv/bin/python scripts/run_dca.py    >> bot.log 2>&1
10 9 * * 1  cd /home/ubuntu/dca-trading-bot && set -a && . ./.env && set +a && timeout 300 .venv/bin/python scripts/dca_status.py >> bot.log 2>&1
```

`run_dca.py` es idempotente: lo corrés todos los días pero solo ejecuta el aporte
1x por período (mes/semana según `DCA_FREQUENCY`). Empezá con `BOT_MODE=simulate`,
después `testnet`. **Esto es la Fase 2 (paper trading).**

---

## 8. Bot 24/7 como servicio (systemd) — Fase 3+ (un bot con edge, si aparece)

Si algún día una estrategia del `research/` le gana al DCA en validación OOS y
querés correrla en vivo con un loop continuo, en vez de cron usás un servicio
que se reinicia solo si se cae:

```bash
sudo nano /etc/systemd/system/crypto-bot.service
```
```ini
[Unit]
Description=Crypto Trading Bot
After=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/crypto-trading-bot
EnvironmentFile=/home/ubuntu/crypto-trading-bot/.env
ExecStart=/home/ubuntu/crypto-trading-bot/.venv/bin/python -m src.live_runner
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now crypto-bot
sudo systemctl status crypto-bot      # ver estado
journalctl -u crypto-bot -f           # ver logs en vivo
```
(`src/live_runner.py` lo construimos en Fase 2.)

---

## 9. Mantenimiento

```bash
# ver logs del reporte diario
tail -f ~/crypto-trading-bot/bot.log

# actualizar el código
cd ~/crypto-trading-bot && git pull && sudo systemctl restart crypto-bot

# uso de recursos
htop        # (sudo apt install htop)
```

---

## Checklist de seguridad 🔒

- [ ] La clave SSH privada **nunca** se sube a GitHub ni se comparte.
- [ ] `.env` está en `.gitignore` (ya lo está). Nunca commitearlo.
- [ ] API keys de Binance (Fase 3): permisos **solo Spot Trading**, **retiros DESHABILITADOS**.
- [ ] Restringir las API keys de Binance a la **IP pública de la VM** (whitelist).
- [ ] Mantener Ubuntu actualizado (`sudo apt upgrade` periódico).
- [ ] No abrir puertos de entrada salvo SSH (22).
```
