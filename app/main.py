import os
import json
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from apscheduler.schedulers.background import BackgroundScheduler

from app.rag_pipeline import build_chain
from app.onedrive_sync import sync_documents, SNAPSHOT_FILE
from app.chat_chains import get_chain_for_user
from app.callbacks import StreamingHandler

load_dotenv()

# LangSmith
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")

app = FastAPI()
chain = build_chain()

@app.on_event("startup")
def startup_event():
    scheduler = BackgroundScheduler()
    scheduler.add_job(sync_documents, 'interval', minutes=10)
    scheduler.start()

@app.get("/query")
async def query(
    question: str = Query(..., description="La pregunta del usuario"),
    chat_id: str = Query("default", description="ID único del usuario/conversación")
):
    try:
        chain = get_chain_for_user(chat_id)
        response = chain.invoke({"question": question})
        return {"answer": response["answer"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/query/stream")
async def stream_query(
    question: str = Query(..., description="La pregunta del usuario"),
    chat_id: str = Query("default", description="ID único del usuario/conversación")
):
    try:
        handler = StreamingHandler()
        chain = get_chain_for_user(chat_id, callback=handler)

        async def token_stream():
            await chain.ainvoke({"question": question})
            async for token in handler.stream_tokens():
                yield token

        return StreamingResponse(token_stream(), media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sync")
async def manual_sync():
    try:
        sync_documents()
        return {"status": "Sync triggered"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

@app.get("/health")
async def health_check():
    return {"status": "ok"}
