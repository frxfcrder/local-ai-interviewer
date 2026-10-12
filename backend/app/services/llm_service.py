import json
import httpx
from typing import AsyncGenerator, List, Dict, Any

class LLMService:
    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "llama3.2"):
        self.base_url = base_url
        self.model_name = model_name

    async def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """
        Sends chat history to Ollama and returns the complete text response.
        Messages format: [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
        """
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("message", {}).get("content", "")
            except httpx.HTTPError as e:
                # Log the error properly in a production app
                raise RuntimeError(f"Failed to communicate with local Ollama instance: {e}")

    async def stream_response(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        """
        Streams chat tokens asynchronously from Ollama for real-time frontend feedback.
        """
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content