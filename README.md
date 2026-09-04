# Odisha Kaju AI Sales Assistant

24×7 WhatsApp AI sales assistant for Odisha Kaju / Jyotsna Enterprises.

## Features
- WhatsApp Cloud API webhook
- OpenAI Responses API
- Price / stock / MOQ database
- Owner approval queue for discounts, credit, complaints and sensitive decisions
- Customer conversation history
- Test endpoint at `/simulate`

## Railway start command
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## Required environment variables
`OPENAI_API_KEY`, `OPENAI_MODEL`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN`, `META_GRAPH_VERSION`, `DB_PATH`.

Do not commit secret keys to this repository.
