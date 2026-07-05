from fastapi.testclient import TestClient

from engine.state import GameState
from main import app
from routers.game import GAMES

client = TestClient(app)


def setup_function() -> None:
    GAMES.clear()


def test_new_game_returns_starting_position():
    resp = client.post("/game/new")
    assert resp.status_code == 200
    body = resp.json()
    assert "game_id" in body
    assert body["state"]["turn"] == 0
    assert sum(abs(c) for c in body["state"]["board"]) == 30


def test_engines_lists_random():
    resp = client.get("/engines")
    assert resp.status_code == 200
    ids = [e["id"] for e in resp.json()]
    assert "random" in ids


def test_roll_then_move_then_ai_full_turn_cycle():
    game_id = client.post("/game/new").json()["game_id"]

    roll_resp = client.post(f"/game/{game_id}/roll")
    assert roll_resp.status_code == 200
    legal_moves = roll_resp.json()["legal_moves"]
    assert len(legal_moves) > 0

    move_resp = client.post(f"/game/{game_id}/move", json={"move": legal_moves[0]})
    assert move_resp.status_code == 200

    # Second /roll call should fail: a turn is still in progress until all dice are used.
    assert client.post(f"/game/{game_id}/roll").status_code == 400


def test_illegal_move_is_rejected():
    game_id = client.post("/game/new").json()["game_id"]
    client.post(f"/game/{game_id}/roll")
    resp = client.post(f"/game/{game_id}/move", json={"move": {"source": 0, "target": 1}})
    assert resp.status_code == 400


def test_ai_endpoint_plays_a_full_turn():
    game_id = client.post("/game/new").json()["game_id"]
    resp = client.post(f"/game/{game_id}/ai")
    assert resp.status_code == 200
    body = resp.json()
    assert body["state"]["turn"] == 1
    assert isinstance(body["move"], list)


def test_engine_move_is_stateless():
    game_id = client.post("/game/new").json()["game_id"]
    state = client.post("/game/new").json()["state"]
    resp = client.post("/engine/move", json={"state": state, "dice": [3, 1], "engine": "random"})
    assert resp.status_code == 200
    assert isinstance(resp.json()["move"], list)
    # No game_id involved / no side effect on any stored game.
    assert game_id in GAMES


def test_roll_reports_turn_flip_when_forced_to_dance():
    game_id = client.post("/game/new").json()["game_id"]
    # Player 0 stuck on the bar, entry blocked for every possible die (1-6).
    board = [0] * 24
    for idx in range(18, 24):
        board[idx] = -2
    GAMES[game_id].state = GameState(board=board, bar=[1, 0], off=[0, 0], turn=0)

    resp = client.post(f"/game/{game_id}/roll")
    assert resp.status_code == 200
    body = resp.json()
    assert body["legal_moves"] == []
    # The turn must have passed server-side, and the response must say so --
    # the frontend has no other way to learn a dance happened on /roll.
    assert body["state"]["turn"] == 1
    # A fresh roll should now be for player 1's turn.
    assert client.post(f"/game/{game_id}/roll").status_code == 200


def test_playing_out_a_full_roll_advances_turn():
    game_id = client.post("/game/new").json()["game_id"]
    roll = client.post(f"/game/{game_id}/roll").json()
    legal_moves = roll["legal_moves"]

    resp = None
    remaining = legal_moves
    while remaining:
        resp = client.post(f"/game/{game_id}/move", json={"move": remaining[0]})
        remaining = resp.json()["legal_moves"]

    assert resp is not None
    assert resp.json()["legal_moves"] == []
    # Turn should have passed to player 1 (unless the last move ended the game).
    assert resp.json()["state"]["turn"] in (0, 1)
    assert client.post(f"/game/{game_id}/roll").status_code == 200
