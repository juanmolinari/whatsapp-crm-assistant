# Asistente CRM / Secretario local $0

MVP local para registrar notas comerciales, follow-ups, tareas, archivos Excel y audios, con costo operativo cero como prioridad.

> No usar con información confidencial real de clientes ni información interna bancaria hasta revisión de Compliance/InfoSec.

## Arquitectura

- FastAPI + Jinja para una web local.
- SQLite en `data/assistant.db`.
- Archivos en `data/uploads`.
- Parser local por reglas en español rioplatense, sin llamadas externas.
- Telegram Bot API por long polling para usarlo desde el celular sin hosting.
- Transcripción local con `faster-whisper` opcional, sin APIs pagas.
- Integración WhatsApp preparada solo como diseño defensivo: con `STRICT_ZERO_COST=true` se bloquea cualquier envío que pueda generar costo.

## Por qué mantiene costo $0

- No usa OpenAI API ni otros LLMs remotos en runtime.
- No usa Twilio, Zapier, Make, hosting cloud ni bases cloud.
- Corre en tu computadora.
- No requiere tarjeta de crédito.
- Telegram usa Bot API oficial y long polling local.
- La transcripción corre localmente con `faster-whisper`.
- WhatsApp queda apagado por defecto y bloqueado en modo estricto.

Limitación deliberada: sin modelos locales instalados, el parsing es heurístico. Para audios reales, el proyecto soporta `faster-whisper` local sin APIs pagas.

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

## Notas de voz reales

Para transcribir notas de voz localmente, instalá el paquete opcional:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-audio.txt
```

En `.env`, usá:

```env
LOCAL_TRANSCRIPTION_PROVIDER=faster-whisper
LOCAL_TRANSCRIPTION_MODEL=base
```

La primera nota de voz puede tardar porque descarga el modelo local. No usa OpenAI API ni servicios pagos. Si querés algo más liviano, podés usar `LOCAL_TRANSCRIPTION_MODEL=tiny`; si querés más precisión, probá `small`.

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
