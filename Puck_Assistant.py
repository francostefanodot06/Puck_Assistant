from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import hmac
import json
import re
import subprocess
import requests
import os
import sys
import glob
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =============================================================================
# CONFIGURACIÓN DEL HOMELAB (COMPLETAR ANTES DE USAR)
# =============================================================================
PROXMOX_IP = "TU_PROXMOX_IP"
PROXMOX_NODO = "TU_NODO"
PROXMOX_TOKEN_ID = "root@pam!TU_TOKEN_ID"
PROXMOX_SECRET = "TU_PROXMOX_SECRET"

GRAFANA_IP = "TU_GRAFANA_IP"
GRAFANA_TOKEN = "TU_GRAFANA_TOKEN"

LOKI_URL = os.environ.get("LOKI_URL", "http://TU_LOKI_IP:3100")
LOKI_LABEL = os.environ.get("LOKI_LABEL", "container")

DISCORD_WEBHOOK_URL = "TU_DISCORD_WEBHOOK_URL"
OLLAMA_IP = "TU_OLLAMA_IP"

RUTA_PIPER = "/mnt/disk2/agente_voces/piper"
RUTA_MODELOS = "/mnt/disk2/agente_voces/modelos"

UMBRAL_VIGILAR = 80
UMBRAL_CRITICO = 90
# =============================================================================

sockets = [s for s in glob.glob("/run/user/1000/wayland-*") if not s.endswith(".lock")]
if sockets:
    sockets.sort(key=os.path.getmtime, reverse=True)
    os.environ["WAYLAND_DISPLAY"] = os.path.basename(sockets[0])

os.environ["DISPLAY"] = ":0"
os.environ["XDG_RUNTIME_DIR"] = "/run/user/1000"
os.environ["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=/run/user/1000/bus"

API_KEY = os.environ.get("PUCK_API_KEY", "")
if not API_KEY:
    print("!!! PUCK_API_KEY no está definida: todas las rutas van a responder 401 !!!", file=sys.stderr)

def auth(authorization: str = Header(default="")):
    esperado = f"Bearer {API_KEY}".encode()
    if not API_KEY or not hmac.compare_digest(authorization.encode(), esperado):
        raise HTTPException(status_code=401, detail="No autorizado")

app = FastAPI(dependencies=[Depends(auth)])

COMANDOS_PERMITIDOS = {
    "discord": "discord",
    "terminal": "konsole",
    "brave": "brave",
    "feishin": "feishin",
    "steam": "steam",
    "dolphin": "dolphin",
    "zen": "zen-browser",
    "zen browser": "zen-browser",
    "heroic": "heroic",
    "heroic games": "heroic",
}

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

@app.post("/media/{accion}")
def controlar_media(accion: str):
    acciones_validas = {"play", "pause", "play-pause", "next", "previous", "stop", "volume-up", "volume-down"}
    if accion not in acciones_validas:
        raise HTTPException(status_code=400, detail="Acción multimedia no válida.")
    try:
        if accion in ["volume-up", "volume-down"]:
            delta = "+5%" if accion == "volume-up" else "-5%"
            outputs = subprocess.check_output("pactl list sink-inputs short", shell=True).decode()
            encontrado = False
            for line in outputs.splitlines():
                parts = line.split()
                if parts:
                    input_id = parts[0]
                    info = subprocess.check_output("pactl list sink-inputs", shell=True).decode()
                    if f"Sink Input #{input_id}" in info and "mpv" in info.lower():
                        subprocess.run(["pactl", "set-sink-input-volume", input_id, delta], check=True)
                        encontrado = True
            if not encontrado:
                return {"status": "warning", "mensaje": "No se encontró un stream de mpv activo para regular el volumen."}
        else:
            subprocess.run(["playerctl", "--player=mpv", accion], check=True)
        return {"status": "success", "mensaje": f"Acción multimedia ejecutada: {accion}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cerrar/{comando}")
def cerrar_comando(comando: str):
    comando_limpio = comando.lower()
    if comando_limpio not in COMANDOS_PERMITIDOS:
        raise HTTPException(status_code=403, detail="Comando no autorizado.")
    try:
        subprocess.run(["pkill", "-f", COMANDOS_PERMITIDOS[comando_limpio]], check=True)
        return {"status": "success", "mensaje": f"Se cerró {comando_limpio} correctamente."}
    except subprocess.CalledProcessError:
        raise HTTPException(status_code=404, detail="El programa no estaba en ejecución.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _nivel(pct: float) -> int:
    return 2 if pct >= UMBRAL_CRITICO else 1 if pct >= UMBRAL_VIGILAR else 0

_ETIQUETA = {0: "", 1: " [a vigilar]", 2: " [CRÍTICO]"}

def _prox_get(path: str):
    r = requests.get(
        f"https://{PROXMOX_IP}:8006/api2/json{path}",
        headers={"Authorization": f"PVEAPIToken={PROXMOX_TOKEN_ID}={PROXMOX_SECRET}"},
        timeout=8,
        verify=False,
    )
    r.raise_for_status()
    return r.json()["data"]

def _prox_estado() -> dict:
    data = _prox_get(f"/nodes/{PROXMOX_NODO}/status")
    discos = []
    for d in _prox_get(f"/nodes/{PROXMOX_NODO}/storage"):
        if d.get("active") == 1 and d.get("total"):
            total = round(d["total"] / (1024**3), 1)
            usado = round(d["used"] / (1024**3), 1)
            discos.append({"nombre": d["storage"], "usado": usado, "total": total, "pct": round(usado / total * 100, 1)})
    return {
        "cpu": round(data["cpu"] * 100, 1),
        "ram": round(data["memory"]["used"] / data["memory"]["total"] * 100, 1),
        "uptime": round(data["uptime"] / 3600, 1),
        "discos": discos,
    }

def _prox_vms() -> list:
    out = []
    for tipo, ruta in (("VM", "qemu"), ("CT", "lxc")):
        for v in _prox_get(f"/nodes/{PROXMOX_NODO}/{ruta}"):
            maxmem = v.get("maxmem") or 0
            out.append({
                "id": v.get("vmid", 0),
                "nombre": v.get("name", "?"),
                "tipo": tipo,
                "estado": v.get("status", "?"),
                "cpu": round(v.get("cpu", 0) * 100, 1),
                "ram": round(v.get("mem", 0) / maxmem * 100, 1) if maxmem else 0.0,
            })
    return sorted(out, key=lambda x: x["id"])

@app.get("/proxmox/estado")
def estado_proxmox():
    try:
        p = _prox_estado()
        discos = "".join(f"- Disco '{d['nombre']}': {d['usado']}GB usados de {d['total']}GB ({d['pct']}%){_ETIQUETA[_nivel(d['pct'])]}.\n" for d in p["discos"])
        mensaje = f"Reporte del homelab:\nCPU: {p['cpu']}%{_ETIQUETA[_nivel(p['cpu'])]}\nRAM: {p['ram']}%{_ETIQUETA[_nivel(p['ram'])]}\nUptime: {p['uptime']} horas.\nAlmacenamiento:\n{discos}(Las etiquetas [a vigilar] y [CRÍTICO] vienen calculadas: a vigilar desde {UMBRAL_VIGILAR}%, crítico desde {UMBRAL_CRITICO}%. Sin etiqueta = normal.)"
        return {"status": "success", "mensaje": mensaje}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/proxmox/vms")
def estado_vms():
    try:
        vms = _prox_vms()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {e}")
    if not vms:
        return {"mensaje": "Proxmox no tiene máquinas."}
    corriendo = [v for v in vms if v["estado"] == "running"]
    detenidas = [v for v in vms if v["estado"] != "running"]
    lineas = [f"{len(corriendo)} en ejecución y {len(detenidas)} detenidas (de {len(vms)})."]
    for v in corriendo[:40]: lineas.append(f"- {v['id']} {v['nombre']} ({v['tipo']}): en ejecución, CPU {v['cpu']}%, RAM {v['ram']}%")
    for v in detenidas[:40]: lineas.append(f"- {v['id']} {v['nombre']} ({v['tipo']}): {v['estado']}")
    return {"mensaje": "\n".join(lineas)}

@app.post("/alertas/discord")
def alerta_discord(payload: dict):
    alerta_cruda = json.dumps(payload)
    prompt = f"Eres Puck, el SysAdmin de la infraestructura. Has recibido esta alerta técnica de Grafana: {alerta_cruda}. Resume el problema en español de forma natural, directa y con tono de mayordomo (máximo 3 líneas). No incluyas código JSON, solo el reporte de la situación."
    try:
        res_ollama = requests.post(f"http://{OLLAMA_IP}:11434/api/generate", json={"model": "qwen3:14b", "prompt": prompt, "stream": False}, timeout=30)
        mensaje_ia = res_ollama.json().get("response", "").strip() if res_ollama.status_code == 200 else "Módulo de lenguaje falló."
    except Exception as e:
        mensaje_ia = f"Fallo Ollama: {str(e)}"
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": f"🤖 **Puck (SysAdmin):**\n{mensaje_ia}"}, timeout=10)
        return {"status": "success", "mensaje": "Alerta procesada."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class TTSRequest(BaseModel):
    input: str
    model: str = "piper"
    voice: str = "davefx"

@app.post("/v1/audio/speech")
def motor_de_voz(request: TTSRequest):
    archivo_salida = "/tmp/respuesta_agente.wav"
    texto_limpio = request.input.replace("'", "")
    diccionario_voces = {"puck": "es_ES-davefx-medium.onnx", "cortana": "es_MX-cortana-19669-epoch-high.onnx", "gevy": "es_MX-gevy-10196-epoch-high.onnx", "claude": "es_MX-claude-14947-epoch-high.onnx", "nova": "es_MX-cortana-19669-epoch-high.onnx", "shimmer": "es_MX-gevy-10196-epoch-high.onnx"}
    voz_solicitada = request.voice.lower()
    sys.stderr.write(f"\n\n---> OPEN WEBUI PIDIÓ LA VOZ: '{voz_solicitada}' <---\n\n")
    sys.stderr.flush()
    modelo_elegido = diccionario_voces.get(voz_solicitada, "es_ES-davefx-medium.onnx")
    cmd = f"echo '{texto_limpio}' | {RUTA_PIPER}/piper -m {RUTA_MODELOS}/{modelo_elegido} --output_file {archivo_salida}"
    try:
        subprocess.run(cmd, shell=True, check=True)
        return FileResponse(archivo_salida, media_type="audio/wav")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _grafana_firing() -> list:
    r = requests.get(
        f"http://{GRAFANA_IP}:3000/api/alertmanager/grafana/api/v2/alerts",
        headers={"Authorization": f"Bearer {GRAFANA_TOKEN}"},
        timeout=6,
    )
    r.raise_for_status()
    return [a for a in r.json() if a.get("status", {}).get("state") == "firing"]

@app.get("/grafana/estado")
def estado_grafana():
    try:
        alertas_activas = _grafana_firing()
        if not alertas_activas: return {"status": "success", "mensaje": "Paneles en verde y no hay alertas activas."}
        resumen = "He detectado las siguientes alertas activas en Grafana:\n"
        for alerta in alertas_activas: resumen += f"- {alerta.get('labels', {}).get('alertname', 'Alerta')} en instancia {alerta.get('labels', {}).get('instance', '?')}\n"
        return {"status": "success", "mensaje": resumen}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

LOKI_MAX_LINEAS = 40
LOKI_MAX_CHARS = 300
LOKI_REGEX_ERRORES = "(?i)error|fail|fatal|panic|exception|denied|timeout"
_SECRETOS = re.compile(r"(?i)(password|passwd|pwd|token|secret|api[_-]?key|authorization)(\"?\s*[:=]\s*\"?(?:Bearer\s+)?)[^\s\"&,;]+")

def _ocultar(linea: str) -> str: return _SECRETOS.sub(r"\1\2***", linea)
def _hora(ts: int) -> str: return datetime.fromtimestamp(ts / 1e9).strftime("%H:%M:%S")

def _loki_servicios() -> list:
    r = requests.get(f"{LOKI_URL}/loki/api/v1/label/{LOKI_LABEL}/values", timeout=10)
    r.raise_for_status()
    return r.json().get("data", [])

def _loki_consulta(servicio: str, minutos: int, solo_errores: bool, limite: int = LOKI_MAX_LINEAS) -> list:
    query = f'{{{LOKI_LABEL}="{servicio}"}}'
    if solo_errores: query += f' |~ "{LOKI_REGEX_ERRORES}"'
    fin = time.time_ns()
    r = requests.get(f"{LOKI_URL}/loki/api/v1/query_range", params={"query": query, "start": fin - minutos * 60 * 10**9, "end": fin, "limit": limite, "direction": "backward"}, timeout=15)
    r.raise_for_status()
    entradas = [(int(ts), linea) for stream in r.json().get("data", {}).get("result", []) for ts, linea in stream["values"]]
    entradas.sort(key=lambda x: x[0], reverse=True)
    return entradas[:limite][::-1]

@app.get("/loki/servicios")
def loki_servicios():
    try: return {"mensaje": ", ".join(sorted(_loki_servicios())) or "Loki no tiene servicios."}
    except requests.RequestException as e: raise HTTPException(status_code=502, detail=str(e))

@app.get("/loki/logs")
def loki_logs(servicio: str, minutos: int = 15, solo_errores: bool = True):
    minutos = max(1, min(minutos, 180))
    try:
        validos = _loki_servicios()
        if servicio not in validos: raise HTTPException(status_code=404, detail=f"Disponibles: {', '.join(sorted(validos))}")
        entradas = _loki_consulta(servicio, minutos, solo_errores)
    except requests.RequestException as e: raise HTTPException(status_code=502, detail=str(e))
    modo = "solo errores" if solo_errores else "todas las líneas"
    if not entradas: return {"mensaje": f"Sin logs de '{servicio}' ({modo})."}
    cuerpo = "\n".join(f"{_hora(ts)} {_ocultar(linea.strip())[:LOKI_MAX_CHARS]}" for ts, linea in entradas)
    return {"mensaje": f"Logs '{servicio}' ({modo}):\n" + cuerpo}

@app.get("/loki/todos")
def loki_todos(minutos: int = 15, solo_errores: bool = True):
    minutos = max(1, min(minutos, 180))
    try: servicios = sorted(_loki_servicios())
    except requests.RequestException as e: raise HTTPException(status_code=502, detail=str(e))
    if not servicios: return {"mensaje": "Loki no tiene servicios."}
    por_servicio = 5 if solo_errores else 3
    tipo = "errores" if solo_errores else "líneas"

    def uno(s):
        try: return s, _loki_consulta(s, minutos, solo_errores, por_servicio), None
        except requests.RequestException as e: return s, [], str(e)[:80]

    with ThreadPoolExecutor(max_workers=4) as ex: resultados = list(ex.map(uno, servicios))
    con, sin, mal = [], [], []
    for s, entradas, error in resultados:
        if error: mal.append(f"{s} ({error})")
        elif not entradas: sin.append(s)
        else: con.append(f"== {s} ==\n" + "\n".join(f"{_hora(ts)} {_ocultar(l.strip())[:180]}" for ts, l in entradas))

    out = f"Revisión de Loki:\n\n" + ("\n\n".join(con) if con else f"Ningún servicio tiene {tipo}.")
    if sin and con: out += f"\n\nSin {tipo}: {', '.join(sin)}."
    if mal: out += f"\nNo se pudo leer: {', '.join(mal)}."
    return {"mensaje": out[:6500]}

_NOMBRES_NIVEL = {0: "OK", 1: "A VIGILAR", 2: "CRÍTICO"}
_EMOJI_NIVEL = {0: "🟢", 1: "🟡", 2: "🔴"}

def _resumen(minutos: int = 15) -> dict:
    nivel, claves, partes = 0, [], []
    try:
        p = _prox_estado()
        for nombre, pct in (("CPU", p["cpu"]), ("RAM", p["ram"])):
            n = _nivel(pct)
            nivel = max(nivel, n)
            if n: claves.append(f"{nombre}:{n}")
        partes.append(f"Proxmox: CPU {p['cpu']}%, RAM {p['ram']}%, uptime {p['uptime']} h.")
        altos = [d for d in p["discos"] if _nivel(d["pct"])]
        for d in altos:
            nivel = max(nivel, _nivel(d["pct"]))
            claves.append(f"disco:{d['nombre']}:{_nivel(d['pct'])}")
            partes.append(f"- Disco '{d['nombre']}' al {d['pct']}%")
    except Exception as e:
        nivel = max(nivel, 1); claves.append("proxmox:caido"); partes.append(f"Proxmox: no pude consultarlo.")
    try:
        firing = _grafana_firing()
        if firing:
            nivel = 2; partes.append(f"Grafana: {len(firing)} alerta(s) activa(s):")
            for a in firing[:10]:
                nombre = a.get("labels", {}).get("alertname", "Alerta")
                inst = a.get("labels", {}).get("instance", "?")
                claves.append(f"alerta:{nombre}:{inst}"); partes.append(f"- {nombre} en {inst}")
        else: partes.append("Grafana: sin alertas activas.")
    except Exception as e:
        nivel = max(nivel, 1); claves.append("grafana:caido"); partes.append(f"Grafana: no pude consultarlo.")
    try:
        vms = _prox_vms()
        detenidas = [v for v in vms if v["estado"] != "running"]
        txt = f"Máquinas: {len(vms) - len(detenidas)} corriendo, {len(detenidas)} detenidas"
        if detenidas: txt += ": " + ", ".join(f"{v['nombre']}" for v in detenidas[:10])
        partes.append(txt + ".")
    except Exception: pass
    try:
        servicios = sorted(_loki_servicios())
        def contar(s):
            try: return s, len(_loki_consulta(s, minutos, True, LOKI_MAX_LINEAS))
            except: return s, -1
        with ThreadPoolExecutor(max_workers=4) as ex: conteos = list(ex.map(contar, servicios))
        con_errores = [(s, n) for s, n in conteos if n > 0]
        if con_errores:
            nivel = max(nivel, 1)
            for s, n in con_errores: claves.append(f"logs:{s}")
            partes.append(f"Logs: servicios con errores: {', '.join(s for s, n in con_errores)}.")
        else: partes.append(f"Logs: sin errores.")
    except Exception as e:
        nivel = max(nivel, 1); claves.append("loki:caido"); partes.append(f"Loki: no pude consultarlo.")

    texto = f"Resumen homelab. Estado: {_NOMBRES_NIVEL[nivel]}.\n" + "\n".join(partes)
    return {"nivel": nivel, "texto": texto, "clave": f"{nivel}|" + ";".join(sorted(claves))}

@app.get("/homelab/resumen")
def homelab_resumen():
    return {"mensaje": _resumen()["texto"]}

_ULTIMO_AVISO = "/tmp/puck_ultimo_aviso.json"
_REPETIR_CADA_S = 6 * 3600

def _ya_avisado(minimo: str, clave: str) -> bool:
    try:
        d = json.load(open(_ULTIMO_AVISO)).get(minimo, {})
        return d.get("clave") == clave and time.time() - d.get("ts", 0) < _REPETIR_CADA_S
    except Exception: return False

def _marcar_avisado(minimo: str, clave: str):
    try:
        try: d = json.load(open(_ULTIMO_AVISO))
        except: d = {}
        d[minimo] = {"clave": clave, "ts": time.time()}
        json.dump(d, open(_ULTIMO_AVISO, "w"))
    except: pass

@app.post("/reporte/discord")
def reporte_discord(minimo: str = "ok", forzar: bool = False):
    niveles = {"ok": 0, "vigilar": 1, "critico": 2}
    r = _resumen()
    if r["nivel"] < niveles[minimo]: return {"status": "omitido", "mensaje": "Nada que reportar."}
    clave = hashlib.sha1(r["clave"].encode()).hexdigest()
    if not forzar and minimo != "ok" and _ya_avisado(minimo, clave): return {"status": "omitido"}
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": f"{_EMOJI_NIVEL[r['nivel']]} **Puck (SysAdmin)**\n```\n{r['texto']}\n```"}, timeout=10)
        _marcar_avisado(minimo, clave)
        return {"status": "enviado"}
    except Exception as e: raise HTTPException(status_code=502, detail=str(e))

class MusicaRequest(BaseModel):
    busqueda: str = ""
    tipo: str = "cancion"
    aleatorio: bool = False
    accion: str = ""
    valor: int = None

@app.post("/musica/control")
def controlar_musica_navidrome(req: MusicaRequest):
    script_path = "/home/TU_USUARIO/puck_music.py"

    cmd = ["python", script_path]

    if req.busqueda:
        cmd.extend([req.busqueda, "--tipo", req.tipo])
        if req.aleatorio:
            cmd.append("--aleatorio")
    elif req.accion:
        cmd.extend(["--accion", req.accion])
        if req.valor is not None:
            cmd.extend(["--valor", str(req.valor)])
    else:
        raise HTTPException(status_code=400, detail="Indica qué reproducir o una acción.")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            return {"status": "success", "mensaje": f"Listo, señor. {result.stdout.strip()}"}
        else:
            raise HTTPException(status_code=500, detail=f"Error ejecutando la orden: {(result.stderr.strip() or result.stdout.strip())}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fallo al ejecutar el script de música: {str(e)}")
@app.get("/homelab/actualizaciones")
def actualizaciones_docker():
    try:
        query = f'{{{LOKI_LABEL}="watchtower"}}'
        fin = time.time_ns()
        r = requests.get(
            f"{LOKI_URL}/loki/api/v1/query_range",
            params={"query": query, "start": fin - 1440 * 60 * 10**9, "end": fin, "limit": 20, "direction": "backward"},
            timeout=15
        )
        r.raise_for_status()
        entradas = [(int(ts), linea) for stream in r.json().get("data", {}).get("result", []) for ts, linea in stream["values"]]
        if not entradas:
            return {"mensaje": "No hay registro de actualizaciones o imágenes nuevas en las últimas 24 horas. ¡Todos los contenedores están al día!"}
        entradas.sort(key=lambda x: x[0], reverse=True)
        lineas = [f"{_hora(ts)} {linea.strip()[:200]}" for ts, linea in entradas[:15]]
        return {"mensaje": "Última actividad de Watchtower (Actualizaciones):\n" + "\n".join(lineas)}
    except Exception as e:
        return {"mensaje": f"Error al consultar actualizaciones en Loki: {e}"}
