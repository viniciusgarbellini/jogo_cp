"""Rota de IA generativa (texto). Recebe o prompt do jogo e delega ao provider."""

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

import config
from auth import verificar_api_key
from providers import ia_provider

log = logging.getLogger("ia_generativa")

router = APIRouter(
    prefix="/v1/ia-generativa",
    tags=["IA generativa"],
    dependencies=[Depends(verificar_api_key)],
)


class TextoRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Contexto/prompt montado pelo jogo.")
    json_mode: bool = Field(False, description="Pede ao modelo uma resposta em JSON puro.")
    pensar: bool = Field(True, description="Liga o 'thinking' do modelo (mais lento, mais coerente).")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "prompt": "Voce e um suspeito sendo interrogado. Pergunta: onde voce estava as 22h?",
                    "json_mode": False,
                    "pensar": False,
                }
            ]
        }
    }


class TextoResponse(BaseModel):
    texto: str
    modelo: str


@router.post(
    "/texto",
    response_model=TextoResponse,
    summary="Gera texto com a IA generativa",
    responses={
        401: {"description": "X-API-Key ausente ou invalida"},
        502: {"description": "O servico de IA externo falhou"},
        503: {"description": "Backend sem chave configurada"},
    },
)
def gerar_texto(body: TextoRequest) -> TextoResponse:
    inicio = time.perf_counter()
    try:
        texto = ia_provider.gerar_texto(body.prompt, json_mode=body.json_mode, pensar=body.pensar)
    except ia_provider.ProviderNaoConfigurado as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except ia_provider.ErroProvider as exc:
        log.warning("falha no provider: %s", exc)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    log.info(
        "texto gerado | json_mode=%s pensar=%s | %d chars | %.1fs",
        body.json_mode, body.pensar, len(texto), time.perf_counter() - inicio,
    )
    return TextoResponse(texto=texto, modelo=config.GEMINI_MODEL)
