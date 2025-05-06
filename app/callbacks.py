from typing import AsyncIterator
from langchain.callbacks.base import AsyncCallbackHandler

class StreamingHandler(AsyncCallbackHandler):
    def __init__(self):
        self.queue = []

    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.queue.append(token)

    async def stream_tokens(self) -> AsyncIterator[str]:
        while self.queue:
            yield self.queue.pop(0)
