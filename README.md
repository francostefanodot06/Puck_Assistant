<div align="center">
  <img src="Assets/Avatar%20de%20Puck.png" alt="Avatar de Puck" width="200"/>
  <h1>🤖 Puck - AI SysAdmin & Infrastructure Middleware</h1>
  <p><em>Asistente de administración inteligente impulsado por LLMs locales para el monitoreo, el diagnóstico y la consulta de un entorno Homelab (Proxmox / Docker).</em></p>
</div>

---

**Puck** no es un simple bot de notificaciones, es un *middleware inteligente* escrito en Python. Diseñado para operar como un Site Reliability Engineer (SRE) virtual, unifica la telemetría de Proxmox, Docker, Prometheus, las alertas de Grafana, los logs de Loki y el estado del stack multimedia en una sola API, pensada para que un LLM local la use como herramientas (*Function Calling*).

Aprovechando modelos de lenguaje locales ejecutados de forma 100% privada mediante **Ollama** e interactuando a través de **Open WebUI**, Puck es capaz de diagnosticar problemas y sugerir comandos de remediación. La API corre en un contenedor **LXC** de Proxmox con **FastAPI**.

> 👀 **El monitoreo es de solo lectura:** Puck consulta Proxmox, Docker, Grafana, Loki, Prometheus, Jellyfin y el stack de descargas, pero nunca ejecuta cambios en el homelab. Si hace falta modificar algo, propone el comando y lo ejecuta una persona. La única excepción es el módulo opcional de [música](#-control-de-música-opcional), que maneja un reproductor local.

<div align="center">
  <img src="Assets/Inicio%20de%20Puck.png" alt="Puck anunciando el inicio del monitoreo en Discord" width="900"/>
  <br/><em>Puck anuncia en Discord que el monitoreo está en línea.</em>
</div>

## 📑 Índice

- [Capacidades y arquitectura](#-capacidades-principales-y-arquitectura)
  - [1. Alertas proactivas](#1--pipeline-de-alertas-proactivas-grafana--loki--ia--discord)
  - [2. Reporte diario a Discord](#2--reporte-diario-a-discord)
  - [3. Asistencia operativa con Open WebUI](#3--asistencia-operativa-mediante-open-webui-tools)
- [Modelos (LLMs)](#-rendimiento-y-uso-de-modelos-llms)
- [Referencia de la API](#-referencia-de-la-api)
- [Estructura del repositorio](#-estructura-del-repositorio)
- [Instalación rápida](#️-instalación-rápida)
- [Seguridad](#-seguridad)
- [Stack tecnológico](#️-stack-tecnológico-y-librerías)
- [Roadmap](#️-roadmap)

---

## 🚀 Capacidades Principales y Arquitectura

El ecosistema de Puck se divide en tres piezas: un pipeline que recibe alertas y las explica en lenguaje natural, un reporte diario que se publica solo en Discord, y un conjunto de endpoints de consulta que Open WebUI expone al modelo como herramientas.

<div align="center">
  <img src="Assets/Arquitectura%20de%20Puck.png" alt="Diagrama de arquitectura de Puck" width="1000"/>
  <br/><em>Arquitectura general. El diagrama es editable: abrí <a href="Arquitectura%20de%20Puck.excalidraw"><code>Arquitectura de Puck.excalidraw</code></a> en <a href="https://excalidraw.com">Excalidraw</a>.</em>
</div>

### 1. 🚨 Pipeline de Alertas Proactivas (Grafana ➔ Loki ➔ IA ➔ Discord)

Puck actúa como el *Webhook Receiver* del stack de observabilidad del Homelab, traduciendo métricas frías en lenguaje natural y **correlacionándolas con los logs** del servicio afectado.

*   **Recepción:** un endpoint en **FastAPI** (`POST /alertas/discord`) captura los payloads JSON que dispara el Alertmanager de Grafana.
*   **Correlación con Loki:** Puck identifica el servicio de cada alerta a partir de sus *labels* (`LOKI_LABEL`, `job` o `container`) y trae hasta 10 líneas de error de los últimos 30 minutos, con los secretos enmascarados.
*   **Procesamiento AI:** la alerta y los logs se inyectan en un prompt estructurado y se consulta a la API local de Ollama (`qwen3:14b`).
*   **Notificación:** la IA resume el incidente en un máximo de 4 líneas, con tono profesional, y lo despacha a un canal privado de Discord mediante Webhooks. Si Ollama falla, Puck avisa por Discord del fallo.

**Reglas de Monitoreo en Grafana** (carpeta *Homelab*, grupo *HomeKing*, evaluación cada 1 minuto): CPU, RAM, espacio en discos, CPU al 85 %, GPU al 85 % y temperatura del M.2.

<div align="center">
  <img src="Assets/Alertas%20en%20Grafana.png" alt="Reglas de alerta en Grafana" width="900"/>
</div>

**Respuesta y Notificación de Puck en Discord:**

> 📸 **Evidencia:** Puck resume en lenguaje natural las alertas que dispara Grafana. Acá, dos alertas de prueba con su umbral y la indicación de revisar el enlace para confirmar si es un test o una situación real.

<div align="center">
  <img src="Assets/Puck%20alerta%20en%20Discord.png" alt="Puck resumiendo alertas de Grafana en Discord" width="900"/>
</div>

> 🔑 El contact point de Grafana debe enviar la API key: en el webhook, configurá el header de autorización con esquema `Bearer` y como credencial el valor de `API_KEY`.

---

### 2. 📰 Reporte Diario a Discord

`POST /homelab/reporte_diario` arma un informe consolidado y lo publica en Discord mediante el webhook. Está pensado para dispararse con una tarea programada (por ejemplo, un `cron` que llame al endpoint con la API key).

El reporte reúne en un solo mensaje:

*   **Proxmox:** CPU, RAM y uptime del nodo.
*   **Salud SMART** de cada disco físico.
*   **Stack de descargas:** avisos de Radarr, Sonarr y Prowlarr, y estado de Bazarr y qBittorrent.
*   **Watchtower:** novedades de imágenes y actualizaciones en las últimas 24 h.
*   **Backups `vzdump`:** últimos resultados.

Cada sección falla de forma independiente: si una consulta no responde, el reporte lo indica y sigue con el resto. El mensaje se recorta a ~1900 caracteres para respetar el límite de Discord.

> 📸 **Evidencia:** el reporte llegando al canal de Discord. El primer mensaje es el resumen corto; el segundo, el informe consolidado, que detecta indexers de Prowlarr caídos hace más de 6 horas.

<div align="center">
  <img src="Assets/Reporte%20diario%20en%20Discord.png" alt="Reporte diario de infraestructura de Puck en Discord" width="900"/>
</div>

---

### 3. 🧠 Asistencia Operativa mediante Open WebUI (Tools)

A través del sistema de *Tools* (Function Calling) de Open WebUI, Puck le otorga al modelo la capacidad de consultar la infraestructura en tiempo real. Cada capacidad es un endpoint con una sola responsabilidad:

| Tool | Qué puede consultar | Endpoint de Puck |
|---|---|---|
| `reporte_homelab` | Resumen general (nivel global del homelab) | `GET /homelab/resumen` |
| `consultar_proxmox` | CPU, RAM, uptime y uso de cada storage | `GET /proxmox/estado` |
| `listar_maquinas_virtuales` | VMs y CTs: estado, CPU y RAM | `GET /proxmox/vms` |
| `estado_smart_discos` | Salud SMART de los discos físicos | `GET /proxmox/discos` |
| `estado_backups_proxmox` | Historial de backups automáticos (`vzdump`) | `GET /proxmox/backups` |
| `docker_estado` | Contenedores caídos, `unhealthy` o en bucle de reinicio | `GET /docker/estado` |
| `estado_hardware_temperaturas` | Temperaturas por chip y estado del UPS (vía Prometheus) | `GET /hardware/estado` |
| `ver_incidencias_abiertas` | Memoria persistente de incidencias abiertas | `GET /incidencias/abiertas` |
| `consultar_grafana` | Alertas activas (*firing*) en Grafana | `GET /grafana/estado` |
| `estado_descargas_arr` | Radarr, Sonarr, Prowlarr, Bazarr y qBittorrent | `GET /homelab/arr` |
| `novedades_jellyfin` | Películas y episodios agregados últimamente a Jellyfin | `GET /multimedia/novedades` |
| `listar_servicios_con_logs` | Servicios con logs disponibles en Loki | `GET /loki/servicios` |
| `consultar_logs` | Logs recientes de un servicio | `GET /loki/logs` |
| `revisar_todos_los_logs` | Errores recientes de todos los servicios en una sola consulta | `GET /loki/todos` |
| `consultar_actualizaciones` | Actividad de Watchtower: imágenes nuevas y actualizaciones de contenedores | `GET /homelab/actualizaciones` |

> 🧾 El comportamiento del modelo (modo solo lectura, uso obligatorio de herramientas para el estado del homelab, anti-alucinación y troubleshooting incremental) se define con un **system prompt** cargado en el modelo de Open WebUI.

#### 📊 Telemetría y Monitoreo de Proxmox

Permite interactuar con la infraestructura mediante lenguaje natural (ej. *"¿Cómo está el servidor?"*). El backend se conecta a la API de **Proxmox VE** y extrae:

*   Consumo de recursos en vivo (CPU/RAM), uptime y uso de cada storage (ZFS, LVM, HDD y SSD).
*   Estado de cada VM y contenedor LXC.
*   **Salud SMART** de los discos físicos (NVMe y HDD).
*   **Historial de backups `vzdump`**: los últimos 5 con fecha, duración y resultado.

Las métricas de uso llegan con una etiqueta ya calculada (`[a vigilar]` desde 80 %, `[CRÍTICO]` desde 90 %), para que el modelo no tenga que interpretar los umbrales.

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

#### 🐳 Estado de Docker

`GET /docker/estado` consulta la API de Docker y clasifica cada contenedor: los que no están en ejecución, los `unhealthy` y los que se reinician en bucle aparecen primero como *PROBLEMA*, seguidos del resto. Se puede excluir contenedores con `DOCKER_IGNORAR` (por defecto, `portainer`).

> 📸 **Evidencia:** Puck lee el estado de los 14 contenedores y detecta que **Watchtower lleva 5 días detenido**: no falló, simplemente dejó de correr, y con eso se pierden las actualizaciones automáticas de imágenes. Además propone revisar sus logs para saber por qué salió.

<div align="center">
  <img src="Assets/docker%20estado.png" alt="Puck detectando un contenedor detenido en Docker" width="900"/>
</div>

#### 📥 Stack de Descargas

`GET /homelab/arr` revisa en una sola llamada:

*   **Radarr y Sonarr** (API `v3`) y **Prowlarr** (API `v1`): consulta su endpoint de `health` y reporta avisos y errores.
*   **Bazarr:** verifica que la API responda.
*   **qBittorrent:** verifica que la WebUI esté en línea. Requiere habilitar *Bypass de autenticación para clientes en la lista blanca de IPs* **solo para la IP del contenedor de Puck**.

Si falta la API key de algún servicio, el reporte lo indica en lugar de fallar.

> 📸 **Evidencia:** con un simple *"auditame el stack de descargas"*, el modelo llama a la tool `estado_descargas_arr` y resume los avisos: indexers de Prowlarr inaccesibles por más de 6 horas, que se propagan a Radarr y Sonarr.

<div align="center">
  <img src="Assets/Puck%20stack%20de%20descargas.png" alt="Puck auditando el stack de descargas" width="800"/>
</div>

#### 🎬 Novedades en Jellyfin

`GET /multimedia/novedades` devuelve las últimas películas y episodios agregados a la biblioteca (de 1 a 25, por fecha de incorporación). Sirve para responder *"¿qué hay de nuevo para ver?"* sin abrir la app.

> 📸 **Evidencia:** Puck detecta que acaba de entrar una tanda de 10 episodios de una serie y aclara que no hay películas nuevas.

<div align="center">
  <img src="Assets/Nuevas%20adiciones%20jelly.png" alt="Puck informando las novedades de Jellyfin" width="900"/>
</div>

#### 🌡️ Hardware: Temperaturas y UPS

`GET /hardware/estado` consulta **Prometheus** (node_exporter + NUT) y devuelve la temperatura máxima por chip y el estado del UPS: voltaje de batería, carga y si el equipo está funcionando con red eléctrica o con batería. Los límites por tipo de sensor se ajustan en `LIMITE_TEMP` (CPU 80 °C, NVMe 70 °C, HDD 50 °C por defecto); se marcan `[a vigilar]` al superarlos y `[CRÍTICO]` con 10 °C de margen extra.

#### 🗂️ Memoria de Incidencias

Puck no solo responde cuando se le pregunta: un **proceso en segundo plano** revisa el homelab cada 5 minutos (`INTERVALO_S`) y guarda lo que encuentra en una base **SQLite** (`/var/lib/puck/puck.db`).

*   **Incidencias:** cada problema detectado (alerta activa, contenedor caído, `unhealthy` o en reinicio, temperatura sobre el límite) se abre una sola vez, con su severidad y la fecha de apertura, y se cierra solo cuando el problema desaparece. Así, `GET /incidencias/abiertas` responde *"¿qué está roto ahora y desde cuándo?"* sin repetir el mismo aviso en cada consulta.
*   **Histórico de métricas:** CPU, RAM, uso de cada storage y temperaturas se registran en cada ciclo y se conservan 90 días (`RETENCION_METRICAS_DIAS`), la base para análisis de tendencias.
*   **Tolerante a fallos:** si una fuente (Docker o Prometheus) no responde durante un ciclo, sus incidencias abiertas se conservan en lugar de cerrarse por error.

> 📸 **Evidencia:** el modelo consulta la memoria persistente, que está vacía, y aun así distingue entre el *log formal* de incidencias y los puntos que conviene vigilar (un storage al 89 %, la GPU a 79 °C, Watchtower detenido e indexers fallando).

<div align="center">
  <img src="Assets/Puck%20memoria%20de%20incidencias.png" alt="Puck consultando su memoria de incidencias" width="800"/>
</div>

#### 🪵 Consulta de Logs con Loki (solo lectura)

Puck consulta **Loki** mediante LogQL para entender qué pasó antes (o durante) una alerta. Filtra solo errores o muestra todo, en una ventana de 1 a 180 minutos. Para una revisión general, `GET /loki/todos` consulta todos los servicios en paralelo y devuelve un resumen compacto.

*   **Límites:** máximo 40 líneas por consulta y 300 caracteres por línea (la revisión general se acota a unos 6500 caracteres en total).
*   **Servicio validado:** el nombre se compara contra la lista real de Loki antes de armar la consulta LogQL.
*   **Redacción de secretos:** cada línea pasa por un filtro que enmascara valores de `password`, `token`, `secret`, `api_key` y `Authorization`.

> 📸 **Evidencia 1:** listado de servicios con logs disponibles en Loki.

<div align="center">
  <img src="Assets/Loki%20servicios.png" alt="Servicios con logs disponibles en Loki" width="900"/>
</div>

> 📸 **Evidencia 2:** con un simple *"Revisame todos"*, Puck lanzó **12 consultas** de logs en una sola respuesta y devolvió un diagnóstico por servicio, con problema, causas probables y recomendación.

<div align="center">
  <img src="Assets/Loki%20diagnostico%201.png" alt="Diagnóstico de logs, parte 1" width="900"/>
  <br/><br/>
  <img src="Assets/Loki%20diagnostico%202.png" alt="Diagnóstico de logs, parte 2" width="900"/>
</div>

> 🐛 **Puck detectó un bug de su propio ecosistema:** Open WebUI recibía un `404` al pedir `/v1/audio/voices` al endpoint de TTS. Justo el tipo de problema que pasa desapercibido hasta que alguien lee los logs.

#### 🔄 Actualizaciones de Contenedores (Watchtower)

`GET /homelab/actualizaciones` lee en Loki los logs de **Watchtower** de las últimas 24 horas y devuelve las 15 líneas más recientes, para saber qué imágenes nuevas se detectaron o qué contenedores se actualizaron. Requiere que Watchtower tenga logs en Loki bajo el valor `watchtower` de `LOKI_LABEL`.

> ℹ️ Un resultado vacío significa *"Watchtower no registró nada"*, no necesariamente *"todo está al día"*: si Watchtower está detenido, tampoco habrá logs. Conviene cruzarlo con `/docker/estado`, como en el ejemplo de arriba.

#### 🧭 Resumen General

`GET /homelab/resumen` devuelve un panorama rápido: CPU y RAM de Proxmox y las alertas activas de Grafana, con un nivel global 🟢 `OK`, 🟡 `A VIGILAR` o 🔴 `CRÍTICO`. Los umbrales se configuran con `UMBRAL_VIGILAR` y `UMBRAL_CRITICO`.

#### 🎵 Control de Música (opcional)

Un módulo aparte, pensado para correr en el equipo que reproduce el audio, deja que el modelo ponga música desde **Navidrome** (compatible con Feishin y cualquier cliente Subsonic):

*   `puck_music.py`: script que busca canciones, álbumes o playlists en Navidrome y los reproduce con `mpv`. Admite modo aleatorio y acciones de `play`, `pause`, `stop`, `next`, `previous`, `volumen` y `actual` (qué está sonando).
*   `tool-gestor_de_navidrome_y_feishin.py`: tool de Open WebUI que le envía el pedido al backend (`POST /musica/control`) y normaliza lo que el modelo suele mandar mal (acciones en español, tipos inválidos).

---

## 📈 Rendimiento y Uso de Modelos (LLMs)

El procesamiento cognitivo recae en modelos de peso medio/alto, ejecutados localmente para garantizar una latencia mínima y asegurar que la topología de la red y las IPs internas nunca se expongan a servicios de terceros.

| Uso | Modelo |
|---|---|
| Resumen de alertas (webhook) y asistente principal | `qwen3:14b` |
| Perfil alternativo "Libre Puck" en Open WebUI | variante de ~27B cuantizada (IQ3) |

Durante el desarrollo se probaron también `qwen3.5:9b`, `qwen3:8b`, `hermes3` y `llama3.2`.

> 📸 **Evidencia:** más de 5.2 M de tokens acumulados en Open WebUI durante el desarrollo y las pruebas, con un pico de 1.1 M en un solo día y una racha de 10 días seguidos de uso.

<div align="center">
  <img src="Assets/Uso.png" alt="Métricas de uso de tokens en Open WebUI" width="900"/>
</div>

---

## 🔌 Referencia de la API

**Todas las rutas requieren** el header `Authorization: Bearer <API_KEY>`.

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/alertas/discord` | Recibe alertas de Grafana, las correlaciona con logs de Loki, las resume con IA y las envía a Discord |
| `POST` | `/homelab/reporte_diario` | Arma el reporte consolidado (Proxmox, SMART, descargas, Watchtower, backups) y lo publica en Discord |
| `GET` | `/homelab/resumen` | Nivel global (OK / A VIGILAR / CRÍTICO) con Proxmox y Grafana |
| `GET` | `/proxmox/estado` | Estado del nodo y de los storages |
| `GET` | `/proxmox/vms` | VMs y CTs: estado, CPU y RAM |
| `GET` | `/proxmox/discos` | Salud SMART de los discos físicos |
| `GET` | `/proxmox/backups` | Últimos 5 backups `vzdump` |
| `GET` | `/docker/estado` | Contenedores con problemas y estado del resto |
| `GET` | `/hardware/estado` | Temperaturas por chip y estado del UPS (Prometheus) |
| `GET` | `/incidencias/abiertas` | Incidencias abiertas en la memoria persistente |
| `GET` | `/grafana/estado` | Alertas activas en Grafana |
| `GET` | `/homelab/arr` | Salud de Radarr, Sonarr, Prowlarr, Bazarr y qBittorrent |
| `GET` | `/homelab/actualizaciones` | Actividad de Watchtower en las últimas 24 h (vía Loki) |
| `GET` | `/multimedia/novedades?limite=` | Últimos elementos agregados a Jellyfin (1 a 25) |
| `GET` | `/loki/servicios` | Servicios con logs disponibles |
| `GET` | `/loki/logs?servicio=&minutos=&solo_errores=` | Logs recientes de un servicio |
| `GET` | `/loki/todos?minutos=&solo_errores=` | Revisión rápida de todos los servicios en paralelo |
| `POST` | `/musica/control` | Control de música (módulo opcional) |

---

## 📁 Estructura del Repositorio

```text
Puck_Assistant/
├── Puck_Assistant.py                        # API principal (FastAPI): Proxmox, Loki, stack de descargas, reporte diario
├── puck_extra.py                            # Módulo extra: Docker, Jellyfin, hardware/UPS, incidencias y proceso en segundo plano
├── puck_music.py                            # Reproductor para Navidrome (mpv), módulo opcional
├── tool-control_pc.py                       # Tools de Open WebUI para consultar la infraestructura
├── tool-gestor_de_navidrome_y_feishin.py    # Tool de Open WebUI para el control de música
├── Arquitectura de Puck.excalidraw          # Diagrama de arquitectura editable
└── Assets/                                  # Capturas y diagramas usados en este README
```

---

## ⚙️ Instalación Rápida

Pensado para correr en un contenedor LXC (Debian/Ubuntu) con acceso de red a Proxmox, Grafana, Loki, Prometheus, Ollama, Docker, Jellyfin y el stack de descargas.

```bash
git clone https://github.com/francostefanodot06/Puck_Assistant.git /opt/Puck_Assistant
cd /opt/Puck_Assistant
python3 -m venv venv
./venv/bin/pip install fastapi uvicorn requests
```

1. **Configurá** los valores del bloque de configuración de `Puck_Assistant.py` y de `puck_extra.py`: Proxmox, Grafana, Ollama, Discord, API keys del stack de descargas y de Jellyfin, Docker, Prometheus, qBittorrent y, sobre todo, **`API_KEY`** (cambiala por una clave larga y aleatoria). `LOKI_URL` y `LOKI_LABEL` se leen de variables de entorno.
2. **Proxmox:** creá un usuario y un token con el rol `PVEAuditor` (solo lectura).
3. **Base de datos:** la memoria de incidencias usa SQLite. Creá el directorio y dale permisos al usuario del servicio:
   ```bash
   mkdir -p /var/lib/puck && chown puck: /var/lib/puck
   ```
4. **Levantá el servicio:**
   ```bash
   ./venv/bin/uvicorn Puck_Assistant:app --host 0.0.0.0 --port 8000
   ```
   O como servicio de systemd:
   ```ini
   # /etc/systemd/system/puck.service
   [Unit]
   Description=Puck API
   After=network-online.target
   Wants=network-online.target

   [Service]
   User=puck
   WorkingDirectory=/opt/Puck_Assistant
   Environment=LOKI_URL=http://IP_DE_LOKI:3100
   ExecStart=/opt/Puck_Assistant/venv/bin/uvicorn Puck_Assistant:app --host 0.0.0.0 --port 8000
   Restart=on-failure

   [Install]
   WantedBy=multi-user.target
   ```
5. **Grafana:** creá un *contact point* de tipo Webhook apuntando a `http://IP_DE_PUCK:8000/alertas/discord`, con el header de autorización `Bearer` y la misma API key.
6. **qBittorrent:** en *Opciones → WebUI*, habilitá el bypass de autenticación para la IP del contenedor de Puck (solo esa IP, `/32`).
7. **Docker:** apuntá `DOCKER_URL` a un proxy de solo lectura del socket (por ejemplo, [`docker-socket-proxy`](https://github.com/Tecnativa/docker-socket-proxy) con solo `CONTAINERS=1`), no al socket expuesto directamente. Ver [Seguridad](#-seguridad).
8. **Reporte diario (opcional):** programá una llamada diaria, por ejemplo con `cron`:
   ```bash
   0 9 * * * curl -s -X POST -H "Authorization: Bearer TU_API_KEY" http://IP_DE_PUCK:8000/homelab/reporte_diario
   ```
9. **Open WebUI:** en *Workspace → Tools*, pegá los scripts de tools y completá la IP de Puck, el puerto y la API key. Cargá además el system prompt en el modelo que uses con Puck.

---

## 🔒 Seguridad

*   **Monitoreo de solo lectura:** el backend únicamente hace consultas `GET` a Proxmox, Docker, Grafana, Loki, Prometheus, Jellyfin, el stack de descargas y qBittorrent. Ningún endpoint de monitoreo modifica el homelab. Lo único que escribe Puck es en su propia base SQLite y en el webhook de Discord.
*   **Autenticación por API key:** todas las rutas exigen `Authorization: Bearer <API_KEY>`, comparada en tiempo constante. Con `API_KEY` vacía, todo responde `401`.
*   **Loki validado:** el servicio pedido se valida contra la lista real de Loki antes de armar la consulta LogQL, las respuestas se limitan en cantidad y tamaño, y los secretos se enmascaran.
*   **Logs como datos no confiables:** el system prompt de Puck indica ignorar cualquier instrucción que aparezca dentro de logs, alertas o respuestas de herramientas (defensa contra *prompt injection*).
*   **Tokens mínimos:** token de Proxmox con rol `PVEAuditor` y bypass de qBittorrent limitado a la IP del contenedor.
*   **API de Docker:** el puerto `2375` no tiene autenticación y equivale a acceso root al host. Exponelo solo a través de un proxy de solo lectura y limitado a la IP de Puck.
*   **Módulo de música:** es el único que actúa sobre una máquina (reproduce y detiene `mpv`); es opcional y se puede omitir sin afectar al resto.
*   **Sin TLS:** la API corre sobre HTTP, así que la API key viaja en claro. Puck debe correr solo en red local, detrás de una VPN (Tailscale) o de un reverse proxy con HTTPS.

---

## 🛠️ Stack Tecnológico y Librerías

El backend está construido sobre **Python 3**, utilizando un enfoque modular:

**Backend, APIs y Comunicación:**
*   `fastapi` & `uvicorn`: framework y servidor para el receptor de webhooks y la API de tools.
*   `requests`: orquestación HTTP/REST con APIs externas (Proxmox, Ollama, Discord Webhooks, Grafana Alertmanager, Loki, Prometheus, Docker, Jellyfin, *arr y qBittorrent).
*   `sqlite3` (biblioteca estándar): memoria de incidencias e histórico de métricas.
*   **Proxmox API:** peticiones mediante *API Tokens* para extraer telemetría, SMART y backups sin exponer credenciales de administrador.

**Observabilidad:**
*   **Grafana + Prometheus:** métricas, temperaturas, UPS y reglas de alerta.
*   **Loki (LogQL):** logs centralizados de los contenedores del Homelab.

**Integración IA:**
*   **Ollama:** inferencia local de los modelos.
*   **Open WebUI Tools:** scripts Python inyectados dinámicamente en la interfaz web que habilitan el *Function Calling* para los modelos de Ollama.

**Multimedia (opcional):**
*   **Jellyfin** para las novedades de la biblioteca y **Navidrome** (API Subsonic) + `mpv` para la música.

---

## 🗺️ Roadmap

Puck seguirá siendo un **observador**: todo lo que sigue es de solo lectura.

**Hecho**
- [x] Autenticación por API key en todos los endpoints
- [x] Correlación automática de alertas con logs de Loki
- [x] Salud SMART de discos y estado de backups `vzdump`
- [x] Integración del stack de descargas (Radarr, Sonarr, Prowlarr, Bazarr, qBittorrent), incluida la detección de indexers caídos
- [x] Consulta de logs con Loki, revisión general y redacción de secretos
- [x] Seguimiento de actualizaciones de contenedores con Watchtower
- [x] Reporte diario consolidado a Discord (Proxmox, SMART, descargas, Watchtower y backups)
- [x] Estado de contenedores Docker (caídos, `unhealthy`, en reinicio)
- [x] Temperaturas y UPS desde Prometheus
- [x] Bitácora de incidentes (SQLite) e histórico de métricas
- [x] Novedades de Jellyfin
- [x] Control de música con Navidrome

**Próximos pasos**
- [ ] Sumar discos, backups, stack de descargas y errores de Loki a `/homelab/resumen`
- [ ] Reporte diario con anti-repetición (no repetir avisos ya reportados)
- [ ] Aviso de respaldo con el detalle crudo de la alerta cuando Ollama no responde
- [ ] SMART detallado: desgaste de NVMe y temperatura
- [ ] Predicción de días hasta que se llene un disco, a partir del histórico de métricas
- [ ] Cola de descargas (qBittorrent, Sonarr, Radarr)
- [ ] Chequeos de disponibilidad de servicios (HTTP/TCP)
- [ ] Detección de problemas recurrentes a partir de la bitácora de incidentes
- [ ] Registro de auditoría de cada llamada a la API
- [ ] Entrada de voz con Whisper y *wake word*

---

*Nota de Seguridad: Las credenciales, URLs de Webhooks y Tokens de API deben gestionarse mediante variables de entorno y nunca subirse al repositorio.*
