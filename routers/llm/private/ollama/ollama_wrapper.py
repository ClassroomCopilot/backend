from typing import Any, Dict
from ollama import Client
from langchain_core.runnables.base import Runnable
from langchain.prompts.base import StringPromptValue

class OllamaWrapper(Runnable):
    def __init__(self, host: str):
        self.client = Client(host=host)

    def invoke(self, prompt: Any, config: Dict[str, Any] = None, **kwargs: Any) -> str:
        if isinstance(prompt, StringPromptValue):
            prompt = prompt.to_string()

        model_name = kwargs.get("model", "llama3")
        options = {
            "temperature": kwargs.get("temperature"),
            "top_p": kwargs.get("top_p"),
            "max_tokens": kwargs.get("max_tokens"),
        }
        messages = [{"role": "user", "content": prompt}]
        response = self.client.chat(model=model_name, messages=messages, options=options)
        if response and "message" in response and "content" in response["message"]:
            return response["message"]["content"]
        else:
            raise ValueError("Invalid response structure from model")

    async def ainvoke(self, prompt: Any, config: Dict[str, Any] = None, **kwargs: Any) -> str:
        return self.invoke(prompt, config, **kwargs)
