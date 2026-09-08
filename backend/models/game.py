"""Pydantic request/response bodies. Thin wrappers around the engine's own
serialization (GameState.to_dict/from_dict, Move) — the engine layer stays
the one canonical format; these models just describe it over HTTP."""

from __future__ import annotations

from pydantic import BaseModel


class MoveModel(BaseModel):
    source: int
    target: int


class CombinedMoveModel(BaseModel):
    """A two-hop combo offered as a single drag: submit `first` then `second`."""

    first: MoveModel
    second: MoveModel


class GameStateModel(BaseModel):
    board: list[int]
    bar: list[int]
    off: list[int]
    turn: int


class GameOverModel(BaseModel):
    winner: int
    multiplier: int


class NewGameResponse(BaseModel):
    game_id: str
    state: GameStateModel


class RollResponse(BaseModel):
    dice: tuple[int, int]
    legal_moves: list[MoveModel]
    combined_moves: list[CombinedMoveModel] = []
    state: GameStateModel


class MoveRequest(BaseModel):
    move: MoveModel


class MoveResponse(BaseModel):
    state: GameStateModel
    legal_moves: list[MoveModel]
    combined_moves: list[CombinedMoveModel] = []
    game_over: GameOverModel | None = None


class AiMoveResponse(BaseModel):
    move: list[MoveModel]
    dice: tuple[int, int]
    state: GameStateModel
    game_over: GameOverModel | None = None


class EngineInfo(BaseModel):
    id: str
    label: str
    available: bool


class EngineMoveRequest(BaseModel):
    state: GameStateModel
    dice: tuple[int, int]
    engine: str = "random"


class EngineMoveResponse(BaseModel):
    move: list[MoveModel]
