import os
import threading
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional


def _env(name: str, default: str) -> str:
    val = os.getenv(name)
    return default if val is None else val


def _cuda_available() -> bool:
    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception:
        return False


def gpu_mode() -> str:
    """
    Controls whether GPU should be used:
      - auto (default): use GPU only if CUDA is available
      - off: force CPU
      - force: require CUDA; GPU tasks will raise if CUDA is unavailable
    """
    return _env("SRRIS_GPU_MODE", "auto").strip().lower()


def gpu_enabled() -> bool:
    mode = gpu_mode()
    if mode == "off":
        return False
    if mode in ("auto", "force"):
        return _cuda_available()
    return _cuda_available()


def assert_gpu_ready() -> None:
    if gpu_mode() == "force" and not _cuda_available():
        raise RuntimeError(
            "SRRIS_GPU_MODE=force but CUDA is not available. "
            "Install a CUDA-enabled PyTorch build + GPU drivers, or set SRRIS_GPU_MODE=auto/off."
        )


class GpuGate:
    """
    A single-process GPU scheduler.

    Guarantees that only ONE GPU-heavy task runs at a time (EasyOCR, TrOCR, FastAI, ECG NN, etc).
    Other requests will wait (queue implicitly forms via threads waiting on the semaphore).
    """

    def __init__(self) -> None:
        self._sem = threading.Semaphore(1)
        self._state_lock = threading.Lock()
        self._current_task: Optional[str] = None
        self._current_started_at: Optional[float] = None
        self._waiting: int = 0

    def status(self) -> Dict[str, Any]:
        with self._state_lock:
            now = time.time()
            running_for_s = (
                round(now - self._current_started_at, 2)
                if self._current_started_at is not None
                else None
            )
            return {
                "gpu_mode": gpu_mode(),
                "cuda_available": _cuda_available(),
                "gpu_enabled": gpu_enabled(),
                "in_use": self._current_task is not None,
                "current_task": self._current_task,
                "current_running_for_s": running_for_s,
                "waiting": self._waiting,
            }

    @contextmanager
    def use(self, task_name: str, timeout_s: Optional[float] = None):
        """
        Context manager for GPU-exclusive sections.
        If GPU is disabled (or CUDA unavailable in auto mode), this is a no-op.
        """
        if not gpu_enabled():
            if gpu_mode() == "force":
                assert_gpu_ready()
            yield
            return

        with self._state_lock:
            self._waiting += 1

        acquired = False
        try:
            acquired = self._sem.acquire(timeout=timeout_s) if timeout_s else self._sem.acquire()
            if not acquired:
                raise TimeoutError(f"GPU busy (timeout after {timeout_s}s) for task: {task_name}")

            with self._state_lock:
                self._waiting = max(0, self._waiting - 1)
                self._current_task = task_name
                self._current_started_at = time.time()

            yield
        finally:
            if acquired:
                with self._state_lock:
                    self._current_task = None
                    self._current_started_at = None
                self._sem.release()
            else:
                with self._state_lock:
                    self._waiting = max(0, self._waiting - 1)


gpu_gate = GpuGate()

