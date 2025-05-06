from langchain.chains import ConversationalRetrievalChain
from langchain_openai import ChatOpenAI
from .memory import get_memory
from .vectorstore import get_vectorstore

def build_chain():
    memory = get_memory()
    vectorstore = get_vectorstore()

    return ConversationalRetrievalChain.from_llm(
        llm=ChatOpenAI(temperature=0),
        retriever=vectorstore.as_retriever(),
        memory=memory
    )
