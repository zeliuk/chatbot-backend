# 🧠 RAG Conversacional Backend – FastAPI + LangChain + OneDrive

Este backend permite consultas conversacionales sobre documentos almacenados en OneDrive, integrando LangChain, OpenAI y ChromaDB.  
Incluye protección por API Key, memoria por usuario (`chat_id`) y soporte para streaming.

---

## 🚀 Funcionalidades

| Endpoint            | Descripción                                      |
|---------------------|--------------------------------------------------|
| `GET /query`        | Consulta al RAG con historial por `chat_id`      |
| `GET /query/stream` | (Opcional) Respuesta token a token (stream)     |
| `POST /chat/reset`  | Reinicia la memoria para el `chat_id`           |
| `GET /sync`         | Sincroniza documentos desde carpeta de OneDrive |
| `GET /status`       | Muestra número de documentos y última sync      |
| `GET /health`       | Devuelve `{"status": "ok"}` si la app está viva |

📌 Todos los endpoints (excepto `/status` y `/health`) requieren autenticación por header `X-API-Key`.

---

## 🔐 Seguridad por API Key

Añade en tu `.env`:

```env
API_KEY=mi_super_clave_secreta
```

Y luego en Postman o el frontend, usa el header:

```
X-API-Key: mi_super_clave_secreta
```

---

## 🧠 Memoria conversacional por usuario

Cada `chat_id` tiene su propia memoria.  
Puedes resetearla con:

```http
POST /chat/reset?chat_id=usuario123
```

---

## 📄 Sincronización de documentos (OneDrive)

Los documentos válidos son:

- `.pdf`
- `.docx`
- `.txt`

La app solo re-indexa los documentos nuevos, modificados o eliminados.

---

## 🧱 Estructura del proyecto

```
.
├── app/
│   ├── main.py               # Entrypoint FastAPI
│   ├── chat_chains.py        # RAG + memoria por chat_id
│   ├── callbacks.py          # Streaming token a token
│   ├── rag_pipeline.py       # Lógica principal del RAG
│   ├── vectorstore.py        # ChromaDB local
│   ├── onedrive_sync.py      # Integración con OneDrive
│   ├── cors_config.py        # Orígenes permitidos por entorno
├── snapshot.json             # Metadatos de sincronización
├── .env                      # Variables sensibles
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
```

---

## 🔧 Variables de entorno (`.env`)

```env
OPENAI_API_KEY=sk-...
API_KEY=mi_super_clave_secreta

O365_CLIENT_ID=...
O365_CLIENT_SECRET=...
O365_TENANT_ID=...
ONEDRIVE_DRIVE_ID=...
ONEDRIVE_FOLDER_PATH=/CHATBOT/conocimiento_chatbot_py

CHROMA_PERSIST_DIRECTORY=./chroma_db
LANGCHAIN_PROJECT=ChatbotHelefante
LANGCHAIN_API_KEY=...
```

---

## 🐳 Docker

```bash
docker-compose up --build
```

---

## 🌐 CORS

Define orígenes permitidos en `app/cors_config.py`:

```python
ALLOWED_ORIGINS = [
    "http://localhost:3000",        # Desarrollo local
    "https://tufrontend.com"        # Producción
]
```

---

## 📊 Observabilidad con LangSmith

Este backend envía trazas a [LangSmith](https://smith.langchain.com) para inspeccionar inputs, outputs y documentos utilizados por el modelo.

---

## 🧩 Stack tecnológico

- FastAPI
- LangChain
- OpenAI (GPT-4o-mini)
- ChromaDB
- OneDrive (O365)
- Docker
