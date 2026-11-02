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
