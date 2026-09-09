"""GET /engines (dropdown) and the stateless POST /engine/move used by
save/load, position analysis, and the benchmark harness."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ai.registry import UnknownEngineError, get_engine, list_engines
from engine.moves import legal_turn_sequences
from engine.state import GameState
from models.game import EngineInfo, EngineMoveRequest, EngineMoveResponse, MoveModel

router = APIRouter(tags=["engine"])


@router.get("/engines", response_model=list[EngineInfo])
def engines() -> list[EngineInfo]:
    return list_engines()


@router.post("/engine/move", response_model=EngineMoveResponse)
def engine_move(body: EngineMoveRequest) -> EngineMoveResponse:
    # Resolve the engine before doing any search work, so a bad id costs nothing.
    try:
        engine = get_engine(body.engine)
    except UnknownEngineError as unknown:
        raise HTTPException(
            status_code=422,
            detail=f"unknown engine '{unknown.engine_id}'; valid ids: {unknown.valid_ids}",
        ) from None

    state = GameState.from_dict(body.state.model_dump())
    sequences = legal_turn_sequences(state, state.turn, body.dice)
    chosen = engine.choose_move(state, body.dice, sequences)
    return EngineMoveResponse(move=[MoveModel(source=m.source, target=m.target) for m in chosen])
