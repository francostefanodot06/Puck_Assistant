import requests

class Tools:
    TIPOS = {"cancion", "album", "playlist"}
    ACCIONES = {
        "play",
        "pause",
        "stop",
        "toggle",
        "next",
        "previous",
        "volumen",
        "actual",
    }

    def __init__(self):
        self.pc_ip = "TU_IP_PC"
        self.puerto = "8000"
        self.api_key = "TU_API_KEY"
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {self.api_key}"

    def reproducir_musica(
        self,
        busqueda: str = "",
        tipo: str = "cancion",
        aleatorio: bool = False,
        accion: str = "",
        valor: int = None,
    ) -> str:

        # --- PARCHE PARA MODELOS TERCOS ---
        accion_limpia = accion.lower().strip()
        if accion_limpia == "reproducir":
            accion = ""
        elif "volumen" in accion_limpia:
            accion = "volumen"
        elif accion_limpia in {"pausar", "pausa"}:
            accion = "pause"
        elif accion_limpia in {"detener", "parar", "kill", "cerrar", "stop"}:
            accion = "stop"
        elif accion_limpia in {"reanudar", "continuar", "play"}:
            accion = "play"

        # Si el modelo manda un tipo inválido o alucina, lo corregimos a 'cancion' por defecto
        if tipo not in self.TIPOS:
            tipo = "cancion"
        # ----------------------------------

        if accion and accion not in self.ACCIONES:
            return f"Error: acción inválida '{accion}'."

        payload = {
            "busqueda": busqueda,
            "tipo": tipo,
            "aleatorio": aleatorio,
            "accion": accion
        }
        if valor is not None:
            payload["valor"] = valor

        url = f"http://{self.pc_ip}:{self.puerto}/musica/control"

        try:
            response = self.s.post(url, json=payload, timeout=15)
            if response.status_code == 200:
                return response.json()["mensaje"]
            elif response.status_code == 401:
                return "Error de Autenticación API. Verifica tu API KEY."
            else:
                return f"Error del backend: {response.text}"
        except Exception as e:
            return f"Fallo de red al comunicarse con la PC: {str(e)}"
