# 🤖 Puck - Asistente de Infraestructura y Automatización

**Puck** es un middleware inteligente y asistente de administración escrito en Python, diseñado para orquestar, monitorear y automatizar las operaciones diarias de un entorno Homelab basado en Proxmox, así como controlar funciones del entorno de escritorio (Desktop).

Aprovechando modelos de lenguaje locales (LLMs vía Ollama) a través de **Open WebUI**, Puck unifica la telemetría del sistema, las notificaciones de emergencia y la ejecución de comandos en una sola interfaz conversacional y de APIs.

## 🚀 Capacidades Principales

El proyecto se divide en dos grandes módulos funcionales: **El Servidor FastAPI (Backend de Alertas)** y **Las Tools de Open WebUI (Interacción y Control)**.

### 1. 🚨 Pipeline de Alertas Inteligentes (Grafana ➔ Discord)
Puck actúa como un *webhook receiver* para el stack de observabilidad del Homelab.
* **Recepción:** Un endpoint en FastAPI recibe los payloads JSON crudos desde el Alertmanager de Grafana.
* **Procesamiento AI:** El script se comunica con la API de Ollama para interpretar los datos técnicos (ej. uso de RAM, discos llenos, temperaturas de CPU/GPU).
* **Notificación:** Formatea y despacha un parte de incidente detallado y legible hacia un canal privado de Discord mediante Webhooks.

### 2. 🧠 Integración con Open WebUI (Tools Script)
Mediante el sistema de *Tools* de Open WebUI, Puck le otorga al modelo de lenguaje (LLM) la capacidad de ejecutar código Python en tiempo real para consultar o modificar la infraestructura y la PC local:

*   **📊 Monitoreo de Proxmox (API):** 
    Permite preguntarle al LLM: *"¿Cómo está el servidor?"*. El script se conecta a la API de Proxmox VE para extraer el estado de los Nodos, el consumo de recursos en vivo y el estatus de los contenedores LXC/Máquinas Virtuales.
*   **💻 Control de Escritorio y Multimedia:**
    Automatización de la estación de trabajo principal. A través del chat, se puede ordenar la apertura o cierre de aplicaciones específicas, o controlar la reproducción multimedia (Play/Pause, subir/bajar volumen).
*   **🔍 Consultas de Telemetría On-Demand:**
    Capacidad de consultar el estado de las alertas directamente a la API de Grafana sin salir de la interfaz de chat.

---

## 🛠️ Stack Tecnológico y Librerías

El ecosistema de Puck está construido sobre **Python 3** y utiliza las siguientes tecnologías clave:

### Backend y APIs
*   **`fastapi` & `uvicorn`**: Framework asíncrono de alto rendimiento para levantar el servidor que recibe los webhooks de Grafana.
*   **`requests`**: Para la comunicación HTTP/REST con las APIs externas (Ollama, Discord Webhooks, Grafana).
*   **`proxmoxer`**: (O peticiones HTTP directas) para interactuar con la API REST de Proxmox y extraer telemetría del clúster.

### Automatización de PC (Desktop)
*   **`os` / `subprocess`**: Librerías nativas de Python para la ejecución de comandos del sistema operativo (abrir/matar procesos de aplicaciones).
*   **`pyautogui` / `keyboard`**: (O equivalentes según el OS) para la simulación de teclas multimedia y automatización de la interfaz de usuario.

### Integración IA
*   **Open WebUI Tools**: Scripts inyectados directamente en la interfaz web que le otorgan funciones (functions calling) a los modelos locales descargados en Ollama.

---

