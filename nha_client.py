from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


MODEL_ALIASES = {
    "Ministral 3B": "ministral-3b-3.0",
    "Ministral 8B": "ministral-8b-3.0",
    "Nemotron Nano 30B": "nvidia-nemotron-3-nano-30b-a3b",
    "Gemma 3 4B": "gemma-3-4b",
    "Gemma 3 12B": "gemma-3-12b",
    "ministral-3b": "ministral-3b-3.0",
    "ministral-8b": "ministral-8b-3.0",
    "nemotron-nano-30b": "nvidia-nemotron-3-nano-30b-a3b",
    "gemma-3-4b": "gemma-3-4b",
    "gemma-3-12b": "gemma-3-12b",
}

ALLOWED_MODELS = {
    "ministral-3b-3.0",
    "ministral-8b-3.0",
    "nvidia-nemotron-3-nano-30b-a3b",
    "gemma-3-4b",
    "gemma-3-12b",
}

DEFAULT_MODEL_ORDER = [
    "ministral-3b-3.0",
    "ministral-8b-3.0",
    "nvidia-nemotron-3-nano-30b-a3b",
    "gemma-3-4b",
    "gemma-3-12b",
]

DEFAULT_CACHE_PATH = Path(".cache") / "llm_cache.json"


class NHAClientError(RuntimeError):
    pass


class NHAclient:
    """Small NHA chat client with token refresh, timeouts, and model validation."""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        token_url: Optional[str] = None,
        chat_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 1,
    ) -> None:
        self.client_id = client_id or os.environ.get("NHA_CLIENT_ID", "")
        self.client_secret = client_secret or os.environ.get("NHA_CLIENT_SECRET", "")
        self.base_url = (base_url or os.environ.get("NHA_BASE_URL", "")).rstrip("/")
        self.token_url = token_url or os.environ.get("NHA_TOKEN_URL", "")
        self.chat_url = chat_url or os.environ.get("NHA_CHAT_URL", "")
        self.timeout = int(timeout)
        self.max_retries = int(max_retries)
        self._access_token: Optional[str] = None
        self._token_expiry = 0.0

        if not self.client_id or not self.client_secret:
            raise NHAClientError("NHA credentials are missing. Set NHA_CLIENT_ID and NHA_CLIENT_SECRET or pass them explicitly.")
        if not self.chat_url and not self.base_url:
            raise NHAClientError("NHA endpoint is missing. Set NHA_CHAT_URL or NHA_BASE_URL.")

    @staticmethod
    def normalize_model(model: str) -> str:
        normalized = MODEL_ALIASES.get(str(model).strip(), str(model).strip())
        if normalized not in ALLOWED_MODELS:
            allowed = ", ".join(sorted(MODEL_ALIASES.keys()))
            raise NHAClientError(f"Model is not NHA-approved for this workflow. Allowed model aliases: {allowed}.")
        return normalized

    def _post_json(self, url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json", **(headers or {})},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:400]
            raise NHAClientError(f"NHA request failed with HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise NHAClientError(f"NHA request failed: {exc.reason}") from exc
        except TimeoutError as exc:
            raise NHAClientError("NHA request timed out.") from exc

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise NHAClientError("NHA response was not valid JSON.") from exc

    def _refresh_token(self) -> str:
        if not self.token_url and self.base_url:
            self.token_url = f"{self.base_url}/oauth/token"
        if not self.token_url:
            raise NHAClientError("NHA token endpoint is missing.")

        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        data = self._post_json(self.token_url, payload)
        token = data.get("access_token") or data.get("token")
        if not token:
            raise NHAClientError("NHA token response did not include an access token.")
        expires_in = data.get("expires_in", 1800)
        try:
            ttl = max(60, int(expires_in) - 60)
        except Exception:
            ttl = 1740
        self._access_token = str(token)
        self._token_expiry = time.time() + ttl
        return self._access_token

    def get_token(self, *, force_refresh: bool = False) -> str:
        if force_refresh or not self._access_token or time.time() >= self._token_expiry:
            return self._refresh_token()
        return self._access_token

    def completion(self, *, model: str, messages: List[Dict[str, Any]], temperature: float = 0, **kwargs: Any) -> Dict[str, Any]:
        model_name = self.normalize_model(model)
        url = self.chat_url or f"{self.base_url}/v1/chat/completions"
        payload = {"model": model_name, "messages": messages, "temperature": temperature, **kwargs}

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            token = self.get_token(force_refresh=attempt > 0)
            try:
                return self._post_json(url, payload, headers={"Authorization": f"Bearer {token}"})
            except NHAClientError as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
        raise NHAClientError(str(last_error or "NHA completion failed."))

    @staticmethod
    def extract_json_response(raw: Any) -> Optional[Dict[str, Any]]:
        if isinstance(raw, dict):
            text = raw.get("choices", [{}])[0].get("message", {}).get("content")
            if text is None and {"document_type", "confidence"} & set(raw):
                return raw
        else:
            text = str(raw)
        if not isinstance(text, str):
            return None
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            pass
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None


def _load_cache(cache_path: Path) -> Dict[str, Any]:
    try:
        return json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    except Exception:
        return {}


def _save_cache(cache_path: Path, cache: Dict[str, Any]) -> None:
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        return


def _cache_key(package_code: str, filename: str, text: str) -> str:
    snippet = re.sub(r"\s+", " ", text or "")[:2200]
    payload = f"{package_code}|{filename}|{snippet}"
    return hashlib.sha256(payload.encode("utf-8", "ignore")).hexdigest()


def _clean_flags(flags: Any, allowed_fields: Iterable[str]) -> Dict[str, int]:
    allowed = set(allowed_fields)
    if not isinstance(flags, dict):
        return {}
    clean: Dict[str, int] = {}
    for key, value in flags.items():
        if key not in allowed:
            continue
        clean[key] = 1 if value in (1, True, "1", "true", "True", "yes", "Yes") else 0
    return clean


def _validate_llm_result(data: Any, allowed_doc_types: Iterable[str], allowed_flags: Iterable[str]) -> Optional[Dict[str, Any]]:
    if not isinstance(data, dict):
        return None
    allowed_docs = set(allowed_doc_types) | {"extra_document"}
    doc_type = data.get("document_type") or data.get("doc_type")
    if doc_type not in allowed_docs:
        return None
    try:
        confidence = max(0.0, min(1.0, float(data.get("confidence", 0.0))))
    except Exception:
        return None
    return {
        "document_type": doc_type,
        "confidence": confidence,
        "extracted_flags": _clean_flags(data.get("extracted_flags", {}), allowed_flags),
        "reason_short": str(data.get("reason_short", data.get("evidence", "")))[:240],
    }


def classify_with_llm(
    text: str,
    filename: str,
    package_code: str,
    candidate_schema: Dict[str, Any],
    client: Optional[NHAclient] = None,
    model: str = "ministral-3b",
) -> Optional[Dict[str, Any]]:
    """Classify one document page with a cached, validated, strict-JSON fallback."""
    allowed_doc_types = list(candidate_schema.get("document_types", []))
    allowed_flags = list(candidate_schema.get("flags", []))
    if not allowed_doc_types:
        return None

    snippet = re.sub(r"\s+", " ", text or "")[:2200]
    cache_path = Path(candidate_schema.get("cache_path") or DEFAULT_CACHE_PATH)
    key = _cache_key(package_code, filename, snippet)
    cache = _load_cache(cache_path)
    if key in cache:
        cached = _validate_llm_result(cache[key], allowed_doc_types, allowed_flags)
        if cached is not None:
            classify_with_llm.last_cache_hit = True
            return cached

    if client is None:
        client = NHAclient()
    classify_with_llm.last_cache_hit = False

    normalized_model = NHAclient.normalize_model(model)
    prompt = (
        "You are classifying one medical claim document page for NHA PS1. "
        "Return strict JSON only. "
        f"Package: {package_code}. "
        f"Allowed document types: {', '.join(allowed_doc_types + ['extra_document'])}. "
        "Based on filename and OCR text, only suggest document_type and confidence. "
        "Do not decide validation, eligibility, pass/fail, ranks, or final schema fields. "
        "If unsure, use extra_document. "
        "Return exactly these JSON keys: document_type, confidence. "
        f"Filename: {filename}. OCR text: {snippet}"
    )
    try:
        raw = client.completion(
            model=normalized_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        parsed = client.extract_json_response(raw)
        clean = _validate_llm_result(parsed, allowed_doc_types, allowed_flags)
    except Exception:
        return None

    if clean is None:
        return None
    cache[key] = clean
    _save_cache(cache_path, cache)
    return clean


classify_with_llm.last_cache_hit = False
