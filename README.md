# Asistente CRM / Secretario local $0

MVP local para registrar notas comerciales, follow-ups, tareas, archivos Excel y audios, con costo operativo cero como prioridad.

> No usar con información confidencial real de clientes ni información interna bancaria hasta revisión de Compliance/InfoSec.

## Arquitectura

- FastAPI + Jinja para una web local.
- SQLite en `data/assistant.db`.
- Archivos en `data/uploads`.
- Parser local por reglas en español rioplatense, sin llamadas externas.
- Transcripción local simulada por defecto. Se puede reemplazar por faster-whisper local.
- Integración WhatsApp preparada solo como diseño defensivo: con `STRICT_ZERO_COST=true` se bloquea cualquier envío que pueda generar costo.

## Por qué mantiene costo $0

- No usa OpenAI API ni otros LLMs remotos en runtime.
- No usa Twilio, Zapier, Make, hosting cloud ni bases cloud.
- Corre en tu computadora.
- No requiere tarjeta de crédito.
- WhatsApp queda apagado por defecto y bloqueado en modo estricto.

Limitación deliberada: sin modelos locales instalados, el parsing es heurístico y la transcripción de audio es simulada. Para audios reales, instalá una transcripción local como faster-whisper y conectala en `app/services/transcription.py`.

## Instalación

```powershell
scripts\setup.ps1
```

## Correr la app

```powershell
scripts\run.ps1
```

Abrí [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Resumen diario manual

```powershell
.\.venv\Scripts\python.exe scripts\generate_daily_summary.py
```

## Scheduler local

```powershell
.\.venv\Scripts\python.exe scripts\run_scheduler.py
```

Genera el resumen a la hora definida en `.env`, por defecto 08:00 en `America/Argentina/Buenos_Aires`.

## Tests

```powershell
scripts\test.ps1
```

## Comandos en la UI

- `/cliente Cliente A`
- `/pendientes`
- `/hoy`
- `/semana`
- `/pipeline`
- `/resumen`
- `/buscar texto`
- `/revisar ambiguos`
- `/whatsapp-test`

## Excel esperado

El importador detecta columnas como:

- cliente
- empresa
- monto
- etapa
- fecha
- comentario
- próximo paso

## Borrar datos locales

```powershell
.\.venv\Scripts\python.exe scripts\clear_local_data.py
```

Esto borra la base SQLite y uploads locales. No toca el código.

## WhatsApp

El MVP no envía WhatsApp automáticamente. Si `STRICT_ZERO_COST=true`, cualquier intento de `send_whatsapp` se bloquea. WhatsApp Business Cloud API puede tener modo test, pero producción puede generar cargos según conversación, plantillas y país. Por eso este proyecto deja el resumen disponible para copiar/pegar desde la UI.
