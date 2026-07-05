"""name -> engine, powers the UI dropdown (GET /engines) and lookups by id.

Only the small curated set of shipped engines a human would want to play
belongs here. The benchmark harness instantiates arbitrary (engine_id, params)
pairs directly and does not go through this registry.
"""

from __future__ import annotations

from dataclasses import dataclass

from ai.base import Engine
from ai.heuristic_engine import HeuristicEngine
from ai.random_engine import RandomEngine

DEFAULT_ENGINE_ID = "random"


@dataclass(frozen=True)
class EngineEntry:
    id: str
    label: str
    engine: Engine


_ENGINES: dict[str, EngineEntry] = {
    "random": EngineEntry(id="random", label="Random", engine=RandomEngine()),
    "heuristic": EngineEntry(id="heuristic", label="Heuristic", engine=HeuristicEngine()),
}


def get_engine(engine_id: str) -> Engine:
    return _ENGINES[engine_id].engine


def list_engines() -> list[dict]:
    return [
        {"id": entry.id, "label": entry.label, "available": True} for entry in _ENGINES.values()
    ]
