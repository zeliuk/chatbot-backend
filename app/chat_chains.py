import os
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from .vectorstore import get_vectorstore

# Diccionarios para cachear memoria y cadenas por chat_id
CHAT_CHAINS = {}
CHAT_MEMORY = {}

def get_chain_for_user(chat_id: str, callback=None):
    # Obtener o crear la memoria asociada a este chat_id
    if chat_id in CHAT_MEMORY:
        memory = CHAT_MEMORY[chat_id]
    else:
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        CHAT_MEMORY[chat_id] = memory

    # Si no se requiere streaming y ya tenemos una chain cacheada, reutilizarla
    if chat_id in CHAT_CHAINS and callback is None:
        return CHAT_CHAINS[chat_id]

    # Recuperar vectorstore y definir prompt personalizado
    vectorstore = get_vectorstore()

    prompt_template = """
Eres un asistente útil. Usa el historial de conversación y los documentos para responder.
Si no sabes algo, puedes decirlo directamente.

Historial de conversación:
{chat_history}

Contexto:
{context}

Pregunta:
{question}
    """.strip()

    prompt = PromptTemplate.from_template(prompt_template)

    # Instanciar modelo OpenAI
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
        streaming=True if callback else False,
        callbacks=[callback] if callback else None
    )

    # Crear la cadena con memoria y prompt
    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
        memory=memory,
        combine_docs_chain_kwargs={"prompt": prompt}
    )

    # Guardar en cache si no es streaming
    if callback is None:
        CHAT_CHAINS[chat_id] = chain

    return chain
