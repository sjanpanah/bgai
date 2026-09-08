import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import engine, game, version

app = FastAPI(title="Backgammon vs AI")

allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(game.router)
app.include_router(engine.router)
app.include_router(version.router)
