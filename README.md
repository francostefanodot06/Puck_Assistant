<div align="center">
  <img src="Assets/Avatar%20de%20Puck.png" alt="Avatar de Puck" width="200"/>
  <h1>🤖 Puck - AI SysAdmin & Infrastructure Middleware</h1>
  <p><em>Asistente de administración inteligente impulsado por LLMs locales para el monitoreo, el diagnóstico y los reportes de un entorno Homelab (Proxmox / Docker), con control de escritorio (Linux/Wayland).</em></p>
</div>

---

**Puck** no es un simple bot de notificaciones, es un *middleware inteligente* escrito en Python. Diseñado para operar como un Site Reliability Engineer (SRE) virtual, Puck unifica la telemetría del sistema, la consulta de logs y los reportes proactivos en una sola interfaz conversacional y de APIs, y además controla funciones nativas del escritorio.

Aprovechando modelos de lenguaje locales (LLMs) ejecutados de forma 100% privada mediante **Ollama** e interactuando a través de **Open WebUI**, este asistente es capaz de diagnosticar problemas y sugerir comandos de remediación.

> 👀 **Sobre el homelab, Puck es de solo lectura:** mira, diagnostica y avisa. Nunca ejecuta cambios por su cuenta. Las únicas acciones que realiza son locales a la PC de escritorio (abrir/cerrar apps de una lista blanca y controlar la música).

<div align="center">
  <img src="Assets/Inicio%20de%20Puck.png" alt="Puck anunciando el inicio del monitoreo en Discord" width="900"/>
  <br/><em>Puck anuncia en Discord que el monitoreo está en línea.</em>
</div>

---

## 🚀 Capacidades Principales y Arquitectura

El ecosistema de Puck se divide en módulos que operan en simultáneo: un backend **FastAPI** que recibe alertas y genera reportes, y un motor de *Function Calling* (Open WebUI Tools) para la asistencia operativa.

<div align="center">
  <img src="Assets/Arquitectura%20de%20Puck.png" alt="Diagrama de arquitectura de Puck" width="1000"/>
  <br/><em>Arquitectura general. El diagrama es editable: abrí <a href="Assets/Arquitectura%20de%20Puck.excalidraw"><code>Arquitectura de Puck.excalidraw</code></a> en <a href="https://excalidraw.com">Excalidraw</a>.</em>
</div>

### 1. 🚨 Pipeline de Alertas Proactivas (Grafana ➔ Discord)

Puck actúa como el *Webhook Receiver* del stack de observabilidad del Homelab, traduciendo métricas frías en lenguaje natural.

*   **Recepción:** un endpoint en **FastAPI** (`POST /alertas/discord`) captura los payloads JSON que dispara el Alertmanager de Grafana.
*   **Procesamiento AI:** el payload se inyecta en un prompt estructurado y se consulta a la API local de Ollama.
*   **Notificación:** la IA resume el incidente en un máximo de 3 líneas, con personalidad de mayordomo, y se despacha a un canal privado de Discord mediante Webhooks. Si Ollama no responde, Puck avisa por Discord del fallo.

**Reglas de Monitoreo en Grafana** (carpeta *Homelab*, grupo *HomeKing*, evaluación cada 1 minuto): CPU, RAM, espacio en discos, CPU al 85 %, GPU al 85 % y temperatura del M.2.

<div align="center">
  <img src="Assets/Alertas%20en%20Grafana.png" alt="Reglas de alerta en Grafana" width="900"/>
</div>

**Respuesta y Notificación de Puck en Discord:**

> 📸 **Evidencia:** Puck resume en lenguaje natural las alertas que dispara Grafana. Acá, dos alertas de prueba con su umbral y la indicación de revisar el enlace para confirmar si es un test o una situación real.

<div align="center">
  <img src="Assets/Puck%20alerta%20en%20Discord.png" alt="Puck resumiendo alertas de Grafana en Discord" width="900"/>
</div>

> 🔑 El contact point de Grafana debe enviar la API key: en el webhook, configurá el header de autorización con esquema `Bearer` y como credencial el valor de `PUCK_API_KEY`.

---

### 2. 📋 Resumen y Reportes Proactivos del Homelab

Además de reaccionar a alertas, Puck puede **armar un panorama completo** del homelab en una sola consulta (`GET /homelab/resumen`). El resumen combina:

*   **Proxmox:** CPU, RAM, uptime y discos que superaron los umbrales.
*   **Grafana:** alertas activas (*firing*).
*   **Máquinas:** cuántas VMs/CTs corren y cuáles están detenidas.
*   **Loki:** servicios con errores en los últimos 15 minutos.

Con eso calcula un **nivel global**: 🟢 `OK`, 🟡 `A VIGILAR` (desde 80 %) o 🔴 `CRÍTICO` (desde 90 %, o cualquier alerta de Grafana activa). Los umbrales son configurables (`UMBRAL_VIGILAR`, `UMBRAL_CRITICO`).

`POST /reporte/discord` envía ese resumen a Discord y admite dos parámetros:

*   `minimo` (`ok` | `vigilar` | `critico`): solo envía si el nivel alcanza ese mínimo.
*   `forzar` (`true`): ignora el filtro anti-repetición.

**Anti-repetición:** con `minimo=vigilar` o `critico`, el mismo estado no se vuelve a avisar durante 6 horas, así que se puede programar seguido sin spamear el canal.

**Ejemplo de programación (cron):**

```bash
# Briefing diario a las 9:00 (siempre envía)
0 9 * * * curl -s -X POST -H "Authorization: Bearer TU_API_KEY" "http://IP_DE_PUCK:8000/reporte/discord?minimo=ok"

# Cada 30 min: solo si hay algo a vigilar o crítico (sin repetir el mismo aviso)
*/30 * * * * curl -s -X POST -H "Authorization: Bearer TU_API_KEY" "http://IP_DE_PUCK:8000/reporte/discord?minimo=vigilar"
```

---

### 3. 🧠 Asistencia Operativa mediante Open WebUI (Tools)

A través del sistema de *Tools* (Function Calling) de Open WebUI, Puck le otorga al modelo de lenguaje la capacidad de ejecutar código Python en tiempo real para auditar la infraestructura. Cada tool tiene una sola responsabilidad y autentica contra el backend con la API key:

| Tool | Qué hace | Endpoint de Puck |
|---|---|---|
| `reporte_homelab` | Resumen general: Proxmox, Grafana, máquinas y errores de Loki | `GET /homelab/resumen` |
| `estado_proxmox` | CPU, RAM, uptime, storages y detalle de VMs/CTs | `GET /proxmox/estado` · `GET /proxmox/vms` |
| `consultar_grafana` | Alertas activas (*firing*) en Grafana | `GET /grafana/estado` |
| `listar_servicios_con_logs` | Servicios con logs disponibles en Loki | `GET /loki/servicios` |
| `consultar_logs` | Logs recientes de un servicio | `GET /loki/logs` |
| *(revisión general de logs)* | Errores recientes de todos los servicios en una sola consulta | `GET /loki/todos` |
| `abrir_aplicacion` / `cerrar_aplicacion` | Abre o cierra apps de una lista blanca | `POST /ejecutar/{app}` · `POST /cerrar/{app}` |
| `reproducir_musica` | Busca y reproduce desde Navidrome; pausa, siguiente, volumen y "qué suena" | `POST /musica/control` |

#### 📊 Telemetría y Monitoreo de Proxmox

Permite interactuar con la infraestructura mediante lenguaje natural (ej. *"¿Cómo está el servidor?"*). El backend se conecta a la API de **Proxmox VE** para extraer el consumo de recursos en vivo (CPU/RAM), el uptime, el uso de cada storage (ZFS, LVM, HDD y SSD) y el estado de cada VM/CT. Cada métrica llega con una etiqueta ya calculada (`[a vigilar]` / `[CRÍTICO]`) para que el modelo no tenga que interpretar los umbrales.

> 📸 **Evidencia:** Puck consulta Proxmox, interpreta los datos y marca qué discos merecen atención (en este caso, el HDD-1TB al 76 %).

<div align="center">
  <img src="Assets/Consulta%20a%20Puck%20mediante%20Open%20Webui.png" alt="Puck informando el estado del servidor Proxmox" width="900"/>
</div>

#### 🔧 Troubleshooting y Resolución de Incidentes

Cuando se detecta una anomalía (como un disco al límite de su capacidad), Puck no solo reporta el problema: cruza el dato con las alertas de Grafana y propone acciones concretas, desde encontrar qué ocupa espacio (`df`, `du`) hasta migrar datos a otro storage o expandir el volumen con LVM (`lvdisplay`, `lvextend`, `resize2fs`).

> ⚠️ Los comandos son **orientativos**: Puck usa rutas genéricas que hay que adaptar al entorno real, y nunca ejecuta cambios por su cuenta.

> 📸 **Evidencia:** respuesta de Puck ante el HDD-1TB casi lleno, con las opciones de remediación.

<div align="center">
  <img src="Assets/Consulta%20a%20Puck%20mediante%20Open%20Webui%202.png" alt="Puck sugiriendo acciones para un disco casi lleno" width="900"/>
</div>

#### 🪵 Consulta de Logs con Loki (solo lectura)

Puck consulta **Loki** mediante LogQL para entender qué pasó antes (o durante) una alerta. El flujo tiene dos pasos: primero descubre qué servicios tienen logs, y después trae los más recientes, filtrando solo errores o mostrando todo, en una ventana de 1 a 180 minutos. Para una revisión general, `GET /loki/todos` consulta todos los servicios en paralelo y devuelve un resumen compacto.

*   **Límites:** máximo 40 líneas por consulta y 300 caracteres por línea (la revisión general se acota a unos 6500 caracteres en total).
*   **Redacción de secretos:** antes de salir, cada línea pasa por un filtro que enmascara valores de `password`, `token`, `secret`, `api_key` y `Authorization`.

> 📸 **Evidencia 1:** listado de servicios con logs disponibles (*bazarr, cadvisor, excalidraw, flaresolverr, grafana, homepage, loki, open-webui, prometheus, prowlarr, radarr, sonarr*).

<div align="center">
  <img src="Assets/Loki%20servicios.png" alt="Servicios con logs disponibles en Loki" width="900"/>
</div>

> 📸 **Evidencia 2:** con un simple *"Revisame todos"*, Puck lanzó **12 consultas** a `consultar_logs` en una sola respuesta y devolvió un diagnóstico por servicio, con problema, causas probables y recomendación.

<div align="center">
  <img src="Assets/Loki%20diagnostico%201.png" alt="Diagnóstico de logs, parte 1" width="900"/>
  <br/><br/>
  <img src="Assets/Loki%20diagnostico%202.png" alt="Diagnóstico de logs, parte 2" width="900"/>
</div>

> 🐛 **Puck detectó un bug de su propio ecosistema:** Open WebUI recibía un `404` al pedir `/v1/audio/voices` al endpoint de TTS del backend. Justo el tipo de problema que pasa desapercibido hasta que alguien lee los logs.

#### 💻 Control de Escritorio y Multimedia (Desktop Automation)

Automatización de la estación de trabajo principal (Linux/Wayland). A través del chat o comandos HTTP, se puede ordenar la apertura o el cierre de aplicaciones de una **lista blanca** (Discord, Konsole, Brave, Zen Browser, Feishin, Steam, Dolphin, Heroic Games), así como controlar la reproducción multimedia a bajo nivel utilizando `wpctl`, `pactl` y `playerctl`.

La música se busca en **Navidrome** (canciones, álbumes y playlists, con modo aleatorio) y se reproduce con **mpv**, regulando el volumen solo del reproductor. El backend ejecuta `puck_music.py` de forma local en la misma PC (ya no hace falta SSH), y el script también permite consultar qué está sonando.

#### 🗣️ Voz Local (Piper TTS)

El endpoint `POST /v1/audio/speech` es compatible con la API de TTS de OpenAI, por lo que Open WebUI puede usarlo directamente. Detrás corre **Piper**, con varias voces en español (incluida la voz `puck`), 100% local.

---

## 📈 Rendimiento y Uso de Modelos (LLMs)

El procesamiento cognitivo recae en modelos de peso medio/alto (como `qwen3:14b`), los cuales son ejecutados localmente para garantizar una latencia mínima y asegurar que la topología de la red y las IPs internas nunca se expongan a servicios de terceros. Durante el desarrollo se probaron también `qwen3.5:9b`, `qwen3:8b`, `hermes3` y `llama3.2`.

> 📸 **Evidencia:** más de 2.8 M de tokens acumulados en Open WebUI durante el desarrollo y las pruebas.

<div align="center">
  <img src="Assets/Uso.png" alt="Métricas de uso de tokens en Open WebUI" width="900"/>
</div>

---

## 🔌 Referencia de la API

**Todas las rutas requieren** el header `Authorization: Bearer <PUCK_API_KEY>`.

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/alertas/discord` | Recibe alertas de Grafana, las resume con IA y las envía a Discord |
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
