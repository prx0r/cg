"""Worldpack registry: kind string -> factory. The only place domains are named."""
from __future__ import annotations

FACTORIES: dict[str, tuple[callable, str]] = {}


def register(kind: str, description: str = ""):
    def deco(fn):
        if kind in FACTORIES:
            raise ValueError(f"duplicate world kind {kind}")
        FACTORIES[kind] = (fn, description)
        return fn
    return deco


def kinds() -> dict[str, str]:
    return {k: d for k, (_, d) in sorted(FACTORIES.items())}


def create(kind: str, **kwargs):
    if kind not in FACTORIES:
        raise KeyError(f"unknown world '{kind}'. known: {sorted(FACTORIES)}")
    return FACTORIES[kind][0](**kwargs)


@register("toy.signal_game", "hidden bit; buy noisy evidence; commit stance")
def _toy(**kw):
    from .toy import SignalWorld
    return SignalWorld(**kw)
