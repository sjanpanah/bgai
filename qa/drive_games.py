"""Play whole games through the real API with random-legal human moves.

This is how the 2026-09-08 pass found its blocker (`report.md`, F2.3): the unit
suite was green while 56-76% of real games died at bear-off, because no test
ever drove a game far enough to reach that code. Engine-vs-engine benchmarks are
blind to it too -- they never touch the human move endpoints.

Reports HTTP failures and games that never finish. Runs in-process against the
FastAPI app, so it needs no server:

    cd backend && PYTHONPATH=. .venv/bin/python ../qa/drive_games.py 42 25
"""

import random
import sys

from fastapi.testclient import TestClient

from main import app


def drive(seed: int, games: int, engine: str = "random", ply_cap: int = 600) -> int:
    client = TestClient(app)
    rng = random.Random(seed)
    errors: list[tuple] = []
    finished = stalled = 0

    for game in range(games):
        game_id = client.post("/game/new").json()["game_id"]
        for _ in range(ply_cap):
            rolled = client.post(f"/game/{game_id}/roll")
            if rolled.status_code != 200:
                errors.append((game, "roll", rolled.status_code, rolled.text[:120]))
                break

            moves = rolled.json()["legal_moves"]
            while moves:
                chosen = rng.choice(moves)
                moved = client.post(f"/game/{game_id}/move", json={"move": chosen})
                if moved.status_code != 200:
                    errors.append((game, "move", moved.status_code, moved.text[:120]))
                    moves = None
                    break
                body = moved.json()
                if body.get("game_over"):
                    finished += 1
                    moves = None
                    break
                moves = body["legal_moves"]
            if moves is None:
                break

            ai = client.post(f"/game/{game_id}/ai?engine={engine}")
            if ai.status_code != 200:
                errors.append((game, "ai", ai.status_code, ai.text[:120]))
                break
            if ai.json().get("game_over"):
                finished += 1
                break
        else:
            stalled += 1

    print(
        f"seed {seed}: {games} games vs {engine} -> "
        f"{finished} finished, {stalled} hit the ply cap, {len(errors)} errors"
    )
    for error in errors[:5]:
        print("  ", error)
    return 1 if errors else 0


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 42
    games = int(sys.argv[2]) if len(sys.argv) > 2 else 25
    sys.exit(drive(seed, games))
