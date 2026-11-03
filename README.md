

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
