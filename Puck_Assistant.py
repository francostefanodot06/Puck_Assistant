from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import subprocess
import requests
import os
import sys
import glob
import json

# --- AUTODETECCIÓN DE ENTORNO GRÁFICO (WAYLAND/KDE) ---
# Necesario para que FastAPI (corriendo en background) pueda lanzar apps en el escritorio del usuario
sockets = [s for s in glob.glob("/run/user/1000/wayland-*") if not s.endswith(".lock")]
if sockets:
    sockets.sort(key=os.path.getmtime, reverse=True)
    os.environ["WAYLAND_DISPLAY"] = os.path.basename(sockets[0])

os.environ["DISPLAY"] = ":0"
os.environ["XDG_RUNTIME_DIR"] = "/run/user/1000"
os.environ["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=/run/user/1000/bus"
# -------------------------------------------------------

app = FastAPI(title="Puck - AI SysAdmin Middleware")

# LISTA BLANCA DE COMANDOS PERMITIDOS (Seguridad)
COMANDOS_PERMITIDOS = {
    "discord": "discord",
    "terminal": "konsole",
    "brave": "brave",
    "feishin": "feishin",
    "steam": "steam",
    "dolphin": "dolphin",
    "zen browser": "zen browser",
    "heroic games": "heroic games"
}

# ==========================================
# MÓDULO 1: CONTROL DE ESCRITORIO (DESKTOP)
# ==========================================

@app.post("/ejecutar/{comando}")
def ejecutar_comando(comando: str):
    comando_limpio = comando.lower()

    if comando_limpio not in COMANDOS_PERMITIDOS:
        raise HTTPException(status_code=403, detail="Comando no autorizado por el SysAdmin.")

    try:
        subprocess.Popen([COMANDOS_PERMITIDOS[comando_limpio]])
        return {"status": "success", "mensaje": f"Se abrió {comando_limpio} correctamente."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cerrar/{comando}")
def cerrar_comando(comando: str):
    comando_limpio = comando.lower()

    if comando_limpio not in COMANDOS_PERMITIDOS:
        raise HTTPException(status_code=403, detail="Comando no autorizado por el SysAdmin.")

    try:
        subprocess.run(["pkill", "-f", COMANDOS_PERMITIDOS[comando_limpio]], check=True)
        return {"status": "success", "mensaje": f"Se cerró {comando_limpio} correctamente."}
    except subprocess.CalledProcessError:
        raise HTTPException(status_code=404, detail="El programa no estaba en ejecución.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/media/{accion}")
def controlar_media(accion: str):
    acciones_validas = {"play", "pause", "play-pause", "next", "previous", "stop", "volume-up", "volume-down", "feishin-up", "feishin-down"}

    if accion not in acciones_validas:
        raise HTTPException(status_code=400, detail="Acción multimedia no válida.")

    try:
        if accion in ["volume-up", "volume-down"]:
            delta = "5%+" if accion == "volume-up" else "5%-"
            subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", delta], check=True)
        elif accion in ["feishin-up", "feishin-down"]:
            delta = "+5%" if accion == "feishin-up" else "-5%"
            outputs = subprocess.check_output("pactl list sink-inputs short", shell=True).decode()
            for line in outputs.splitlines():
                parts = line.split()
                if parts:
                    input_id = parts[0]
                    info = subprocess.check_output("pactl list sink-inputs", shell=True).decode()
                    if f"Sink Input #{input_id}" in info and "feishin" in info.lower():
                        subprocess.run(["pactl", "set-sink-input-volume", input_id, delta], check=True)
        else:
            subprocess.run(["playerctl", accion], check=True)

        return {"status": "success", "mensaje": f"Acción multimedia ejecutada: {accion}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# MÓDULO 2: INFRAESTRUCTURA Y OBSERVABILIDAD
# ==========================================

@app.get("/proxmox/estado")
def estado_proxmox():
    # Credenciales cargadas desde variables de entorno para seguridad
    TOKEN_ID = os.getenv("PROXMOX_TOKEN_ID", "root@pam!agente-ia")
    SECRET = os.getenv("PROXMOX_SECRET", "")
    PROXMOX_URL = os.getenv("PROXMOX_URL", "https://tu-dominio-proxmox.duckdns.org")
    NODE_NAME = os.getenv("PROXMOX_NODE", "frankdevlab")

    headers = {"Authorization": f"PVEAPIToken={TOKEN_ID}={SECRET}"}

    try:
        url_status = f"{PROXMOX_URL}/api2/json/nodes/{NODE_NAME}/status"
        res_status = requests.get(url_status, headers=headers, timeout=5)
        res_status.raise_for_status()
        data = res_status.json()["data"]

        cpu_usage = round(data["cpu"] * 100, 1)
        ram_usage = round((data["memory"]["used"] / data["memory"]["total"]) * 100, 1)
        uptime_horas = round(data["uptime"] / 3600, 1)

        url_storage = f"{PROXMOX_URL}/api2/json/nodes/{NODE_NAME}/storage"
        res_storage = requests.get(url_storage, headers=headers, timeout=5)
        res_storage.raise_for_status()
        storages = res_storage.json()["data"]

        info_discos = ""
        for disco in storages:
            if disco.get("active") == 1:
                nombre = disco["storage"]
                total_gb = round(disco["total"] / (1024**3), 1)
                usado_gb = round(disco["used"] / (1024**3), 1)
                porcentaje = round((usado_gb / total_gb) * 100, 1)
                info_discos += f"- Disco '{nombre}': {usado_gb}GB usados de {total_gb}GB ({porcentaje}%).\n"

        mensaje = (
            f"Reporte del homelab:\n"
            f"CPU: {cpu_usage}%\n"
            f"RAM: {ram_usage}%\n"
            f"Uptime: {uptime_horas} horas.\n"
            f"Almacenamiento:\n{info_discos}"
        )

        return {"status": "success", "mensaje": mensaje}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/grafana/estado")
def estado_grafana():
    GRAFANA_URL = os.getenv("GRAFANA_API_URL", "http://192.168.0.x:3000/api/alertmanager/grafana/api/v2/alerts")
    GRAFANA_TOKEN = os.getenv("GRAFANA_TOKEN", "")

    headers = {"Authorization": f"Bearer {GRAFANA_TOKEN}"}

    try:
        respuesta = requests.get(GRAFANA_URL, headers=headers, timeout=5)
        respuesta.raise_for_status()
        alertas = respuesta.json()

        # Filtramos solo las alertas que están fallando ("firing")
        alertas_activas = [alerta for alerta in alertas if alerta.get("status", {}).get("state") == "firing"]

        if not alertas_activas:
            return {"status": "success", "mensaje": "He revisado los paneles de Grafana, señor. Todos los sistemas están en verde y no hay alertas activas."}

        resumen = "He detectado las siguientes alertas activas en Grafana:\n"
        for alerta in alertas_activas:
            nombre = alerta.get("labels", {}).get("alertname", "Alerta técnica")
            instancia = alerta.get("labels", {}).get("instance", "Desconocida")
            resumen += f"- {nombre} en la instancia {instancia}\n"

        return {"status": "success", "mensaje": resumen}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No pude comunicarme con Grafana: {str(e)}")

# ==========================================
# MÓDULO 3: IA & WEBHOOKS (Alertas Proactivas)
# ==========================================

@app.post("/alertas/discord")
def alerta_discord(payload: dict):
    DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
    OLLAMA_URL = os.getenv("OLLAMA_GENERATE_URL", "http://127.0.0.1:11434/api/generate")

    alerta_cruda = json.dumps(payload)

    prompt = f"""Eres Puck, el SysAdmin de la infraestructura de Franco.
    Has recibido esta alerta técnica de Grafana: {alerta_cruda}.
    Resume el problema en español de forma natural, directa y con tono de mayordomo (máximo 3 líneas).
    No incluyas código JSON, solo el reporte de la situación."""

    try:
        res_ollama = requests.post(
            OLLAMA_URL,
            json={
                "model": "qwen3:14b",
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )
        if res_ollama.status_code == 200:
            mensaje_ia = res_ollama.json().get("response", "").strip()
        else:
            mensaje_ia = "Señor, recibimos una alerta, pero mi módulo de procesamiento de lenguaje falló. Revise Grafana."
    except Exception as e:
        mensaje_ia = f"Señor, no me pude conectar a mi cerebro local (Ollama). Error: {str(e)}"

    data = {
        "content": f"🤖 **Puck (SysAdmin):**\n{mensaje_ia}"
    }

    try:
        requests.post(DISCORD_WEBHOOK_URL, json=data)
        return {"status": "success", "mensaje": "Alerta procesada por IA y enviada."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# MÓDULO 4: TEXT TO SPEECH (Piper TTS)
# ==========================================

class TTSRequest(BaseModel):
    input: str
    model: str = "piper"
    voice: str = "davefx"

@app.post("/v1/audio/speech")
def motor_de_voz(request: TTSRequest):
    archivo_salida = "/tmp/respuesta_agente.wav"
    texto_limpio = request.input.replace("'", "")

    diccionario_voces = {
        "puck": "es_ES-davefx-medium.onnx",
        "cortana": "es_MX-cortana-19669-epoch-high.onnx",
        "gevy": "es_MX-gevy-10196-epoch-high.onnx",
        "claude": "es_MX-claude-14947-epoch-high.onnx",
        "nova": "es_MX-cortana-19669-epoch-high.onnx",
        "shimmer": "es_MX-gevy-10196-epoch-high.onnx"
    }

    voz_solicitada = request.voice.lower()

    sys.stderr.write(f"\n\n---> OPEN WEBUI PIDIÓ LA VOZ: '{voz_solicitada}' <---\n\n")
    sys.stderr.flush()

    modelo_elegido = diccionario_voces.get(voz_solicitada, "es_ES-davefx-medium.onnx")

    # Rutas locales absolutas a los binarios de Piper
    cmd = f"echo '{texto_limpio}' | /mnt/disk2/agente_voces/piper/piper -m /mnt/disk2/agente_voces/modelos/{modelo_elegido} --output_file {archivo_salida}"

    try:
        subprocess.run(cmd, shell=True, check=True)
        return FileResponse(archivo_salida, media_type="audio/wav")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
