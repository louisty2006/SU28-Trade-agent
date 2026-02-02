"""
REISHI 霊視 v5.0 - 四 LLM 客戶端（與 v4.3 相同架構）

與 v4.3 Stage 3 共用同一組 API Key 與四個供應商：
- Scitely（基本面）
- Cohere（技術面）
- Mistral（風險）
- OpenRouter（宏觀）

Key 不足時：單一 LLM 可兼多角（依 fallback 順序使用第一個有 key 的供應商）。
框架不變，僅呼叫時 fallback。
"""

import os
import requests
import time
from typing import Optional, List, Tuple

# 與 v4.3 stage3 完全一致的配置
PROVIDERS = (
    "scitely",
    "cohere",
    "mistral",
    "openrouter",
)

CONFIG = {
    "scitely": {
        "name": "基本面",
        "api_key_env": "SCITELY_API_KEY",
        "model_env": "SCITELY_MODEL",
        "model_default": "qwen3-235b-a22b-instruct",
        "url": "https://api.scitely.com/v1/chat/completions",
    },
    "cohere": {
        "name": "技術面",
        "api_key_env": "COHERE_API_KEY",
        "model_env": "COHERE_MODEL",
        "model_default": "command-a-03-2025",
        "url": "https://api.cohere.com/v2/chat",
    },
    "mistral": {
        "name": "風險",
        "api_key_env": "MISTRAL_API_KEY",
        "model_env": "MISTRAL_MODEL",
        "model_default": "mistral-small-latest",
        "url": "https://api.mistral.ai/v1/chat/completions",
    },
    "openrouter": {
        "name": "宏觀",
        "api_key_env": "OPENROUTER_API_KEY",
        "model_env": "OPENROUTER_MODEL",
        "model_default": "meta-llama/llama-3.1-8b-instruct",
        "url": "https://openrouter.ai/api/v1/chat/completions",
    },
}

# 預設 fallback 順序（key 不足時依序嘗試）
FALLBACK_ORDER: List[str] = ["scitely", "cohere", "mistral", "openrouter"]


class LLMClients:
    """
    四 LLM 客戶端：與 v4.3 相同資料源與 key，key 不足時一 LLM 兼多角。
    """

    def __init__(self):
        self._keys: dict = {}
        self._models: dict = {}
        for pid in PROVIDERS:
            key = os.getenv(CONFIG[pid]["api_key_env"])
            if key:
                self._keys[pid] = key
                self._models[pid] = os.getenv(
                    CONFIG[pid]["model_env"], CONFIG[pid]["model_default"]
                )

    def has_any_key(self) -> bool:
        return len(self._keys) > 0

    def available_providers(self) -> List[str]:
        return list(self._keys.keys())

    def call(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        provider_hint: Optional[str] = None,
        timeout: int = 120,
    ) -> Tuple[str, Optional[str]]:
        """
        呼叫 LLM。優先使用 provider_hint；若該 key 不存在則依 FALLBACK_ORDER 用第一個有 key 的。
        回傳 (response_text, used_provider_id)。
        """
        order = (
            [provider_hint] + [p for p in FALLBACK_ORDER if p != provider_hint]
            if provider_hint
            else list(FALLBACK_ORDER)
        )
        for pid in order:
            if pid not in self._keys:
                continue
            text = self._call_one(pid, prompt, system_prompt, timeout)
            if text is not None:
                return (text.strip(), pid)
        return ("", None)

    def _call_one(
        self,
        provider_id: str,
        prompt: str,
        system_prompt: Optional[str],
        timeout: int,
    ) -> Optional[str]:
        if provider_id == "scitely":
            return self._call_scitely(prompt, system_prompt, timeout)
        if provider_id == "cohere":
            return self._call_cohere(prompt, system_prompt, timeout)
        if provider_id == "mistral":
            return self._call_mistral(prompt, system_prompt, timeout)
        if provider_id == "openrouter":
            return self._call_openrouter(prompt, system_prompt, timeout)
        return None

    def _messages(self, prompt: str, system_prompt: Optional[str]):
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.append({"role": "user", "content": prompt})
        return msgs

    def _call_scitely(
        self, prompt: str, system_prompt: Optional[str], timeout: int
    ) -> Optional[str]:
        url = CONFIG["scitely"]["url"]
        key = self._keys["scitely"]
        model = self._models["scitely"]
        msgs = self._messages(prompt, system_prompt)
        for attempt in range(3):
            try:
                r = requests.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": msgs,
                        "temperature": 0.3,
                        "max_tokens": 4000,
                    },
                    timeout=timeout,
                )
                if r.status_code == 200:
                    return (
                        r.json()
                        .get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )
                if 500 <= r.status_code < 600 and attempt < 2:
                    time.sleep(3 + attempt * 2)
                    continue
            except Exception:
                if attempt < 2:
                    time.sleep(2)
        return None

    def _call_cohere(
        self, prompt: str, system_prompt: Optional[str], timeout: int
    ) -> Optional[str]:
        url = CONFIG["cohere"]["url"]
        key = self._keys["cohere"]
        model = self._models["cohere"]
        msgs = self._messages(prompt, system_prompt)
        try:
            r = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": msgs,
                    "temperature": 0.3,
                },
                timeout=timeout,
            )
            if r.status_code == 200:
                data = r.json()
                content = data.get("message", {}).get("content", [])
                return content[0].get("text", "") if content else ""
        except Exception:
            pass
        return None

    def _call_mistral(
        self, prompt: str, system_prompt: Optional[str], timeout: int
    ) -> Optional[str]:
        url = CONFIG["mistral"]["url"]
        key = self._keys["mistral"]
        model = self._models["mistral"]
        msgs = self._messages(prompt, system_prompt)
        try:
            r = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": msgs,
                    "temperature": 0.3,
                    "max_tokens": 4000,
                },
                timeout=timeout,
            )
            if r.status_code == 200:
                return (
                    r.json()
                    .get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
        except Exception:
            pass
        return None

    def _call_openrouter(
        self, prompt: str, system_prompt: Optional[str], timeout: int
    ) -> Optional[str]:
        url = CONFIG["openrouter"]["url"]
        key = self._keys["openrouter"]
        model = self._models["openrouter"]
        msgs = self._messages(prompt, system_prompt)
        try:
            r = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": msgs,
                    "temperature": 0.3,
                    "max_tokens": 4000,
                },
                timeout=timeout,
            )
            if r.status_code == 200:
                return (
                    r.json()
                    .get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
        except Exception:
            pass
        return None
