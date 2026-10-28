"""
title: Control PC y Monitoreo Homelab
description: Agente para controlar aplicaciones de escritorio y consultar métricas/alertas del homelab.
author: Tu_Nombre
"""

import requests

class Tools:
    def __init__(self):
        self.pc_ip = "TU_IP_PC"
        self.puerto = "8000"

    def abrir_aplicacion(self, nombre_app: str) -> str:
        """
        Abre una aplicación específica en la PC de escritorio física del usuario (EndeavourOS).
        :param nombre_app: El nombre de la aplicación a abrir (opciones válidas: 'discord', 'navegador', 'terminal', 'feishin' , 'steam' , 'dolphin' , 'brave' , 'zen').
        """
        url = f"http://{self.pc_ip}:{self.puerto}/ejecutar/{nombre_app}"
        try:
            response = requests.post(url, timeout=5)
            if response.status_code == 200:
                return f"Éxito: {response.json()['mensaje']}"
            else:
                return f"Error: Comando bloqueado por seguridad o aplicación no encontrada. Detalle: {response.text}"
        except Exception as e:
            return f"Fallo de red: No me pude comunicar con la PC. ¿Está el servidor uvicorn corriendo? Detalle: {str(e)}"

    def controlar_reproductor(self, accion: str) -> str:
        """
        Controla la reproducción de música y el volumen en la PC física del usuario.
        :param accion: Acción a realizar. Opciones válidas: 'play', 'pause', 'play-pause', 'next', 'previous', 'stop', 'feishin-up' (subir volumen solo a Feishin), 'feishin-down' (bajar volumen solo a Feishin).
        """
        url = f"http://{self.pc_ip}:{self.puerto}/media/{accion}"
        try:
            response = requests.post(url, timeout=5)
            if response.status_code == 200:
                return f"Éxito: {response.json()['mensaje']}"
            else:
                return f"Error al ejecutar. Detalle: {response.text}"
        except Exception as e:
            return f"Fallo de conexión. Detalle: {str(e)}"

    def cerrar_aplicacion(self, nombre_app: str) -> str:
        """
        Cierra o termina una aplicación específica que se esté ejecutando en la PC física del usuario (EndeavourOS).
        :param nombre_app: El nombre de la aplicación a cerrar (opciones válidas: 'discord', 'terminal', 'brave', 'feishin', 'steam', 'dolphin', 'zen browser').
        """
        url = f"http://{self.pc_ip}:{self.puerto}/cerrar/{nombre_app}"
        try:
            response = requests.post(url, timeout=5)
            if response.status_code == 200:
                return f"Éxito: {response.json()['mensaje']}"
            elif response.status_code == 404:
                return f"Aviso: El programa {nombre_app} no estaba en ejecución."
            else:
                return f"Error al cerrar la aplicación. Detalle: {response.text}"
        except Exception as e:
            return f"Fallo de red: No me pude comunicar con la PC. Detalle: {str(e)}"

    def consultar_proxmox(self) -> str:
        """
        Consulta el estado de salud, consumo de CPU, RAM, almacenamiento de todos los discos y tiempo de actividad del servidor Proxmox del homelab.
        No requiere parámetros.
        """
        url = f"http://{self.pc_ip}:{self.puerto}/proxmox/estado"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()["mensaje"]
            else:
                return f"Error al consultar Proxmox. Detalle: {response.text}"
        except Exception as e:
            return f"Fallo de conexión con la API local. Detalle: {str(e)}"

    def consultar_grafana(self) -> str:
        """
        Consulta el panel de Grafana para verificar si hay alertas activas, errores o incidencias en el homelab.
        Úsalo cuando el usuario pregunte por el estado de las alertas o qué ves en Grafana.
        No requiere parámetros.
        """
        url = f"http://{self.pc_ip}:{self.puerto}/grafana/estado"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()["mensaje"]
            else:
                return f"Error al consultar Grafana. Detalle: {response.text}"
        except Exception as e:
            return f"Fallo de conexión con la API local. Detalle: {str(e)}"

    def listar_servicios_con_logs(self) -> str:
        """
        Lista los servicios del homelab que tienen logs disponibles en Loki.
        Úsalo antes de consultar_logs si no sabés el nombre exacto del servicio.
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
