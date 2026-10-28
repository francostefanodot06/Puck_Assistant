"""
title: Gestor de Navidrome y Reproductor
description: Busca, reproduce y controla música, volumen y estados multimedia en la PC principal.
author: Tu_Nombre
"""

import subprocess

class Tools:
    def __init__(self):
        self.pc_ip = "TU_IP_PC"
        self.pc_user = "TU_USUARIO_PC"
        self.script_path = "/ruta/a/tu/puck_music.py"

    def reproducir_musica(
        self,
        busqueda: str = "",
        tipo: str = "cancion",
        aleatorio: bool = False,
        accion: str = "",
        valor: int = None,
    ) -> str:
        """
        Controla la reproducción musical, búsquedas, saltos de pista y volumen exclusivo de la música.

        :param busqueda: Lo que el usuario quiere buscar o reproducir (canción, álbum o playlist).
        :param tipo: Filtro de búsqueda. Opciones: "cancion", "album", "playlist". (Por defecto: "cancion").
        :param aleatorio: True si se pide modo aleatorio o shuffle, False en caso contrario.
        :param accion: Acción multimedia si no es búsqueda. Opciones: "play", "pause", "toggle", "next", "previous", "volumen".
        :param valor: Número entero del 0 al 100 si la acción es "volumen".
        """
        cmd = f"python {self.script_path}"

        if busqueda:
            cmd += f" '{busqueda}' --tipo {tipo}"
            if aleatorio:
                cmd += " --aleatorio"
        elif accion:
            cmd += f" --accion {accion}"
            if valor is not None:
                cmd += f" --valor {valor}"

        try:
            ssh_cmd = [
                "ssh",
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "BatchMode=yes",
                f"{self.pc_user}@{self.pc_ip}",
                f"DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus {cmd}",
            ]
            result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                return f"Listo, señor. {result.stdout.strip()}"
            else:
                return f"Error ejecutando la orden en el host: {result.stderr.strip()}"

        except Exception as e:
            return f"Error de conexión SSH al host: {str(e)}"
