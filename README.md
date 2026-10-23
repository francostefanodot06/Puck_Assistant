<div align="center">
  <img src="Assets/Avatar%20de%20Puck.png" alt="Avatar de Puck" width="200"/>
  <h1>🤖 Puck - AI SysAdmin & Infrastructure Middleware</h1>
  <p><em>Asistente de administración inteligente impulsado por LLMs locales para la orquestación, monitoreo y automatización de un entorno Homelab (Proxmox / Docker).</em></p>
</div>

---

**Puck** no es un simple bot de notificaciones, es un *middleware inteligente* escrito en Python. Diseñado para operar como un Site Reliability Engineer (SRE) virtual, Puck unifica la telemetría del sistema, la gestión de incidentes y la ejecución de comandos de infraestructura en una sola interfaz conversacional y de APIs. 

Aprovechando modelos de lenguaje locales (LLMs) ejecutados de forma 100% privada mediante **Ollama** e interactuando a través de **Open WebUI**, este asistente es capaz de diagnosticar problemas, sugerir comandos de remediación y controlar funciones nativas del entorno de escritorio (Desktop/Wayland).

![Inicio de Puck](Assets/Inicio%20de%20Puck.png)

---

## 🚀 Capacidades Principales y Arquitectura

El ecosistema de Puck se divide en dos grandes módulos funcionales que operan en simultáneo: un backend asíncrono para el manejo de emergencias y un motor de *Function Calling* para la asistencia operativa.

### 1. 🚨 Pipeline de Alertas Proactivas (Grafana ➔ Discord)
Puck actúa como el *Webhook Receiver* definitivo para el stack de observabilidad del Homelab, traduciendo métricas frías en lenguaje natural.

*   **Recepción:** Un endpoint dedicado en **FastAPI** captura los payloads JSON crudos disparados por el Alertmanager de Grafana.
*   **Procesamiento AI:** El script inyecta los datos técnicos (ej. uso de RAM, discos llenos, temperaturas de CPU/GPU) en un prompt estructurado y consulta a la API local de Ollama.
*   **Notificación y Enrutamiento:** La IA formatea el incidente y despacha un reporte detallado, con personalidad de mayordomo, hacia un canal privado de Discord mediante Webhooks.

**Reglas de Monitoreo en Grafana:**
![Alertas en Grafana](Assets/Alertas%20en%20Grafana.png)

**Respuesta y Notificación de Puck en Discord:**
![Puck alerta en Discord](Assets/Puck%20alerta%20en%20Discord.png)

---

### 2. 🧠 Asistencia Operativa mediante Open WebUI (Tools)
A través del sistema de *Tools* (Function Calling) de Open WebUI, Puck le otorga al modelo de lenguaje la capacidad de ejecutar código Python en tiempo real para auditar o modificar la infraestructura:

#### 📊 Telemetría y Monitoreo de Proxmox
Permite interactuar con la infraestructura mediante lenguaje natural (ej. *"¿Cómo está el servidor?"*). El script se conecta directamente a la API de **Proxmox VE** para extraer el estado de los nodos, el consumo de recursos en vivo (CPU/RAM) y el estatus del almacenamiento ZFS/LVM.

![Consulta a Puck](Assets/Consulta%20a%20Puck%20mediante%20Open%20Webui.png)

#### 🔧 Troubleshooting y Resolución de Incidentes
Cuando se detecta una anomalía (como un disco al límite de su capacidad), Puck no solo reporta el problema, sino que es capaz de consultar a Grafana On-Demand y proporcionar los comandos exactos de `bash` y `LVM` (`lvdisplay`, `lvextend`, `resize2fs`) necesarios para mitigar el incidente directamente en el servidor.

![Resolución de incidentes](Assets/Consulta%20a%20Puck%20mediante%20Open%20Webui%202.png)

#### 💻 Control de Escritorio y Multimedia (Desktop Automation)
Automatización profunda de la estación de trabajo principal (Linux/Wayland). A través del chat o comandos HTTP, se puede ordenar la apertura, cierre o interrupción (kill) de aplicaciones específicas (Brave, Terminal, Steam), así como controlar la reproducción multimedia a bajo nivel utilizando `wpctl`, `pactl` y `playerctl`.

---

## 📈 Rendimiento y Uso de Modelos (LLMs)

El procesamiento cognitivo recae en modelos de peso medio/alto (como `qwen3:14b`), los cuales son ejecutados localmente para garantizar una latencia mínima y asegurar que la topología de la red y las IPs internas nunca se expongan a servicios de terceros.

![Métricas de Uso](Assets/Uso.png)

---

## 🛠️ Stack Tecnológico y Librerías

El backend está construido sobre **Python 3**, utilizando un enfoque modular:

**Backend, APIs y Comunicación:**
*   `fastapi` & `uvicorn`: Framework asíncrono de altísimo rendimiento para levantar el servidor receptor de webhooks.
*   `requests`: Para la orquestación HTTP/REST con APIs externas (Ollama, Discord Webhooks, Grafana Alertmanager).
*   **Proxmox API:** Peticiones seguras mediante *API Tokens* (`root@pam`) para extraer telemetría del clúster sin exponer credenciales de administrador.

**Automatización de SO y Audio:**
*   `os` / `subprocess`: Librerías nativas para la manipulación de procesos del sistema operativo e inyección de comandos en terminal.
*   **Piper TTS:** Motor de Text-to-Speech neuronal de ejecución local para generar respuestas de voz ultra-rápidas a partir de las inferencias del LLM.

**Integración IA:**
*   **Open WebUI Tools:** Scripts Python inyectados dinámicamente en la interfaz web que habilitan el *Function Calling* para los modelos de Ollama.

---
*Nota de Seguridad: Todas las credenciales, URLs de Webhooks y Tokens de API se gestionan estrictamente mediante variables de entorno para garantizar un despliegue seguro y auditable.*
