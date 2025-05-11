import os
import json
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Header, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from app.rag_pipeline import build_chain
from app.onedrive_sync import sync_documents, SNAPSHOT_FILE
from app.chat_chains import get_chain_for_user, CHAT_CHAINS, CHAT_MEMORY
from app.callbacks import StreamingHandler
from app.cors_config import ALLOWED_ORIGINS

load_dotenv()

# LangSmith config
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")

# FastAPI app
app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Función de validación de API key
def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    expected_key = os.getenv("API_KEY")
    if x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

# Inicialización del RAG
chain = build_chain()

# Sincronización periódica
@app.on_event("startup")
def startup_event():
    scheduler = BackgroundScheduler()
    scheduler.add_job(sync_documents, 'interval', minutes=10)
    scheduler.start()

# Consulta normal
@app.get("/query")
async def query(
    question: str = Query(..., description="La pregunta del usuario"),
    chat_id: str = Query("default", description="ID único del usuario/conversación"),
    auth: str = Depends(verify_api_key)
):
    try:
        chain = get_chain_for_user(chat_id)
        response = chain.invoke({"question": question})
        
        # 🔍 Capturar documentos usados
        docs = response.get("source_documents", [])
        print("🔍 Documentos recuperados:")
        for i, doc in enumerate(docs):
            print(f"{i+1}. Fuente: {doc.metadata.get('source')}")
            print(doc.page_content[:200])
        sources = list({doc.metadata.get("source", "desconocido") for doc in docs})

        return {
            "answer": response["answer"],
            "sources": sources
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Consulta con stream (opcional)
@app.get("/query/stream")
async def stream_query(
    question: str = Query(...),
    chat_id: str = Query("default"),
    auth: str = Depends(verify_api_key)
):
    try:
        handler = StreamingHandler(user_question=question)
        chain = get_chain_for_user(chat_id, callback=handler)

        async def token_stream():
            await chain.ainvoke({"question": question})
            await handler.end()
            async for token in handler.stream_tokens():
                yield token

        return StreamingResponse(token_stream(), media_type="text/plain")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Reiniciar memoria del usuario
@app.post("/chat/reset")
async def reset_memory(
    chat_id: str = Query(..., description="ID único del usuario/conversación"),
    auth: str = Depends(verify_api_key)
):
    if chat_id in CHAT_MEMORY:
        del CHAT_MEMORY[chat_id]
    if chat_id in CHAT_CHAINS:
        del CHAT_CHAINS[chat_id]
    return {"status": f"Memoria reiniciada para chat_id='{chat_id}'"}

# Forzar sincronización manual
@app.get("/sync")
async def manual_sync(auth: str = Depends(verify_api_key)):
    try:
        sync_documents()
        return {"status": "Sync triggered"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Ver estado de snapshot (sin protección)
@app.get("/status")
async def get_status():
    try:
        if not os.path.exists(SNAPSHOT_FILE):
            return {"documents": 0, "last_sync": None}

        with open(SNAPSHOT_FILE, "r") as f:
            snapshot = json.load(f)

        num_docs = len(snapshot)
        last_dates = list(snapshot.values())
        last_sync = max(last_dates) if last_dates else None

        return {
            "documents": num_docs,
            "last_sync": last_sync
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Ping de salud (sin protección)
@app.get("/health")
async def health_check():
    return {"status": "ok"}
