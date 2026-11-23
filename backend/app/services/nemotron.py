import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
NEMOTRON_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
REQUEST_TIMEOUT_SECONDS = 35


class NemotronUnavailable(Exception):
    """The configured model could not provide a usable response."""


class NemotronClient:
    def __init__(self, api_key_provider=None, opener=None):
        self.api_key_provider = api_key_provider or (lambda: os.environ.get("OPENROUTER_API_KEY", "").strip())
        self.opener = opener or urlopen

    def complete(self, messages, max_tokens=1200):
        api_key = self.api_key_provider()
        if not api_key:
            raise NemotronUnavailable("OpenRouter API key is not configured.")

        payload = json.dumps({
            "model": NEMOTRON_MODEL,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }).encode("utf-8")
        request = Request(
            OPENROUTER_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5173",
                "X-Title": "Prepwise Placement Preparation",
            },
            method="POST",
        )
        try:
            with self.opener(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code == 429:
                raise NemotronUnavailable("OpenRouter is temporarily rate-limiting requests.") from None
            raise NemotronUnavailable(f"OpenRouter returned HTTP {error.code}.") from None
        except (URLError, TimeoutError, OSError):
            raise NemotronUnavailable("OpenRouter could not be reached before the request timed out.") from None
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise NemotronUnavailable("OpenRouter returned an invalid response.") from None

        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise NemotronUnavailable("OpenRouter returned an incomplete response.") from None
        if not isinstance(content, str) or not content.strip() or len(content) > 12000:
            raise NemotronUnavailable("OpenRouter returned an empty or oversized response.")
        return content.strip()

    def complete_json(self, messages, max_tokens=1600):
        content = self.complete(messages, max_tokens=max_tokens)
        text = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", content, flags=re.IGNORECASE)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            if start >= 0:
                try:
                    parsed, _ = json.JSONDecoder().raw_decode(text[start:])
                    return parsed
                except json.JSONDecodeError:
                    pass
            raise NemotronUnavailable("Nemotron returned malformed JSON.") from None
