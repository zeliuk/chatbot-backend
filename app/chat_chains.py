import os
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from .vectorstore import get_vectorstore

CHAT_CHAINS = {}

def get_chain_for_user(chat_id: str, callback=None):
    if chat_id in CHAT_CHAINS and callback is None:
        return CHAT_CHAINS[chat_id]

    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )

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

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
        streaming=True if callback else False,
        callbacks=[callback] if callback else None
    )

    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
        memory=memory,
        combine_docs_chain_kwargs={"prompt": prompt}
    )

    # Solo cacheamos si no es streaming (callback = None)
    if callback is None:
        CHAT_CHAINS[chat_id] = chain

    return chain
