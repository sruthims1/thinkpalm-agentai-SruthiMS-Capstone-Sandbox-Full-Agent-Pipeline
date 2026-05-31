"""
Central LLM service — Groq primary, OpenRouter fallback.

Two model buckets to stay within free-tier rate limits:
  GROQ_QUALITY (llama-3.3-70b-versatile)  6,000 TPM  — analysis, review, audit
  GROQ_GEN     (llama-3.1-8b-instant)   131,072 TPM  — Gherkin/TypeScript generation
"""

from __future__ import annotations
import json, os, re, time, logging
from dataclasses import dataclass
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")
log = logging.getLogger(__name__)

GROQ_URL       = "https://api.groq.com/openai/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


@dataclass
class LLMConfig:
    model:       str
    max_tokens:  int   = 2000
    temperature: float = 0.2


class LLMService:
    """Unified LLM gateway — Groq 70B / 8B with OpenRouter fallback."""

    GROQ_QUALITY = "llama-3.3-70b-versatile"   # 6K TPM  — analysis/review
    GROQ_GEN     = "llama-3.1-8b-instant"       # 131K TPM — generation
    OR_FALLBACKS = [
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemma-4-31b-it:free",
        "deepseek/deepseek-v4-flash:free",
    ]

    def __init__(self) -> None:
        self.groq_key = os.environ.get("GROQ_API_KEY", "")
        self.or_key   = os.environ.get("OPENROUTER_API_KEY", "")

    # ── Public API ──────────────────────────────────────────────────────────────
    def complete_quality(self, system: str, user: str, max_tokens: int = 1500) -> str:
        """70B quality model — domain analysis, BDD review, audit tasks."""
        return self._call(LLMConfig(self.GROQ_QUALITY, max_tokens), system, user)

    def complete_gen(self, system: str, user: str, max_tokens: int = 4000) -> str:
        """8B generation model — Gherkin BDD, TypeScript Playwright (131K TPM bucket)."""
        return self._call(LLMConfig(self.GROQ_GEN, max_tokens), system, user)

    def complete_with_tools(
        self,
        system: str,
        user: str,
        tools: list[dict],
        max_tokens: int = 2000,
        dispatcher=None,
    ) -> str:
        """LLM-driven tool-calling loop via Groq function calling.
        The LLM decides which tools to invoke and when; results are fed back into context.
        Falls back to complete_gen() transparently if tool calling fails."""
        if not self.groq_key or not tools:
            return self.complete_gen(system, user, max_tokens)
        try:
            return self._groq_with_tools(system, user, tools, max_tokens, dispatcher)
        except Exception as exc:
            log.warning(f"[LLMService] Tool calling failed ({str(exc)[:80]}) — fallback to complete_gen")
            return self.complete_gen(system, user, max_tokens)

    def _groq_with_tools(
        self,
        system: str,
        user: str,
        tools: list[dict],
        max_tokens: int,
        dispatcher,
    ) -> str:
        """Inner Groq tool-calling loop — up to 3 tool-call rounds."""
        groq_tools = [
            {
                "type": "function",
                "function": {
                    "name":        t["name"],
                    "description": t["description"],
                    "parameters":  t["input_schema"],
                },
            }
            for t in tools
        ]
        messages: list[dict] = [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ]

        for _round in range(3):
            # Guard against 413 Payload Too Large — truncate system message if needed.
            # Groq's safe threshold is ~24,000 chars of serialised JSON payload.
            payload_estimate = len(json.dumps({"messages": messages, "tools": groq_tools}))
            if payload_estimate > 24_000 and messages and messages[0]["role"] == "system":
                overage   = payload_estimate - 24_000
                sys_content = messages[0]["content"] or ""
                messages[0]["content"] = sys_content[:max(500, len(sys_content) - overage)]
                log.warning(f"[LLMService] Payload {payload_estimate} chars — truncated system to avoid 413")

            r = requests.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {self.groq_key}", "Content-Type": "application/json"},
                json={
                    "model":       self.GROQ_GEN,
                    "messages":    messages,
                    "tools":       groq_tools,
                    "tool_choice": "auto",
                    "max_tokens":  max_tokens,
                    "temperature": 0.2,
                },
                timeout=60,
            )
            if r.status_code == 429:
                time.sleep(5)
                continue
            r.raise_for_status()

            choice = r.json()["choices"][0]
            msg    = choice["message"]
            finish = choice.get("finish_reason", "stop")

            if finish == "tool_calls" and msg.get("tool_calls"):
                messages.append({
                    "role":       "assistant",
                    "content":    msg.get("content"),
                    "tool_calls": msg["tool_calls"],
                })
                for call in msg["tool_calls"]:
                    fn_name = call["function"]["name"]
                    try:
                        fn_args = json.loads(call["function"]["arguments"])
                    except Exception:
                        fn_args = {}
                    result = dispatcher(fn_name, fn_args) if dispatcher else json.dumps({"error": "no dispatcher"})
                    log.info(f"[LLMService] Tool called by LLM: {fn_name}")
                    messages.append({
                        "role":         "tool",
                        "tool_call_id": call["id"],
                        "content":      result if isinstance(result, str) else json.dumps(result),
                    })
            else:
                return msg.get("content") or ""

        # Rounds exhausted — return last assistant text if any
        for m in reversed(messages):
            if m.get("role") == "assistant" and m.get("content"):
                return m["content"]
        raise RuntimeError("Tool-calling loop exhausted with no text response")

    # ── Internal routing ────────────────────────────────────────────────────────
    def _call(self, cfg: LLMConfig, system: str, user: str) -> str:
        try:
            return self._groq(cfg, system, user)
        except Exception as exc:
            s = str(exc)
            if "429" in s or "Too Many" in s or "413" in s or "Payload Too Large" in s:
                log.warning(f"[LLMService] Groq error ({s[:60]}) — falling back to OpenRouter")
                return self._openrouter(system, user, cfg.max_tokens)
            raise

    def _groq(self, cfg: LLMConfig, system: str, user: str) -> str:
        if not self.groq_key:
            raise ValueError("GROQ_API_KEY not set")
        for attempt in range(2):
            r = requests.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {self.groq_key}", "Content-Type": "application/json"},
                json={
                    "model":       cfg.model,
                    "messages":    [{"role": "system", "content": system}, {"role": "user", "content": user}],
                    "max_tokens":  cfg.max_tokens,
                    "temperature": cfg.temperature,
                },
                timeout=60,
            )
            if r.status_code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"] or ""
        r.raise_for_status()
        return ""

    def _openrouter(self, system: str, user: str, max_tokens: int) -> str:
        if not self.or_key:
            raise ValueError("OPENROUTER_API_KEY not set")
        last_exc: Exception = RuntimeError("All OpenRouter models exhausted")
        for model in self.OR_FALLBACKS:
            try:
                r = requests.post(
                    OPENROUTER_URL,
                    headers={
                        "Authorization": f"Bearer {self.or_key}",
                        "Content-Type":  "application/json",
                        "HTTP-Referer":  "https://maritime-qa.local",
                        "X-Title":       "MaritimeTestAI",
                    },
                    json={
                        "model":       model,
                        "messages":    [{"role": "system", "content": system}, {"role": "user", "content": user}],
                        "max_tokens":  max_tokens,
                        "temperature": 0.2,
                    },
                    timeout=45,
                )
                if r.status_code == 200:
                    content = r.json()["choices"][0]["message"]["content"] or ""
                    return re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
                last_exc = requests.exceptions.HTTPError(f"{r.status_code} [{model}]", response=r)
            except Exception as exc:
                last_exc = exc
        raise last_exc


# Module-level singleton
llm = LLMService()
