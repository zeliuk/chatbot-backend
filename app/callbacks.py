import asyncio
from typing import AsyncIterator
from langchain.callbacks.base import AsyncCallbackHandler

class StreamingHandler(AsyncCallbackHandler):
    def __init__(self, user_question: str = ""):
        self.user_question = user_question.strip().lower()
        self.queue = asyncio.Queue()
        self.accumulated_tokens = ""

    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        await self.queue.put(token)

    async def stream_tokens(self) -> AsyncIterator[str]:
        # Espera hasta el final para filtrar bien
        while True:
            token = await self.queue.get()
            if token is None:
                break
            self.accumulated_tokens += token

        response = self.accumulated_tokens.strip()

        # 🔥 Si por alguna razón empieza con la pregunta, la limpiamos
        if self.user_question and response.lower().startswith(self.user_question):
            response = response[len(self.user_question):].lstrip()

        for char in response:
            yield char

    async def end(self):
        await self.queue.put(None)
