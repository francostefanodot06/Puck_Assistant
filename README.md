
> 📸 **Evidencia 1:** listado de servicios con logs disponibles (*bazarr, cadvisor, excalidraw, flaresolverr, grafana, homepage, loki, open-webui, prometheus, prowlarr, radarr, sonarr*).

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

#### 🧭 Resumen General

`GET /homelab/resumen` devuelve un panorama rápido: CPU y RAM de Proxmox y las alertas activas de Grafana, con un nivel global 🟢 `OK`, 🟡 `A VIGILAR` o 🔴 `CRÍTICO`. Los umbrales se configuran con `UMBRAL_VIGILAR` y `UMBRAL_CRITICO`.

---

## 📈 Rendimiento y Uso de Modelos (LLMs)

El procesamiento cognitivo recae en modelos de peso medio/alto (como `qwen3:14b`), ejecutados localmente para garantizar una latencia mínima y asegurar que la topología de la red y las IPs internas nunca se expongan a servicios de terceros. Durante el desarrollo se probaron también `qwen3.5:9b`, `qwen3:8b`, `hermes3` y `llama3.2`.

> 📸 **Evidencia:** más de 2.8 M de tokens acumulados en Open WebUI durante el desarrollo y las pruebas.

<div align="center">
  <img src="Assets/Uso.png" alt="Métricas de uso de tokens en Open WebUI" width="900"/>
</div>

---

## 🔌 Referencia de la API

**Todas las rutas requieren** el header `Authorization: Bearer <API_KEY>`.

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/alertas/discord` | Recibe alertas de Grafana, las correlaciona con logs de Loki, las resume con IA y las envía a Discord |
| `GET` | `/homelab/resumen` | Nivel global (OK / A VIGILAR / CRÍTICO) con Proxmox y Grafana |
| `GET` | `/proxmox/estado` | Estado del nodo y de los storages |
| `GET` | `/proxmox/vms` | VMs y CTs: estado, CPU y RAM |
| `GET` | `/proxmox/discos` | Salud SMART de los discos físicos |
| `GET` | `/proxmox/backups` | Últimos 5 backups `vzdump` |
| `GET` | `/grafana/estado` | Alertas activas en Grafana |
| `GET` | `/homelab/arr` | Salud de Radarr, Sonarr, Prowlarr, Bazarr y qBittorrent |
| `GET` | `/loki/logs?servicio=&minutos=&solo_errores=` | Logs recientes de un servicio |
| `GET` | `/loki/todos?minutos=&solo_errores=` | Revisión rápida de todos los servicios en paralelo |

---

## ⚙️ Instalación Rápida

Pensado para correr en un contenedor LXC (Debian/Ubuntu) con acceso de red a Proxmox, Grafana, Loki, Ollama y el stack de descargas.

```bash
git clone https://github.com/francostefanodot06/Puck_Assistant.git /opt/Puck_Assistant
cd /opt/Puck_Assistant
python3 -m venv venv
./venv/bin/pip install fastapi uvicorn requests
```

1. **Configurá** los valores del bloque de configuración de `Puck_Assistant.py`: Proxmox, Grafana, Ollama, Discord, API keys del stack de descargas, qBittorrent y, sobre todo, **`API_KEY`** (cambiala por una clave larga y aleatoria). `LOKI_URL` y `LOKI_LABEL` se leen de variables de entorno.
2. **Proxmox:** creá un usuario y un token con el rol `PVEAuditor` (solo lectura).
3. **Levantá el servicio:**

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

4. **Grafana:** creá un *contact point* de tipo Webhook apuntando a `http://IP_DE_PUCK:8000/alertas/discord`, con el header de autorización `Bearer` y la misma API key.
5. **qBittorrent:** en *Opciones → WebUI*, habilitá el bypass de autenticación para la IP del contenedor de Puck (solo esa IP, `/32`).
6. **Open WebUI:** en *Workspace → Tools*, pegá los scripts de tools y completá la IP de Puck, el puerto y la API key. Cargá además el system prompt en el modelo que uses con Puck.

---

## 🔒 Seguridad

*   **Solo lectura:** el backend únicamente hace consultas `GET` a Proxmox, Grafana, Loki, el stack de descargas y qBittorrent. No existe ningún endpoint que modifique el homelab.
*   **Autenticación por API key:** todas las rutas exigen `Authorization: Bearer <API_KEY>`, comparada en tiempo constante. Con `API_KEY` vacía, todo responde `401`.
*   **Loki validado:** el servicio pedido se valida contra la lista real de Loki antes de armar la consulta LogQL, las respuestas se limitan en cantidad y tamaño, y los secretos se enmascaran.
*   **Logs como datos no confiables:** el system prompt de Puck indica ignorar cualquier instrucción que aparezca dentro de logs, alertas o respuestas de herramientas (defensa contra *prompt injection*).
*   **Tokens mínimos:** token de Proxmox con rol `PVEAuditor` y bypass de qBittorrent limitado a la IP del contenedor.
*   **Sin TLS:** la API corre sobre HTTP, así que la API key viaja en claro. Puck debe correr solo en red local, detrás de una VPN (Tailscale) o de un reverse proxy con HTTPS.

---

## 🛠️ Stack Tecnológico y Librerías

El backend está construido sobre **Python 3**, utilizando un enfoque modular:

**Backend, APIs y Comunicación:**
*   `fastapi` & `uvicorn`: framework y servidor para el receptor de webhooks y la API de tools.
*   `requests`: orquestación HTTP/REST con APIs externas (Proxmox, Ollama, Discord Webhooks, Grafana Alertmanager, Loki, *arr y qBittorrent).
*   **Proxmox API:** peticiones mediante *API Tokens* para extraer telemetría, SMART y backups sin exponer credenciales de administrador.

**Observabilidad:**
*   **Grafana + Prometheus:** métricas y reglas de alerta.
*   **Loki (LogQL):** logs centralizados de los contenedores del Homelab.

**Integración IA:**
*   **Ollama:** inferencia local de los modelos.
*   **Open WebUI Tools:** scripts Python inyectados dinámicamente en la interfaz web que habilitan el *Function Calling* para los modelos de Ollama.

---

## 🗺️ Roadmap

Puck seguirá siendo un **observador**: todo lo que sigue es de solo lectura.

**Hecho**
- [x] Autenticación por API key en todos los endpoints
- [x] Correlación automática de alertas con logs de Loki
- [x] Salud SMART de discos y estado de backups `vzdump`
- [x] Integración del stack de descargas (Radarr, Sonarr, Prowlarr, Bazarr, qBittorrent)
- [x] Consulta de logs con Loki, revisión general y redacción de secretos

**Próximos pasos**
- [ ] Resumen completo: sumar discos, backups, stack de descargas y errores de Loki a `/homelab/resumen`
- [ ] Reporte proactivo a Discord (briefing matutino) con anti-repetición
- [ ] Aviso de respaldo con el detalle crudo de la alerta cuando Ollama no responde
- [ ] SMART detallado: desgaste de NVMe y temperatura
- [ ] Métricas de Prometheus de solo lectura (consultas PromQL predefinidas): contenedores caídos y predicción de días hasta que se llene un disco
- [ ] Cola de descargas (qBittorrent, Sonarr, Radarr) e indexadores caídos
- [ ] Chequeos de disponibilidad de servicios (HTTP/TCP)
- [ ] Bitácora de incidentes para detectar problemas recurrentes
- [ ] Registro de auditoría de cada llamada a la API
- [ ] Entrada de voz con Whisper y *wake word*

---

*Nota de Seguridad: Las credenciales, URLs de Webhooks y Tokens de API deben gestionarse mediante variables de entorno y nunca subirse al repositorio.*
