# Asistente CRM / Secretario local $0

MVP local para registrar notas comerciales, follow-ups, tareas, archivos Excel y audios, con costo operativo cero como prioridad.

> No usar con información confidencial real de clientes ni información interna bancaria hasta revisión de Compliance/InfoSec.

## Arquitectura

- FastAPI + Jinja para una web local.
- SQLite en `data/assistant.db`.
- Archivos en `data/uploads`.
- Parser local por reglas en español rioplatense, sin llamadas externas.
- Transcripción local simulada por defecto. Se puede reemplazar por faster-whisper local.
- Telegram Bot API por long polling para usarlo desde el celular sin hosting.
- Integración WhatsApp preparada solo como diseño defensivo: con `STRICT_ZERO_COST=true` se bloquea cualquier envío que pueda generar costo.

## Por qué mantiene costo $0

- No usa OpenAI API ni otros LLMs remotos en runtime.
- No usa Twilio, Zapier, Make, hosting cloud ni bases cloud.
- Corre en tu computadora.
- No requiere tarjeta de crédito.
- Telegram usa Bot API oficial y long polling local.
- WhatsApp queda apagado por defecto y bloqueado en modo estricto.

Limitación deliberada: sin modelos locales instalados, el parsing es heurístico y la transcripción de audio es simulada. Para audios reales, instalá una transcripción local como faster-whisper y conectala en `app/services/transcription.py`.

## Instalación

```powershell
scripts\setup.ps1
```

## Correr la app web

```powershell
scripts\run.ps1
```

Abrí [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Telegram desde el celular

Telegram es el canal recomendado para el MVP móvil con costo operativo $0.

1. En Telegram, abrí `@BotFather`.
2. Mandá `/newbot` y seguí los pasos.
3. Copiá el token del bot.
4. En `.env`, configurá:

```env
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=tu_token_de_botfather
OWNER_TELEGRAM_USER_ID=
```

5. Corré:

```powershell
scripts\run_telegram_bot.ps1
```

6. Escribile `/start` al bot desde Telegram.

Si `OWNER_TELEGRAM_USER_ID` está vacío, el bot acepta mensajes de cualquier usuario que conozca el bot. Para cerrarlo solo a vos, mandale un mensaje al bot: si no estás autorizado, te responde tu `user_id`. Pegá ese número en `OWNER_TELEGRAM_USER_ID`.

Desde Telegram podés mandar:

- notas comerciales en texto libre;
- comandos como `/pendientes`, `/hoy`, `/pipeline`, `/resumen`;
- notas de voz;
- archivos Excel con pipeline;
- documentos para guardar y revisar.

Importante: los mensajes pasan por Telegram. No usar información confidencial real de clientes ni información interna bancaria hasta validación de Compliance/InfoSec.

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

## Comandos

- `/cliente Cliente A`
- `/pendientes`
- `/hoy`
- `/semana`
- `/pipeline`
- `/resumen`
- `/buscar texto`
- `/revisar ambiguos`
- `/revisar_ambiguos`
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

El MVP no envía WhatsApp automáticamente. Si `STRICT_ZERO_COST=true`, cualquier intento de `send_whatsapp` se bloquea. WhatsApp Business Cloud API puede tener modo test, pero producción puede generar cargos según conversación, plantillas y país. Por eso este proyecto deja el resumen disponible para copiar/pegar desde la UI o usar Telegram como canal móvil gratuito.
