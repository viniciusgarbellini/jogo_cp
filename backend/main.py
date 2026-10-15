"""API do grupo: encapsula a chamada ao Gemini usada pelo jogo O Interrogatorio.

Rodar: uvicorn main:app --reload   (Swagger em http://localhost:8000/docs)
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
from routers import ia_generativa

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

app = FastAPI(
    title="O Interrogatório — API de IA generativa",
    description=(
        "Back-end do jogo **O Interrogatório**. O jogo não fala mais com o Gemini: "
        "ele chama `POST /v1/ia-generativa/texto` com o header `X-API-Key`, e esta API "
        "chama o Gemini internamente."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)

app.include_router(ia_generativa.router)


@app.get("/health", tags=["Status"], summary="Verifica se a API está no ar (sem autenticação)")
def health():
    return {"status": "ok", "modelo": config.GEMINI_MODEL}
