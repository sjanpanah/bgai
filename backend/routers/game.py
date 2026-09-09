"""Stateful game endpoints. The server holds GameState keyed by game_id and
is authoritative for legality; the frontend only renders and collects intent.

A turn is played one die-step at a time (supporting partial turns in the UI):
`legal_next_moves` is recomputed from the current state and remaining dice
after each single-die move comes in via POST /move, until the dice run out.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException

from ai.registry import DEFAULT_ENGINE_ID, get_engine
from engine.moves import (
    apply_move,
    apply_turn,
    combined_moves as compute_combined_moves,
    legal_next_moves,
    legal_single_die_moves,
    legal_turn_sequences,
)
from engine.rules import has_won, win_multiplier
from engine.state import Dice, GameState, Move
from models.game import (
    AiMoveResponse,
    CombinedMoveModel,
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
    remaining_dice: list[int] | None = None


GAMES: dict[str, GameSession] = {}


def _get_session(game_id: str) -> GameSession:
    session = GAMES.get(game_id)
    if session is None:
        raise HTTPException(status_code=404, detail="no such game")
    return session


def _as_models(moves: list[Move]) -> list[MoveModel]:
    return [MoveModel(source=m.source, target=m.target) for m in moves]


def _combined_as_models(pairs: list[tuple[Move, Move]]) -> list[CombinedMoveModel]:
    return [
        CombinedMoveModel(
            first=MoveModel(source=m1.source, target=m1.target),
            second=MoveModel(source=m2.source, target=m2.target),
        )
        for m1, m2 in pairs
    ]


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
    if session.remaining_dice is not None:
        raise HTTPException(status_code=400, detail="a turn is already in progress")

    dice = Dice().roll()
    values = [dice[0]] * 4 if dice[0] == dice[1] else [dice[0], dice[1]]
    next_moves = legal_next_moves(session.state, session.state.turn, values)

    if not next_moves:
        session.state.turn = 1 - session.state.turn
        return RollResponse(dice=dice, legal_moves=[], state=session.state.to_dict())

    # Build the response before touching the session: a failure in here would
    # otherwise leave the session believing a turn is in progress while the
    # client holds an error and no legal moves, wedging the game permanently.
    combos = compute_combined_moves(session.state, session.state.turn, values)
    session.remaining_dice = values
    return RollResponse(
        dice=dice,
        legal_moves=_as_models(next_moves),
        combined_moves=_combined_as_models(combos),
        remaining_dice=values,
        state=session.state.to_dict(),
    )


@router.post("/{game_id}/move", response_model=MoveResponse)
def move(game_id: str, body: MoveRequest) -> MoveResponse:
    session = _get_session(game_id)
    if session.remaining_dice is None:
        raise HTTPException(status_code=400, detail="no roll in progress")

    submitted = Move(body.move.source, body.move.target)
    current_options = legal_next_moves(session.state, session.state.turn, session.remaining_dice)
    if submitted not in current_options:
        raise HTTPException(status_code=400, detail="illegal move")

    player = session.state.turn
    die_used = next(
        die
        for die in sorted(set(session.remaining_dice))
        if submitted in legal_single_die_moves(session.state, player, die)
    )
    # `apply_move` returns a new state, so the whole response is built off
    # locals and the session is only updated once nothing else can fail —
    # otherwise an error partway through leaves the session mid-turn with the
    # client unable to continue or retry, which costs the player the game.
    new_state = apply_move(session.state, player, submitted)
    remaining = list(session.remaining_dice)
    remaining.remove(die_used)

    game_over = _game_over(new_state, player)
    next_moves = [] if game_over else legal_next_moves(new_state, player, remaining)
    turn_complete = game_over is not None or not remaining or not next_moves

    if turn_complete:
        if game_over is None:
            new_state.turn = 1 - player
        session.state = new_state
        session.remaining_dice = None
        return MoveResponse(
            state=session.state.to_dict(),
            legal_moves=[],
            remaining_dice=[],
            game_over=game_over,
        )

    combos = compute_combined_moves(new_state, player, remaining)
    session.state = new_state
    session.remaining_dice = remaining
    return MoveResponse(
        state=session.state.to_dict(),
        legal_moves=_as_models(next_moves),
        combined_moves=_combined_as_models(combos),
        remaining_dice=remaining,
        game_over=None,
    )


@router.post("/{game_id}/ai", response_model=AiMoveResponse)
def ai_move(game_id: str, engine: str = DEFAULT_ENGINE_ID) -> AiMoveResponse:
    session = _get_session(game_id)
    if session.remaining_dice is not None:
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
