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
import logging
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

# 與 v4.3 stage3 完全一致的配置 + openrouter2 + routeway
PROVIDERS = (
    "mistral",
    "openrouter",
    "ollama",
)

CONFIG = {
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
        "model_default": "meta-llama/llama-3.2-3b-instruct:free",
        "url": "https://openrouter.ai/api/v1/chat/completions",
    },
    "ollama": {
        "name": "本地 DeepSeek",
        "api_key_env": "OLLAMA_API_KEY",
        "model_env": "OLLAMA_MODEL",
        "model_default": "deepseek-r1:14b",
        "url": "http://localhost:11434/api/chat",
    },
}

# 預設 fallback 順序（key 不足時依序嘗試）
FALLBACK_ORDER: List[str] = ["mistral", "openrouter", "ollama"]


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
            logger.info(f"[LLM] 嘗試使用 {pid} provider...")
            text = self._call_one(pid, prompt, system_prompt, timeout)
            if text is not None:
                logger.info(f"[LLM] ✓ {pid} 成功，回應長度 {len(text)} 字")
                return (text.strip(), pid)
            logger.warning(f"[LLM] ✗ {pid} 失敗或無回應，嘗試下一個 provider")
        logger.error(f"[LLM] 所有 providers 失敗，已嘗試：{order}")
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
        if provider_id == "openrouter2":
            return self._call_openrouter2(prompt, system_prompt, timeout)
        if provider_id == "routeway":
            return self._call_routeway(prompt, system_prompt, timeout)
        if provider_id == "huggingface":
            return self._call_huggingface(prompt, system_prompt, timeout)
        if provider_id == "ollama":
            return self._call_ollama(prompt, system_prompt, timeout)
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

    def _call_openrouter2(
        self, prompt: str, system_prompt: Optional[str], timeout: int
    ) -> Optional[str]:
        """第二個 OpenRouter 帳號（Reishi02）"""
        url = CONFIG["openrouter2"]["url"]
        key = self._keys.get("openrouter2")
        if not key:
            return None
        model = self._models.get("openrouter2", CONFIG["openrouter2"]["model_default"])
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

    def _call_routeway(
        self, prompt: str, system_prompt: Optional[str], timeout: int
    ) -> Optional[str]:
        """Routeway.ai - DeepSeek R1"""
        url = CONFIG["routeway"]["url"]
        key = self._keys.get("routeway")
        if not key:
            return None
        model = self._models.get("routeway", CONFIG["routeway"]["model_default"])
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

    def _call_huggingface(
        self, prompt: str, system_prompt: Optional[str], timeout: int
    ) -> Optional[str]:
        """HuggingFace Inference Router API"""
        key = self._keys.get("huggingface")
        if not key:
            return None
        model = self._models.get("huggingface", CONFIG["huggingface"]["model_default"])
        url = f"https://router.huggingface.co/models/{model}"

        # HuggingFace 使用不同的请求格式
        full_prompt = ""
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n"
        full_prompt += prompt

        try:
            r = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "inputs": full_prompt,
                    "parameters": {
                        "max_new_tokens": 512,
                        "temperature": 0.3,
                    }
                },
                timeout=timeout,
            )
            if r.status_code == 200:
                data = r.json()
                # HuggingFace 返回格式：[{"generated_text": "..."}]
                if isinstance(data, list) and len(data) > 0:
                    text = data[0].get("generated_text", "")
                    # 移除输入提示部分，只返回生成的部分
                    if text.startswith(full_prompt):
                        text = text[len(full_prompt):].strip()
                    return text
                return ""
        except Exception:
            pass
        return None

    def _call_ollama(
        self, prompt: str, system_prompt: Optional[str], timeout: int
    ) -> Optional[str]:
        """Ollama 本地 LLM 調用"""
        url = CONFIG["ollama"]["url"]
        model = self._models.get("ollama", CONFIG["ollama"]["model_default"])
        msgs = self._messages(prompt, system_prompt)
        try:
            r = requests.post(
                url,
                json={
                    "model": model,
                    "messages": msgs,
                    "temperature": 0.3,
                    "stream": False,
                },
                timeout=timeout,
            )
            if r.status_code == 200:
                data = r.json()
                return (
                    data.get("message", {})
                    .get("content", "")
                )
        except Exception as e:
            logger.warning(f"[Ollama] 調用失敗: {e}")
        return None
