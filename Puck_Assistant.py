from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel
from datetime import datetime
import requests
import os
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =============================================================================
# CONFIGURACIÓN DEL HOMELAB (VALORES GENÉRICOS)
# =============================================================================
PROXMOX_IP = "TU_IP_DE_PROXMOX"
PROXMOX_NODO = "TU_NOMBRE_DE_NODO"
PROXMOX_TOKEN_ID = "root@pam!tu-token-id"
PROXMOX_SECRET = "tu-secret-de-proxmox-aqui"

LOKI_URL = os.environ.get("LOKI_URL", "http://TU_IP_DE_LOKI:3100")
LOKI_LABEL = os.environ.get("LOKI_LABEL", "container")

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/tu-webhook-de-discord"

# --- API KEYS DEL ECOSISTEMA DE DESCARGAS ---
ARR_IP = "TU_IP_DEL_STACK_ARR"
RADARR_KEY = "PEGA_TU_API_KEY_ACA"
SONARR_KEY = "PEGA_TU_API_KEY_ACA"
PROWLARR_KEY = "PEGA_TU_API_KEY_ACA"
BAZARR_KEY = "PEGA_TU_API_KEY_ACA"

QBIT_IP = "TU_IP_DE_QBITTORRENT"
QBIT_PUERTO = 8080

UMBRAL_VIGILAR = 80
UMBRAL_CRITICO = 90
API_KEY = "tu_clave_bearer_para_la_api"
# =============================================================================

def auth(authorization: str = Header(default="")):
    esperado = f"Bearer {API_KEY}".encode()
    if not API_KEY or not hmac.compare_digest(authorization.encode(), esperado):
        raise HTTPException(status_code=401, detail="No autorizado")

app = FastAPI(dependencies=[Depends(auth)])

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
        mensaje = f"Reporte del homelab:\nCPU: {p['cpu']}%{_ETIQUETA[_nivel(p['cpu'])]}\nRAM: {p['ram']}%{_ETIQUETA[_nivel(p['ram'])]}\nUptime: {p['uptime']} horas.\nAlmacenamiento:\n{discos}"
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

@app.get("/proxmox/backups")
def estado_backups():
    try:
        tareas = _prox_get(f"/nodes/{PROXMOX_NODO}/tasks?limit=50")
        backups = [t for t in tareas if t.get("type") == "vzdump"]
        if not backups: return {"mensaje": "No se encontraron tareas de backup recientes en Proxmox."}
        lineas = []
        for b in backups[:5]:
            estado = b.get("status", "Desconocido")
            inicio = datetime.fromtimestamp(b.get("starttime", 0)).strftime("%d/%m %H:%M")
            fin = datetime.fromtimestamp(b.get("endtime", 0)).strftime("%H:%M") if b.get("endtime") else "Corriendo"
            lineas.append(f"- [{inicio} a {fin}] Backup: {estado}")
        return {"mensaje": "Últimos 5 backups de Proxmox:\n" + "\n".join(lineas)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error leyendo backups: {e}")

@app.get("/proxmox/discos")
def estado_discos():
    try:
        discos = _prox_get(f"/nodes/{PROXMOX_NODO}/disks/list")
        lineas = []
        for d in discos:
            dev = d.get("devpath", "?")
            salud = d.get("health", "Desconocido")
            modelo = d.get("model", "N/A")
            size = round(d.get("size", 0) / (1024**3), 1) if d.get("size") else 0
            lineas.append(f"- {dev} ({modelo}, {size}GB): Salud {salud}")
        return {"mensaje": "Estado SMART de discos físicos:\n" + "\n".join(lineas)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error leyendo discos: {e}")

@app.get("/homelab/arr")
def estado_descargas():
    reporte = []
    servicios_arr = {
        "Radarr": (7878, RADARR_KEY),
        "Sonarr": (8989, SONARR_KEY),
        "Prowlarr": (9696, PROWLARR_KEY)
    }
    for app_name, (puerto, key) in servicios_arr.items():
        if key == "PEGA_TU_API_KEY_ACA" or not key:
            reporte.append(f"- {app_name}: API Key no configurada.")
            continue
        try:
            version = "v1" if app_name == "Prowlarr" else "v3"
            r = requests.get(f"http://{ARR_IP}:{puerto}/api/{version}/health", headers={"X-Api-Key": key}, timeout=5)
            r.raise_for_status()
            alertas = r.json()
            errores = [a["message"] for a in alertas if a.get("type") in ("error", "warning")]
            if errores:
                reporte.append(f"- {app_name}: {len(errores)} avisos (Ej: {errores[0]})")
            else:
                reporte.append(f"- {app_name}: Operativo, sin avisos.")
        except Exception:
            reporte.append(f"- {app_name}: Inalcanzable o error de API.")

    if BAZARR_KEY != "PEGA_TU_API_KEY_ACA" and BAZARR_KEY:
        try:
            r = requests.get(f"http://{ARR_IP}:6767/api/system/status", headers={"X-Api-Key": BAZARR_KEY}, timeout=5)
            r.raise_for_status()
            reporte.append("- Bazarr: Operativo (API conectada).")
        except Exception:
            reporte.append("- Bazarr: Inalcanzable o error de API.")
    else:
        reporte.append("- Bazarr: API Key no configurada.")

    try:
        r = requests.get(f"http://{QBIT_IP}:{QBIT_PUERTO}/api/v2/app/version", timeout=5)
        if r.status_code == 200:
            reporte.append("- qBittorrent: Operativo y en línea.")
        elif r.status_code == 403:
            reporte.append("- qBittorrent: Bloqueado (Bypass de Auth requerido).")
        else:
            reporte.append(f"- qBittorrent: Error HTTP {r.status_code}.")
    except Exception:
        reporte.append("- qBittorrent: Inalcanzable.")

    return {"mensaje": "Reporte de Descargas:\n" + "\n".join(reporte)}

LOKI_MAX_LINEAS = 40
LOKI_MAX_CHARS = 300
LOKI_REGEX_ERRORES = "(?i)error|fail|fatal|panic|exception|denied|timeout"
_SECRETOS = re.compile(r"(?i)(password|passwd|pwd|token|secret|api[_-]?key|authorization)(\"?\s*[:=]\s*\"?(?:Bearer\s+)?)[^\s\"&,;]+")

def _hora(ts: int) -> str: return datetime.fromtimestamp(ts / 1e9).strftime("%H:%M:%S")

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

@app.post("/homelab/reporte_diario")
def reporte_diario_discord():
    try:
        p = _prox_estado()
        cuerpo = [
            f"📊 **REPORTE DIARIO DE INFRAESTRUCTURA**",
            "--------------------------------------------------",
            f"🖥️ **Proxmox (Hardware):**",
            f"• CPU: {p['cpu']}% | RAM: {p['ram']}% | Uptime: {p['uptime']} hrs",
        ]
        try:
            res_discos = estado_discos()["mensaje"]
            cuerpo.append(f"\n💾 **{res_discos}**")
        except Exception:
            cuerpo.append("\n💾 **Discos:** Error al consultar SMART.")

        try:
            res_arr = estado_descargas()["mensaje"]
            cuerpo.append(f"\n🎬 **{res_arr}**")
        except Exception:
            cuerpo.append("\n🎬 **Descargas:** Error al consultar stack.")

        try:
            res_watch = actualizaciones_docker()["mensaje"]
            cuerpo.append(f"\n🐳 **{res_watch}**")
        except Exception:
            cuerpo.append("\n🐳 **Watchtower:** Error al consultar logs.")

        try:
            res_backups = estado_backups()["mensaje"]
            cuerpo.append(f"\n📦 **{res_backups}**")
        except Exception:
            cuerpo.append("\n📦 **Backups:** Error al consultar historial.")

        mensaje_final = "\n".join(cuerpo)
        if len(mensaje_final) > 1900:
            mensaje_final = mensaje_final[:1890] + "\n...(Recortado por longitud)"

        r = requests.post(DISCORD_WEBHOOK_URL, json={"content": mensaje_final}, timeout=12)
        r.raise_for_status()
        return {"status": "success", "mensaje": "Reporte diario consolidado enviado a Discord."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enviando reporte completo: {str(e)}")

# --- INTEGRACIÓN DEL MÓDULO EXTRA (PUCK_EXTRA) ---
import puck_extra
app.include_router(puck_extra.router)
puck_extra.iniciar(lambda: _resumen()["texto"] if "_resumen" in globals() else "Homelab OK", _prox_estado)
