

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
