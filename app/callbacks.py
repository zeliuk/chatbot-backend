import asyncio
from typing import AsyncIterator
from langchain.callbacks.base import AsyncCallbackHandler

class StreamingHandler(AsyncCallbackHandler):
    def __init__(self, user_question: str = ""):
        self.user_question = user_question.strip().lower()
        self.queue = asyncio.Queue()
        self.started = False
        self.skip_prefix = self.user_question

    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        # Detecta y elimina la pregunta al inicio del stream
        if not self.started:
            self.started = True
            token_strip = token.strip().lower()
            if token_strip.startswith(self.skip_prefix):
                token = token[len(self.skip_prefix):].lstrip()
        await self.queue.put(token)

    async def stream_tokens(self) -> AsyncIterator[str]:
        while True:
            token = await self.queue.get()
            if token is None:
                break
            yield token

    async def end(self):
        await self.queue.put(None)
