"""Pydantic request/response bodies. Thin wrappers around the engine's own
serialization (GameState.to_dict/from_dict, Move) — the engine layer stays
the one canonical format; these models just describe it over HTTP."""

from __future__ import annotations

from typing import Annotated, Literal

from annotated_types import Len
from pydantic import BaseModel, Field

# The engine's structural assumptions, stated once as types. Without these an
# arbitrary `state` reaches the rules code and fails as an IndexError deep
# inside it -- a 500 on user input rather than a 422 -- and an oversized board
# is accepted and burns CPU proportional to a length the caller chooses.
Board = Annotated[list[int], Len(24, 24)]
PerPlayer = Annotated[list[int], Len(2, 2)]
DieValue = Annotated[int, Field(ge=1, le=6)]


class MoveModel(BaseModel):
    source: int
    target: int


class CombinedMoveModel(BaseModel):
    """A two-hop combo offered as a single drag: submit `first` then `second`."""

    first: MoveModel
    second: MoveModel


class GameStateModel(BaseModel):
    board: Board
    bar: PerPlayer
    off: PerPlayer
    turn: Literal[0, 1]


class GameOverModel(BaseModel):
    winner: int
    multiplier: int


class NewGameResponse(BaseModel):
    game_id: str
    state: GameStateModel


class RollResponse(BaseModel):
    dice: tuple[DieValue, DieValue]
    legal_moves: list[MoveModel]
    combined_moves: list[CombinedMoveModel] = []
    remaining_dice: list[int] = []
    state: GameStateModel


class MoveRequest(BaseModel):
    move: MoveModel


class MoveResponse(BaseModel):
    state: GameStateModel
    legal_moves: list[MoveModel]
    combined_moves: list[CombinedMoveModel] = []
    remaining_dice: list[int] = []
    game_over: GameOverModel | None = None


class AiMoveResponse(BaseModel):
    move: list[MoveModel]
    dice: tuple[DieValue, DieValue]
    state: GameStateModel
    game_over: GameOverModel | None = None


class EngineInfo(BaseModel):
    id: str
    label: str
    available: bool


class EngineMoveRequest(BaseModel):
    state: GameStateModel
    dice: tuple[DieValue, DieValue]
    engine: str = "random"


class EngineMoveResponse(BaseModel):
    move: list[MoveModel]
