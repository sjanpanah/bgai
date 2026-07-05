"""Stateful game endpoints. The server holds GameState keyed by game_id and
is authoritative for legality; the frontend only renders and collects intent.

A turn is played one die-step at a time (supporting partial turns in the UI):
`legal_turn_sequences` is computed once per roll, then narrowed by prefix as
each single-die move comes in via POST /move, until a sequence is exhausted.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException

from ai.registry import DEFAULT_ENGINE_ID, get_engine
from engine.moves import apply_move, apply_turn, legal_turn_sequences
from engine.rules import has_won, win_multiplier
from engine.state import Dice, GameState, Move
from models.game import (
    AiMoveResponse,
    GameOverModel,
    MoveModel,
    MoveRequest,
    MoveResponse,
    NewGameResponse,
    RollResponse,
)

router = APIRouter(prefix="/game", tags=["game"])


@dataclass
class GameSession:
    state: GameState
    dice: tuple[int, int] | None = None
    pending_sequences: list[list[Move]] | None = None


GAMES: dict[str, GameSession] = {}


def _get_session(game_id: str) -> GameSession:
    session = GAMES.get(game_id)
    if session is None:
        raise HTTPException(status_code=404, detail="no such game")
    return session


def _dedup_first_moves(sequences: list[list[Move]]) -> list[MoveModel]:
    seen: set[Move] = set()
    moves: list[MoveModel] = []
    for seq in sequences:
        if not seq or seq[0] in seen:
            continue
        seen.add(seq[0])
        moves.append(MoveModel(source=seq[0].source, target=seq[0].target))
    return moves


def _game_over(state: GameState, player: int) -> GameOverModel | None:
    if not has_won(state, player):
        return None
    return GameOverModel(winner=player, multiplier=win_multiplier(state, player))


@router.post("/new", response_model=NewGameResponse)
def new_game() -> NewGameResponse:
    game_id = str(uuid.uuid4())
    state = GameState.new_game()
    GAMES[game_id] = GameSession(state=state)
    return NewGameResponse(game_id=game_id, state=state.to_dict())


@router.post("/{game_id}/roll", response_model=RollResponse)
def roll(game_id: str) -> RollResponse:
    session = _get_session(game_id)
    if session.dice is not None:
        raise HTTPException(status_code=400, detail="a turn is already in progress")

    dice = Dice().roll()
    sequences = legal_turn_sequences(session.state, session.state.turn, dice)

    if sequences == [[]]:
        session.state.turn = 1 - session.state.turn
        return RollResponse(dice=dice, legal_moves=[])

    session.dice = dice
    session.pending_sequences = sequences
    return RollResponse(dice=dice, legal_moves=_dedup_first_moves(sequences))


@router.post("/{game_id}/move", response_model=MoveResponse)
def move(game_id: str, body: MoveRequest) -> MoveResponse:
    session = _get_session(game_id)
    if session.pending_sequences is None:
        raise HTTPException(status_code=400, detail="no roll in progress")

    submitted = Move(body.move.source, body.move.target)
    matching = [seq for seq in session.pending_sequences if seq and seq[0] == submitted]
    if not matching:
        raise HTTPException(status_code=400, detail="illegal move")

    player = session.state.turn
    session.state = apply_move(session.state, player, submitted)
    session.pending_sequences = [seq[1:] for seq in matching]

    game_over = _game_over(session.state, player)
    turn_complete = game_over is not None or all(len(seq) == 0 for seq in session.pending_sequences)
    if turn_complete:
        session.dice = None
        session.pending_sequences = None
        if game_over is None:
            session.state.turn = 1 - player
        return MoveResponse(state=session.state.to_dict(), legal_moves=[], game_over=game_over)

    return MoveResponse(
        state=session.state.to_dict(),
        legal_moves=_dedup_first_moves(session.pending_sequences),
        game_over=None,
    )


@router.post("/{game_id}/ai", response_model=AiMoveResponse)
def ai_move(game_id: str, engine: str = DEFAULT_ENGINE_ID) -> AiMoveResponse:
    session = _get_session(game_id)
    if session.dice is not None:
        raise HTTPException(status_code=400, detail="a turn is already in progress")

    player = session.state.turn
    dice = Dice().roll()
    sequences = legal_turn_sequences(session.state, player, dice)

    if sequences == [[]]:
        session.state.turn = 1 - player
        return AiMoveResponse(move=[], dice=dice, state=session.state.to_dict(), game_over=None)

    chosen = get_engine(engine).choose_move(session.state, dice, sequences)
    session.state = apply_turn(session.state, player, chosen)

    game_over = _game_over(session.state, player)
    if game_over is None:
        session.state.turn = 1 - player

    return AiMoveResponse(
        move=[MoveModel(source=m.source, target=m.target) for m in chosen],
        dice=dice,
        state=session.state.to_dict(),
        game_over=game_over,
    )
