y las envía a Discord |
| `GET` | `/homelab/resumen` | Resumen global (Proxmox, Grafana, máquinas y Loki) con nivel OK / A VIGILAR / CRÍTICO |
| `POST` | `/reporte/discord?minimo=&forzar=` | Envía el resumen a Discord, con filtro por nivel y anti-repetición de 6 h |
| `GET` | `/proxmox/estado` | Estado del nodo y de los storages |
| `GET` | `/proxmox/vms` | VMs y CTs: estado, CPU y RAM |
| `GET` | `/grafana/estado` | Alertas activas en Grafana |
| `GET` | `/loki/servicios` | Servicios con logs disponibles |
| `GET` | `/loki/logs?servicio=&minutos=&solo_errores=` | Logs recientes de un servicio |
| `GET` | `/loki/todos?minutos=&solo_errores=` | Revisión rápida de todos los servicios en paralelo |
| `POST` | `/ejecutar/{app}` · `/cerrar/{app}` | Abre o cierra una app de la lista blanca |
| `POST` | `/media/{accion}` | `play`, `pause`, `play-pause`, `next`, `previous`, `stop`, `volume-up`, `volume-down` |
| `POST` | `/musica/control` | Busca y reproduce desde Navidrome, o ejecuta una acción (`play`, `pause`, `next`, `volumen`, `actual`…) |
| `POST` | `/v1/audio/speech` | TTS compatible con OpenAI (Piper) |

---

## ⚙️ Instalación Rápida

```bash
git clone https://github.com/francostefanodot06/Puck_Assistant.git
cd Puck_Assistant
pip install fastapi uvicorn requests

export PUCK_API_KEY="una-clave-larga-y-aleatoria"
uvicorn Puck_Assistant:app --host 0.0.0.0 --port 8000
```

**Dependencias del sistema** (para el control de escritorio y la música): `mpv`, `playerctl`, `pipewire` (`wpctl`), `pactl` y [Piper](https://github.com/rhasspy/piper) para la voz.

1. **Configurá** los valores `TU_*` de `Puck_Assistant.py` (Proxmox, Grafana, Ollama, Discord, Piper). `PUCK_API_KEY`, `LOKI_URL` y `LOKI_LABEL` se leen desde variables de entorno. Sin `PUCK_API_KEY`, todas las rutas responden `401`.
2. **Grafana:** creá un *contact point* de tipo Webhook apuntando a `http://IP_DE_PUCK:8000/alertas/discord`, con el header de autorización `Bearer` y la misma API key.
3. **Open WebUI:** en *Workspace → Tools*, pegá los scripts de tools y completá la IP de la PC, el puerto de Puck y la API key.
4. **Voz (opcional):** en *Ajustes → Audio*, motor *OpenAI* con URL `http://IP_DE_PUCK:8000/v1` y voz `puck`.
5. **Música (opcional):** copiá `puck_music.py` a la PC de escritorio, completá los datos de Navidrome y ajustá la ruta del script en el endpoint `/musica/control`.
6. **Reportes (opcional):** programá `POST /reporte/discord` con cron o un timer de systemd (ver arriba).

**Como servicio de usuario (ejemplo):** como Puck controla el escritorio, conviene correrlo dentro de tu sesión con `systemd --user`:

```ini
# ~/.config/systemd/user/puck.service
[Unit]
Description=Puck Assistant
After=graphical-session.target

[Service]
EnvironmentFile=%h/.config/puck/env      # contiene PUCK_API_KEY=...
WorkingDirectory=%h/Puck_Assistant
ExecStart=/usr/bin/uvicorn Puck_Assistant:app --host 0.0.0.0 --port 8000
Restart=on-failure

[Install]
WantedBy=default.target
```

---

## 🔒 Seguridad

*   **Autenticación por API key:** todas las rutas exigen `Authorization: Bearer <PUCK_API_KEY>`, comparada en tiempo constante. Si la variable no está definida, todo responde `401`.
*   **Lista blanca de comandos:** solo se pueden abrir o cerrar las apps definidas en `COMANDOS_PERMITIDOS`; el resto devuelve `403`.
*   **Loki validado y de solo lectura:** el servicio pedido se valida contra la lista real de Loki antes de armar la consulta LogQL, las respuestas se limitan en cantidad y tamaño, y los secretos se enmascaran.
*   **Logs como datos no confiables:** cada respuesta de logs advierte al LLM que no obedezca instrucciones que aparezcan dentro (defensa contra *prompt injection*).
*   **Tokens mínimos:** usá un token de Proxmox de solo lectura (rol `PVEAuditor`), nunca uno de `root`.
*   **Sin TLS:** la API corre sobre HTTP, así que la API key viaja en claro. Puck debe correr solo en red local, detrás de una VPN o de un reverse proxy con HTTPS.

---

## 🛠️ Stack Tecnológico y Librerías

El backend está construido sobre **Python 3**, utilizando un enfoque modular:

**Backend, APIs y Comunicación:**
*   `fastapi` & `uvicorn`: framework y servidor para el receptor de webhooks y la API de tools.
*   `requests`: orquestación HTTP/REST con APIs externas (Ollama, Discord Webhooks, Grafana Alertmanager, Loki).
*   **Proxmox API:** peticiones mediante *API Tokens* para extraer telemetría del clúster sin exponer credenciales de administrador.

**Observabilidad:**
*   **Grafana + Prometheus:** métricas y reglas de alerta.
*   **Loki (LogQL):** logs centralizados de los contenedores del Homelab.

**Automatización de SO y Audio:**
*   `os` / `subprocess`: librerías nativas para la manipulación de procesos del sistema operativo.
*   `playerctl` / `pactl` / `wpctl` / `mpv`: control multimedia en Wayland, con **Navidrome** como biblioteca musical.
*   **Piper TTS:** motor de Text-to-Speech neuronal de ejecución local.

**Integración IA:**
*   **Ollama:** inferencia local de los modelos.
*   **Open WebUI Tools:** scripts Python inyectados dinámicamente en la interfaz web que habilitan el *Function Calling* para los modelos de Ollama.

---

## 🗺️ Roadmap

Puck seguirá siendo un **observador**: todo lo que sigue es de solo lectura.

**Hecho**
- [x] Autenticación por API key en todos los endpoints
- [x] Resumen global del homelab con niveles (OK / A VIGILAR / CRÍTICO)
- [x] Reporte proactivo a Discord con anti-repetición
- [x] Consulta de logs con Loki, revisión general de todos los servicios y redacción de secretos

**Próximos pasos**
- [ ] Endpoint `GET /v1/audio/voices` (detectado por el propio Puck en los logs)
- [ ] Briefing matutino programado (el endpoint ya existe; falta el timer)
- [ ] Correlación automática: al llegar una alerta, adjuntar los logs recientes del servicio afectado
- [ ] Aviso de respaldo con el detalle crudo de la alerta cuando Ollama no responde
- [ ] Métricas de Prometheus de solo lectura (consultas PromQL predefinidas): contenedores caídos, CPU/RAM por contenedor y predicción de días hasta que se llene un disco
- [ ] Estado de los backups de Proxmox (¿corrió el último? ¿falló?)
- [ ] Salud de discos (SMART y temperatura) vía API de Proxmox
- [ ] Estado del stack *arr (Sonarr, Radarr, Prowlarr, Bazarr): salud, cola e indexadores caídos
- [ ] Chequeos de disponibilidad de servicios (HTTP/TCP)
- [ ] Bitácora de incidentes para detectar problemas recurrentes
- [ ] Registro de auditoría de cada llamada a la API
- [ ] Entrada de voz con Whisper y *wake word*

---

*Nota de Seguridad: Las credenciales, URLs de Webhooks y Tokens de API deben gestionarse mediante variables de entorno y nunca subirse al repositorio.*
