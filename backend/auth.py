"""Autenticacao simples por API Key no header X-API-Key."""

import secrets

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

import config

# auto_error=False para devolvermos 401 com mensagem propria em vez do 403 padrao.
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verificar_api_key(chave: str | None = Security(api_key_header)) -> None:
    if not config.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API_KEY nao configurada no servidor. Preencha o .env do backend.",
        )
    if not chave or not secrets.compare_digest(chave, config.API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key ausente ou invalida.",
        )
