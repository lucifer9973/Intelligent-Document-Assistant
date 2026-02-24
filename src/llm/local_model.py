"""
Local LLM wrapper with GPT4All-first runtime selection.

Backend preference:
1. gpt4all (preferred)
2. llama-cpp-python (fallback)
"""
from __future__ import annotations

import os
from typing import Any, Optional

try:
    from gpt4all import GPT4All
except Exception:  # pragma: no cover - optional dependency
    GPT4All = None

try:
    from llama_cpp import Llama
except Exception:  # pragma: no cover - graceful fallback if not installed
    Llama = None


class LocalLLM:
    def __init__(self, model_path: Optional[str] = None, n_ctx: int = 2048):
        """Initialize local LLM wrapper.

        Args:
            model_path: Path to the GGML/llama model file. If None, looks at
                the environment variable `LOCAL_LLM_MODEL_PATH`.
            n_ctx: Context window size to pass to the model.
        """
        self.model_path = model_path or os.getenv("LOCAL_LLM_MODEL_PATH")
        self.n_ctx = n_ctx
        self._client: Any = None
        self.backend: Optional[str] = None

        if not self.model_path or not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Model file not found. Set `model_path` or `LOCAL_LLM_MODEL_PATH`. Given: {self.model_path}"
            )

        # Prefer GPT4All runtime when available.
        if GPT4All is not None:
            model_name = os.path.basename(self.model_path)
            model_dir = os.path.dirname(self.model_path) or None
            self._client = GPT4All(
                model_name=model_name,
                model_path=model_dir,
                allow_download=False,
                device="cpu",
            )
            self.backend = "gpt4all"
            return

        # Fallback to llama-cpp-python.
        if Llama is not None:
            self._client = Llama(model_path=self.model_path, n_ctx=self.n_ctx)
            self.backend = "llama_cpp"
            return

        raise RuntimeError(
            "No local LLM backend available. Install `gpt4all` (preferred) "
            "or `llama-cpp-python`."
        )

    def generate(
        self,
        prompt: str,
        max_tokens: int = 256,
        temperature: float = 0.1,
        stop: Optional[list[str]] = None,
    ) -> str:
        """Generate text from the local model.

        Returns the generated text. Raises exceptions from the
        underlying library if generation fails.
        """
        if self._client is None:
            raise RuntimeError("Local LLM client not initialized")

        if self.backend == "gpt4all":
            try:
                # GPT4All versions differ: some use `max_tokens`, others use `n_predict`.
                kwargs = {
                    "temp": temperature,
                    "top_k": 40,
                    "top_p": 0.9,
                }
                try:
                    resp = self._client.generate(prompt, max_tokens=max_tokens, **kwargs)
                except TypeError:
                    resp = self._client.generate(prompt, n_predict=max_tokens, **kwargs)
                return resp if isinstance(resp, str) else str(resp)
            except Exception as e:
                raise RuntimeError(f"Failed to generate with GPT4All backend: {e}")

        try:
            # llama-cpp-python create_completion -> choices[0].text
            resp = self._client.create_completion(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop or []
            )
            if isinstance(resp, dict):
                return resp.get("choices", [{}])[0].get("text", "")
            return str(resp)
        except Exception as e:
            raise RuntimeError(f"Failed to generate with llama-cpp backend: {e}")


def is_gpt4all_available() -> bool:
    return GPT4All is not None


def is_llama_available() -> bool:
    return Llama is not None


def is_local_llm_available() -> bool:
    return is_gpt4all_available() or is_llama_available()
