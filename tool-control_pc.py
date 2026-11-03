kkimport requests

class Tools:
    def __init__(self):
        self.pc_ip = "TU_IP_O_DOMINIO_DEL_BACKEND"
        self.puerto = "8000"
        self.api_key = "tu_clave_bearer_para_la_api"
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {self.api_key}"

    def _base(self) -> str:
        return f"http://{self.pc_ip}:{self.puerto}"

    def consultar_proxmox(self) -> str:
        """Obtiene un resumen general del estado del servidor, CPU, RAM y uso de almacenamiento virtual."""
        try:
            response = self.s.get(f"{self._base()}/proxmox/estado", timeout=10)
            if response.status_code == 200:
                return response.json()["mensaje"]
            else:
                return f"Error: {response.text}"
        except Exception as e:
            return f"Fallo: {str(e)}"

    def listar_maquinas_virtuales(self) -> str:
        """Lista todas las máquinas virtuales y contenedores LXC con su estado."""
        try:
            response = self.s.get(f"{self._base()}/proxmox/vms", timeout=15)
            if response.status_code == 200:
                return response.json()["mensaje"]
            else:
                return f"Error: {response.text}"
        except Exception as e:
            return f"Fallo: {str(e)}"

    def revisar_todos_los_logs(self, minutos: int = 15, solo_errores: bool = True) -> str:
        """Revisa los logs de TODOS los contenedores del homelab en simultáneo buscando errores recientes."""
        try:
            response = self.s.get(
                f"{self._base()}/loki/todos",
                params={"minutos": minutos, "solo_errores": solo_errores},
                timeout=60,
            )
            if response.status_code == 200:
                return response.json()["mensaje"]
            else:
                return f"Error: {response.text}"
        except Exception as e:
            return f"Fallo: {str(e)}"

    def estado_smart_discos(self) -> str:
        """Revisa la salud SMART detallada de los discos físicos en Proxmox."""
        try:
            response = self.s.get(f"{self._base()}/proxmox/discos", timeout=10)
            if response.status_code == 200:
                return response.json()["mensaje"]
            else:
                return f"Error: {response.text}"
        except Exception as e:
            return f"Fallo: {str(e)}"

    def estado_descargas_arr(self) -> str:
        """Consulta el estado, salud y alertas del stack de descargas (Radarr, Sonarr, Prowlarr, Bazarr, qBittorrent)."""
        try:
            response = self.s.get(f"{self._base()}/homelab/arr", timeout=10)
            if response.status_code == 200:
                return response.json()["mensaje"]
            else:
                return f"Error: {response.text}"
        except Exception as e:
            return f"Fallo: {str(e)}"

    def estado_backups_proxmox(self) -> str:
        """Revisa el historial y estado de los últimos backups de Proxmox."""
        try:
            response = self.s.get(f"{self._base()}/proxmox/backups", timeout=10)
            if response.status_code == 200:
                return response.json()["mensaje"]
            else:
                return f"Error: {response.text}"
        except Exception as e:
            return f"Fallo: {str(e)}"

    def consultar_actualizaciones(self) -> str:
        """Consulta los registros de Watchtower para saber si hay actualizaciones recientes de contenedores o imágenes nuevas."""
        try:
            response = self.s.get(f"{self._base()}/homelab/actualizaciones", timeout=15)
            if response.status_code == 200:
                return response.json()["mensaje"]
            else:
                return f"Error: {response.text}"
        except Exception as e:
            return f"Fallo: {str(e)}"
