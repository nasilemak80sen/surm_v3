"""Lightweight production profiling helpers."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Callable


@dataclass(frozen=True)
class ProfileResult:
    label: str
    elapsed_ms: float
    result: Any


def profile_call(
    label: str,
    func: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> ProfileResult:
    start = perf_counter()
    result = func(*args, **kwargs)
    elapsed_ms = (perf_counter() - start) * 1000
    return ProfileResult(label=label, elapsed_ms=elapsed_ms, result=result)
