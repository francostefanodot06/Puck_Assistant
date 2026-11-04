import os
import sqlite3
import threading
import time
from contextlib import closing
from datetime import datetime
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# =============================================================================
# CONFIGURACIÓN (Valores Genéricos)
# =============================================================================
DB_PATH = "/var/lib/puck/puck.db"
INTERVALO_S = 300
RETENCION_METRICAS_DIAS = 90

DOCKER_URL = "http://TU_IP_DOCKER:2375"
DOCKER_IGNORAR = {"portainer"}

PROMETHEUS_URL = "http://TU_IP_PROMETHEUS:9090"
JELLYFIN_URL = "http://TU_IP_JELLYFIN:8096"
JELLYFIN_KEY = "TU_API_KEY_DE_JELLYFIN"

ARRS = {
    "sonarr": ("http://TU_IP_SONARR:8989", "TU_API_KEY_SONARR", "v3"),
    "radarr": ("http://TU_IP_RADARR:7878", "TU_API_KEY_RADARR", "v3"),
    "prowlarr": ("http://TU_IP_PROWLARR:9696", "TU_API_KEY_PROWLARR", "v1"),
}

LIMITE_TEMP = {"coretemp": 80, "k10temp": 80, "nvme": 70, "drivetemp": 50}
# =============================================================================

router = APIRouter()
_SEV = {1: "a vigilar", 2: "CRÍTICO"}

def _get(url: str, **kw):
    r = requests.get(url, timeout=8, **kw)
    r.raise_for_status()
    return r.json()

def _fmt_ts(ts: float) -> str: return datetime.fromtimestamp(ts).strftime("%d/%m %H:%M")

def _dur(seg: float) -> str:
    seg = int(seg)
    if seg < 3600: return f"{seg // 60} min"
    if seg < 86400: return f"{seg // 3600} h {seg % 3600 // 60} min"
    return f"{seg // 86400} d {seg % 86400 // 3600} h"

# --- BASE DE DATOS SQLITE ---
def _db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    return c

def _init_db():
    with closing(_db()) as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS incidencias(
                id INTEGER PRIMARY KEY, clave TEXT NOT NULL, severidad INTEGER NOT NULL,
                detalle TEXT, abierta_ts REAL NOT NULL, cerrada_ts REAL, notas TEXT
            );
            CREATE INDEX IF NOT EXISTS ix_inc_clave ON incidencias(clave, cerrada_ts);
            CREATE TABLE IF NOT EXISTS metricas(ts REAL NOT NULL, nombre TEXT NOT NULL, valor REAL NOT NULL);
            CREATE INDEX IF NOT EXISTS ix_met ON metricas(nombre, ts);
        """)
        c.commit()

def sincronizar_incidencias(activas: dict, preservar_prefijos: tuple = ()):
    ahora = time.time()
    nuevas, cerradas = [], []
    with closing(_db()) as c:
        abiertas = {r["clave"]: r for r in c.execute("SELECT * FROM incidencias WHERE cerrada_ts IS NULL")}
        for clave, (sev, det) in activas.items():
            if clave not in abiertas:
                c.execute("INSERT INTO incidencias(clave, severidad, detalle, abierta_ts) VALUES (?,?,?,?)", (clave, sev, det, ahora))
                nuevas.append(clave)
            elif sev > abiertas[clave]["severidad"]:
                c.execute("UPDATE incidencias SET severidad=?, detalle=COALESCE(?, detalle) WHERE id=?", (sev, det, abiertas[clave]["id"]))
        for clave, fila in abiertas.items():
            if clave not in activas and not clave.startswith(preservar_prefijos):
                c.execute("UPDATE incidencias SET cerrada_ts=? WHERE id=?", (ahora, fila["id"]))
                cerradas.append(clave)
        c.commit()
    return nuevas, cerradas

def _guardar_metricas(muestras: dict):
    if not muestras: return
    ahora = time.time()
    with closing(_db()) as c:
        c.executemany("INSERT INTO metricas(ts, nombre, valor) VALUES (?,?,?)", [(ahora, k, v) for k, v in muestras.items()])
        c.execute("DELETE FROM metricas WHERE ts < ?", (ahora - RETENCION_METRICAS_DIAS * 86400,))
        c.commit()

# --- DOCKER ---
def _docker_estado() -> list:
    out = []
    for c in _get(f"{DOCKER_URL}/containers/json", params={"all": 1}):
        status = c.get("Status", "")
        salud = "unhealthy" if "(unhealthy)" in status else "healthy" if "(healthy)" in status else ""
        out.append({"nombre": c["Names"][0].lstrip("/"), "estado": c.get("State", "?"), "detalle": status, "salud": salud})
    return sorted(out, key=lambda x: x["nombre"])

@router.get("/docker/estado")
def docker_estado():
    try: cs = _docker_estado()
    except requests.RequestException as e: raise HTTPException(status_code=502, detail=str(e))
    if not cs: return {"mensaje": "Docker no tiene contenedores."}
    mal = [c for c in cs if c["estado"] != "running" or c["salud"] == "unhealthy"]
    lineas = [f"{len(cs) - len(mal)} contenedores bien y {len(mal)} con problemas (de {len(cs)})."]
    for c in mal: lineas.append(f"- PROBLEMA {c['nombre']}: {c['estado']} {c['salud']} ({c['detalle']})")
    for c in cs:
        if c not in mal: lineas.append(f"- {c['nombre']}: {c['estado']} {c['salud']} ({c['detalle']})")
    return {"mensaje": "\n".join(lineas[:70])}

# --- MULTIMEDIA Y NOVEDADES (JELLYFIN) ---
@router.get("/multimedia/novedades")
def multimedia_novedades(limite: int = 10):
    limite = max(1, min(limite, 25))
    lineas = []
    try:
        headers = {
            "X-Emby-Token": JELLYFIN_KEY,
            "Authorization": f'MediaBrowser Token="{JELLYFIN_KEY}"'
        }
        data = _get(f"{JELLYFIN_URL}/Items", headers=headers, params={
            "Recursive": "true", "SortBy": "DateCreated", "SortOrder": "Descending", "Limit": limite,
            "IncludeItemTypes": "Movie,Episode", "Fields": "DateCreated"
        })
        lineas.append("Agregado últimamente a Jellyfin:")
        for it in data.get("Items", []):
            titulo = f"{it.get('SeriesName', '')} - {it['Name']}" if it.get("Type") == "Episode" else it["Name"]
            lineas.append(f"- {titulo[:80]} ({it.get('DateCreated', '')[:10]})")
    except requests.RequestException as e:
        lineas.append(f"Jellyfin no respondió ({str(e)[:60]}).")
    return {"mensaje": "\n".join(lineas)}

# --- HARDWARE (TÉRMICAS Y UPS) ---
def _prom(q: str) -> list:
    return _get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": q})["data"]["result"]

def _temperaturas() -> list:
    por_chip = {}
    for r in _prom("node_hwmon_temp_celsius * on(chip, instance) group_left(chip_name) node_hwmon_chip_names"):
        m = r["metric"]
        clave = (m.get("chip_name", "?"), m.get("chip", "?"))
        por_chip[clave] = max(por_chip.get(clave, 0.0), float(r["value"][1]))
    contador, out = {}, []
    for (tipo, chip), v in sorted(por_chip.items()):
        contador[tipo] = contador.get(tipo, 0) + 1
        out.append({"tipo": tipo, "nombre": f"{tipo}#{contador[tipo]}", "valor": round(v, 1)})
    return out

def _nivel_temp(tipo: str, v: float) -> int:
    lim = LIMITE_TEMP.get(tipo)
    if lim is None: return 0
    return 2 if v >= lim + 10 else 1 if v >= lim else 0

def _ups() -> dict | None:
    voltaje = _prom("network_ups_tools_battery_voltage")
    if not voltaje: return None
    uso = _prom("network_ups_tools_ups_load")
    voltaje_entrada = _prom("network_ups_tools_input_voltage")

    en_bateria = False
    if voltaje_entrada and float(voltaje_entrada[0]["value"][1]) < 100:
        en_bateria = True

    return {
        "bateria": round(float(voltaje[0]["value"][1]), 1),
        "carga": round(float(uso[0]["value"][1])) if uso else None,
        "en_bateria": en_bateria
    }

@router.get("/hardware/estado")
def hardware_estado():
    lineas = []
    try:
        temps = _temperaturas()
        if temps: lineas.insert(0, "Temperaturas (maximo por chip):")
        for t in temps: lineas.append(f"- {t['nombre']}: {t['valor']} C")
    except requests.RequestException: lineas.append("Temperaturas: no pude consultar Prometheus.")
    try:
        u = _ups()
        if u: lineas.append(f"UPS: bateria {u['bateria']}V, carga {u['carga']}%, {'BATERIA' if u['en_bateria'] else 'Red electrica'}.")
    except requests.RequestException: lineas.append("UPS: no pude consultarlo.")
    return {"mensaje": "\n".join(lineas)}

# --- INCIDENCIAS (MEMORIA) ---
@router.get("/incidencias/abiertas")
def incidencias_abiertas():
    with closing(_db()) as c:
        filas = c.execute("SELECT * FROM incidencias WHERE cerrada_ts IS NULL ORDER BY severidad DESC, abierta_ts").fetchall()
    if not filas: return {"mensaje": "No hay incidencias abiertas."}
    ahora = time.time()
    lineas = [f"- #{f['id']} [{_SEV[f['severidad']]}] {f['clave']} (hace {_dur(ahora - f['abierta_ts'])})" for f in filas]
    return {"mensaje": "Incidencias abiertas:\n" + "\n".join(lineas)}

# --- BACKGROUND WATCHER ---
def _ciclo(resumen_fn, prox_fn):
    activas, muestras, preservar = {}, {}, []
    try:
        r = resumen_fn()
        for k in filter(None, r.split(";", 1)[0].split(";")): activas[k] = (1, None)
    except Exception: return

    try:
        p = prox_fn()
        muestras["cpu"], muestras["ram"] = p["cpu"], p["ram"]
        for d in p["discos"]: muestras[f"disco:{d['nombre']}"] = d["pct"]
    except Exception: pass

    try:
        for c in _docker_estado():
            if c["nombre"] in DOCKER_IGNORAR: continue
            if c["estado"] == "restarting": activas[f"docker:{c['nombre']}:reiniciando"] = (2, c["detalle"])
            elif c["estado"] != "running": activas[f"docker:{c['nombre']}:{c['estado']}"] = (1, c["detalle"])
            elif c["salud"] == "unhealthy": activas[f"docker:{c['nombre']}:unhealthy"] = (1, c["detalle"])
    except Exception: preservar.append("docker:")

    try:
        for t in _temperaturas():
            muestras[f"temp:{t['nombre']}"] = t["valor"]
            n = _nivel_temp(t["tipo"], t["valor"])
            if n: activas[f"temp:{t['nombre']}"] = (n, f"{t['valor']}°C")
    except Exception: preservar.append("temp:")

    sincronizar_incidencias(activas, tuple(preservar))
    _guardar_metricas(muestras)

def _loop(resumen_fn, prox_fn):
    while True:
        try: _ciclo(resumen_fn, prox_fn)
        except Exception: pass
        time.sleep(INTERVALO_S)

def iniciar(resumen_fn, prox_fn):
    _init_db()
    threading.Thread(target=_loop, args=(resumen_fn, prox_fn), daemon=True).start()
