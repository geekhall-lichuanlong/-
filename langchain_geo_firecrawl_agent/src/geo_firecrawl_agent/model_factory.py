from __future__ import annotations

from typing import Any


def build_chat_model(model_name: str) -> Any:
    """Build provider-specific chat models when LangChain cannot infer enough safely."""

    if model_name.startswith("deepseek:"):
        try:
            from langchain_deepseek import ChatDeepSeek
        except ImportError as exc:
            raise RuntimeError(
                "DeepSeek support is not installed. Run: pip install -e \".[deepseek]\""
            ) from exc

        deepseek_model = model_name.split(":", 1)[1]
        return ChatDeepSeek(
            model=deepseek_model,
            temperature=0,
            max_retries=2,
        )

    return model_name
