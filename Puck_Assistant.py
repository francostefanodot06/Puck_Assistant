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
