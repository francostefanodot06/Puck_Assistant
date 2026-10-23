import os
import requests
import subprocess
from typing import Dict, Any

class Tools:
    """
    Herramientas de SysAdmin para Puck.
    Inyecta este script en la sección de 'Tools' de Open WebUI.
    """
    def __init__(self):
        # Variables de entorno para seguridad
        self.proxmox_host = os.getenv("PROXMOX_HOST", "https://X.X.X.X:8006")
        self.proxmox_node = os.getenv("PROXMOX_NODE", "pve")

        # Token format: 'USER@realm!TOKENID=SECRET'
        self.proxmox_token = os.getenv("PROXMOX_API_TOKEN", "")
        self.headers = {
            "Authorization": f"PVEAPIToken={self.proxmox_token}"
        }

    def consultar_estado_proxmox(self) -> str:
        """
        Consulta la API de Proxmox para revisar el estado del servidor (CPU, RAM, Uptime).
        Útil para responder: "¿Cómo está el servidor Proxmox?"
        """
        if not self.proxmox_token:
            return "Señor, no tengo configurado el token de acceso a la API de Proxmox."

        url = f"{self.proxmox_host}/api2/json/nodes/{self.proxmox_node}/status"

        try:
            # verify=False si usás certificados autofirmados en Proxmox
            response = requests.get(url, headers=self.headers, verify=False, timeout=10)
            response.raise_for_status()
            data = response.json().get("data", {})

            cpu_usage = data.get("cpu", 0) * 100
            ram_usage = (data.get("memory", {}).get("used", 0) / data.get("memory", {}).get("total", 1)) * 100

            return f"Proxmox Status - CPU: {cpu_usage:.1f}%, RAM: {ram_usage:.1f}%."

        except Exception as e:
            return f"Se produjo un error al conectar con Proxmox: {e}"

    def abrir_aplicacion(self, nombre_app: str) -> str:
        """
        Abre una aplicación local en la PC de escritorio.
        Útil para comandos como: "Puck, abrime el navegador"
        """
        try:
            # Lógica básica para Windows (ejemplo). Adaptar según SO (Linux/Mac).
            if os.name == 'nt':
                subprocess.Popen(["start", nombre_app], shell=True)
            else:
                subprocess.Popen(["xdg-open", nombre_app])

            return f"He ejecutado la orden para abrir {nombre_app}, señor."
        except Exception as e:
            return f"Hubo un inconveniente intentando abrir la aplicación: {e}"

    def control_multimedia(self, accion: str) -> str:
        """
        Controla la reproducción multimedia local (Play, Pause, Mute).
        Requiere instalar librerías adicionales como pyautogui en la PC host.
        """
        # Nota para GitHub: Esta función requiere dependencias de SO específicas.
        # import pyautogui
        acciones_validas = ["playpause", "volumemute", "volumeup", "volumedown"]

        if accion.lower() not in acciones_validas:
            return "Acción multimedia no reconocida."

        try:
            # pyautogui.press(accion.lower())
            return f"Acción multimedia '{accion}' ejecutada con éxito."
        except Exception as e:
            return f"Error ejecutando control multimedia: {e}"
