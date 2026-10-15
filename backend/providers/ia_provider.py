"""Provider: unico lugar do projeto que fala com o servico externo de IA (Gemini).

A rota nao sabe que existe Gemini; ela so chama `gerar_texto`. Trocar de provedor
significa mexer apenas neste arquivo.
"""

from google import genai
from google.genai import types

import config


class ProviderNaoConfigurado(Exception):
    """GEMINI_API_KEY ausente no .env do backend."""


class ErroProvider(Exception):
    """O servico externo falhou ou devolveu uma resposta vazia."""


_cliente: genai.Client | None = None


def _get_cliente() -> genai.Client:
    global _cliente
    if _cliente is None:
        if not config.GEMINI_API_KEY.strip():
            raise ProviderNaoConfigurado(
                "GEMINI_API_KEY nao configurada no backend. Preencha o .env do backend."
            )
        _cliente = genai.Client(api_key=config.GEMINI_API_KEY)
    return _cliente


def _montar_config(json_mode: bool, pensar: bool) -> types.GenerateContentConfig:
    extra = {"response_mime_type": "application/json"} if json_mode else {}
    if not pensar:
        # "Pensamento" desligado nas tarefas curtas (suspeito e avaliacao): resposta mais rapida.
        extra["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
    return types.GenerateContentConfig(**extra)


def gerar_texto(prompt: str, json_mode: bool = False, pensar: bool = True) -> str:
    """Envia o prompt ao Gemini e devolve o texto gerado."""
    cliente = _get_cliente()
    try:
        resposta = cliente.models.generate_content(
            model=config.GEMINI_MODEL, contents=prompt, config=_montar_config(json_mode, pensar)
        )
    except Exception as exc:
        raise ErroProvider(f"Falha ao chamar o Gemini: {exc}") from exc

    texto = (resposta.text or "").strip()
    if not texto:
        raise ErroProvider("O Gemini devolveu uma resposta vazia.")
    return texto
