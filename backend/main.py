"""API do grupo: encapsula a chamada ao Gemini usada pelo jogo O Interrogatorio.

Rodar: uvicorn main:app --reload   (Swagger em http://localhost:8000/docs)
"""

import logging

import truststore

# Usa os certificados do sistema operacional. Sem isso, redes com inspecao de HTTPS
# (ex.: rede da faculdade) derrubam a chamada ao Gemini com CERTIFICATE_VERIFY_FAILED.
truststore.inject_into_ssl()

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

import config  # noqa: E402
from routers import ia_generativa  # noqa: E402

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
