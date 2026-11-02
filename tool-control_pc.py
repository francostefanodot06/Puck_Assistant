import requests

class Tools:
    def __init__(self):
        self.pc_ip = "TU_IP_PC"
        self.puerto = "8000"
        self.api_key = "TU_API_KEY"
        self.base_url = f"http://{self.pc_ip}:{self.puerto}"
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {self.api_key}"

    def abrir_aplicacion(self, comando: str) -> str:
        """
        Abre una aplicación en la PC.
        Opciones permitidas: discord, terminal, brave, feishin, steam, dolphin, zen, heroic.
        """
        try:
            r = self.s.post(f"{self.base_url}/ejecutar/{comando.lower().strip()}", timeout=10)
            if r.status_code == 200:
                return r.json().get("mensaje", "Aplicación abierta.")
            elif r.status_code == 401:
                return "Error de Autenticación API."
            return f"Error del backend: {r.text}"
        except Exception as e:
            return f"Fallo de red al comunicarse con la PC: {str(e)}"

    def cerrar_aplicacion(self, comando: str) -> str:
        """
        Cierra una aplicación en la PC.
        Opciones permitidas: discord, terminal, brave, feishin, steam, dolphin, zen, heroic.
        """
        try:
            r = self.s.post(f"{self.base_url}/cerrar/{comando.lower().strip()}", timeout=10)
            if r.status_code == 200:
                return r.json().get("mensaje", "Aplicación cerrada.")
            elif r.status_code == 401:
                return "Error de Autenticación API."
            return f"Error del backend: {r.text}"
        except Exception as e:
            return f"Fallo de red al comunicarse con la PC: {str(e)}"

    def reporte_homelab(self) -> str:
        """
        Obtiene un resumen general del estado del Homelab (alertas de Grafana, uso de Proxmox y errores de Loki).
        """
        try:
            r = self.s.get(f"{self.base_url}/homelab/resumen", timeout=15)
            if r.status_code == 200:
                return r.json().get("mensaje", "Reporte vacío.")
            elif r.status_code == 401:
                return "Error de Autenticación API."
            return f"Error del backend: {r.text}"
        except Exception as e:
            return f"Fallo de red al comunicarse con el servidor: {str(e)}"

    def estado_proxmox(self) -> str:
        """
        Obtiene el estado detallado de Proxmox, uso de discos, CPU, RAM y máquinas virtuales (VMs/LXCs).
        """
        try:
            r_estado = self.s.get(f"{self.base_url}/proxmox/estado", timeout=10)
            r_vms = self.s.get(f"{self.base_url}/proxmox/vms", timeout=10)

            if r_estado.status_code == 401:
                return "Error de Autenticación API."

            estado_txt = r_estado.json().get("mensaje", "") if r_estado.status_code == 200 else "Fallo al leer estado."
            vms_txt = r_vms.json().get("mensaje", "") if r_vms.status_code == 200 else "Fallo al leer VMs."

            return f"{estado_txt}\n\nDetalle de máquinas:\n{vms_txt}"
        except Exception as e:
            return f"Fallo de red al comunicarse con Proxmox: {str(e)}"
