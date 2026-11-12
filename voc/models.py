"""Model lifecycle — one model resident at a time (invariant I6).

Your 8 GB RAM / 4 GB VRAM cannot hold Whisper, the local LLM and the embedder
together, so the orchestrator asks this manager to make exactly one model
resident before each stage and to release whatever was resident before.

Two kinds of model live in different places:
  - **Ollama LLMs** (phi4-mini, gemma3:4b, ...) run inside the Ollama server
    process. We don't hold a Python handle; we just warm one and ask Ollama to
    unload it (keep_alive=0) to free its VRAM before an in-process model loads.
  - **In-process models** (the sentence-transformers embedder, faster-whisper)
    are Python objects we hold. We free them by dropping the reference, running
    gc, and emptying the CUDA cache.

`ensure(name)` returns a handle for in-process models and None for Ollama LLMs
(which are used via voc/llm.py). All heavy imports are lazy, so this module
imports cleanly even before torch / sentence-transformers / faster-whisper are
installed.
"""
from __future__ import annotations

import gc

from . import config

# Logical names that mean an in-process model. Anything else is an Ollama tag.
EMBEDDER = "embedder"
WHISPER = "whisper"
IN_PROCESS = {EMBEDDER, WHISPER}


def _kind(name: str) -> str:
    return name if name in IN_PROCESS else "ollama"


class ModelManager:
    """Holds at most one resident model and swaps it on demand."""

    def __init__(self) -> None:
        self._name: str | None = None
        self._handle: object | None = None

    @property
    def resident(self) -> str | None:
        return self._name

    def ensure(self, name: str | None) -> object | None:
        """Make `name` the single resident model; return its handle (or None
        for Ollama LLMs). Idempotent: asking for the resident model is a no-op."""
        if name is None:
            self.release()
            return None
        if name == self._name:
            return self._handle
        self.release()
        print(f"    [models] load {name}")
        self._handle = self._load(name)
        self._name = name
        return self._handle

    def release(self) -> None:
        """Unload the resident model and reclaim its memory."""
        if self._name is None:
            return
        name, handle = self._name, self._handle
        print(f"    [models] unload {name}")
        self._name = None
        self._handle = None
        self._unload(name, handle)

    # --- loaders / unloaders ------------------------------------------------
    def _load(self, name: str) -> object | None:
        kind = _kind(name)
        if kind == EMBEDDER:
            from sentence_transformers import SentenceTransformer

            return SentenceTransformer(config.EMBED_MODEL)
        if kind == WHISPER:
            from faster_whisper import WhisperModel

            return WhisperModel(config.WHISPER_SIZE, compute_type=config.WHISPER_COMPUTE)
        # Ollama LLM: warm it so it's resident and pinned; no Python handle.
        self._ollama_keep_alive(name, "30m")
        return None

    def _unload(self, name: str, handle: object | None) -> None:
        if _kind(name) == "ollama":
            self._ollama_keep_alive(name, 0)  # ask the server to evict it now
        else:
            del handle  # drop our only reference
        gc.collect()
        self._empty_cuda_cache()

    # --- helpers ------------------------------------------------------------
    @staticmethod
    def _ollama_keep_alive(name: str, keep_alive) -> None:
        """Best-effort warm (keep_alive>'0') or evict (keep_alive=0)."""
        try:
            import ollama

            ollama.generate(model=name, prompt="", keep_alive=keep_alive)
        except Exception as exc:  # never let memory bookkeeping crash a run
            print(f"    [models] ollama keep_alive({name}, {keep_alive}) skipped: "
                  f"{type(exc).__name__}")

    @staticmethod
    def _empty_cuda_cache() -> None:
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass


# Process-wide singleton. The orchestrator and stages share this one instance.
MANAGER = ModelManager()


def ensure(name: str | None) -> object | None:
    return MANAGER.ensure(name)


def release() -> None:
    MANAGER.release()
