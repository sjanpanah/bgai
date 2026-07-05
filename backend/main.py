from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import engine, game

app = FastAPI(title="Backgammon vs AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(game.router)
app.include_router(engine.router)
