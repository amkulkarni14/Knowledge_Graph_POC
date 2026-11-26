"""Local model transport for workspace graph questions."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from backend.app.exceptions.handlers import ApiError


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def request(path, payload=None, timeout=3):
    base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").strip().rstrip("/")
    try:
        url = urlsplit(base)
        url.port
    except ValueError:
        raise ApiError(503, "ollama_url_invalid", "Set OLLAMA_BASE_URL to a valid HTTP origin.") from None
    if (url.scheme not in {"http", "https"} or not url.hostname or url.username
            or url.password or url.path or url.query or url.fragment):
        raise ApiError(503, "ollama_url_invalid", "Set OLLAMA_BASE_URL to an HTTP origin without credentials.")
    body = None if payload is None else json.dumps(payload).encode()
    try:
        opener = build_opener(ProxyHandler({}), NoRedirect())
        with opener.open(Request(base + path, data=body, headers={"Content-Type": "application/json"}),
                         timeout=timeout) as response:
            raw = response.read(262145)
        if len(raw) > 262144:
            raise ValueError
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError
        return result
    except HTTPError as error:
        raise ApiError(503, "ollama_request_failed", f"Ollama returned HTTP {error.code}. Check the host and model.") from None
    except (URLError, OSError):
        raise ApiError(503, "ollama_unreachable", "Cannot reach Ollama. Start it and check OLLAMA_BASE_URL from the backend.") from None
    except (ValueError, UnicodeError):
        raise ApiError(502, "ollama_response_invalid", "Ollama returned an unusable response.") from None


def check():
    model = os.getenv("KG_GRAPH_AI_MODEL", "").strip()
    if not model:
        raise ApiError(503, "ollama_model_unconfigured", "Set KG_GRAPH_AI_MODEL to an installed Ollama model tag.")
    models = request("/api/tags").get("models", [])
    names = {item.get("name") for item in models if isinstance(item, dict)} if isinstance(models, list) else set()
    if model not in names and model + ":latest" not in names:
        raise ApiError(503, "ollama_model_missing", "The configured Ollama model is missing. Run ollama pull with its exact tag.")
    return model


def complete(instruction, payload):
    model = check()
    response = request("/api/chat", {
        "model": model, "stream": False, "format": "json",
        "options": {"temperature": 0, "num_predict": 600},
        "messages": [{"role": "system", "content": instruction},
                     {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
    }, timeout=35)
    try:
        result = json.loads(response["message"]["content"])
        if isinstance(result, dict):
            return result
    except (KeyError, TypeError, ValueError):
        pass
    raise ApiError(502, "ollama_response_invalid", "The model did not return a JSON query plan.")
