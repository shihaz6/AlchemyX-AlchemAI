import os
import requests
from dotenv import find_dotenv, load_dotenv


load_dotenv(find_dotenv())


class OpenRouterClient:

    def __init__(self):

        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = os.getenv("OPENROUTER_MODEL")

        if not self.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY is not set in .env"
            )

        if not self.model:
            raise ValueError(
                "OPENROUTER_MODEL is not set in .env"
            )

        self.url = "https://openrouter.ai/api/v1/chat/completions"

    def ask(self, prompt):

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        response = requests.post(
            self.url,
            headers=headers,
            json=data,
            timeout=60
        )

        response.raise_for_status()

        result = response.json()

        return result["choices"][0]["message"]["content"]
