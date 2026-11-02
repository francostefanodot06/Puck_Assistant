        No requiere parámetros.
        """
        url = f"http://{self.pc_ip}:{self.puerto}/loki/servicios"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()["mensaje"]
            else:
                return f"Error al consultar Loki. Detalle: {response.text}"
        except Exception as e:
            return f"Fallo de conexión con la API local. Detalle: {str(e)}"

    def consultar_logs(
        self, servicio: str, minutos: int = 15, solo_errores: bool = True
    ) -> str:
        """
        Consulta los logs recientes de un servicio del homelab en Loki, para diagnosticar fallos o entender qué pasó antes de una alerta.
        Úsalo cuando el usuario pregunte por errores, fallos o el comportamiento reciente de un servicio.
        :param servicio: Nombre exacto del servicio (si no lo sabés, usá primero listar_servicios_con_logs).
        :param minutos: Ventana de tiempo hacia atrás en minutos (entre 1 y 180). Por defecto 15.
        :param solo_errores: Si es True trae solo líneas con errores o fallos; si es False trae todas las líneas recientes.
        """
        url = f"http://{self.pc_ip}:{self.puerto}/loki/logs"
        try:
            response = requests.get(
                url,
                params={
                    "servicio": servicio,
                    "minutos": minutos,
                    "solo_errores": solo_errores,
                },
                timeout=20,
            )
            if response.status_code == 200:
                return response.json()["mensaje"]
            else:
                return f"Error al consultar los logs. Detalle: {response.text}"
        except Exception as e:
            return f"Fallo de conexión con la API local. Detalle: {str(e)}"
