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
