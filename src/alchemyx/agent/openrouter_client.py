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

        payload = {
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
            json=payload,
            timeout=60
        )

        if not response.ok:
            raise RuntimeError(
                f"OpenRouter returned {response.status_code}: {response.text}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError(
                f"OpenRouter returned invalid JSON ({response.status_code}): "
                f"{response.text}"
            ) from exc

        choices = data.get("choices") if isinstance(data, dict) else None
        if not choices:
            provider_error = data.get("error") if isinstance(data, dict) else data
            raise RuntimeError(
                "OpenRouter response did not contain any choices. "
                f"Provider response: {provider_error!r}"
            )

        try:
            content = choices[0]["message"]["content"]
        except (IndexError, KeyError, TypeError) as exc:
            raise RuntimeError(
                f"OpenRouter returned an invalid completion shape: {data!r}"
            ) from exc

        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(
                f"OpenRouter returned empty completion content: {data!r}"
            )
        return content
