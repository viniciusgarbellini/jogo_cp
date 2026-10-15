"""Chamadas de IA generativa e pontuacao do jogo.

Ver proposta_final.md secao 12 (arquitetura) e Entrega_CP5.md (Diario de Mudancas).

Decisoes de engenharia registradas aqui:
- O jogo NAO chama mais o Gemini. Toda geracao de texto passa pela API do grupo
  (pasta backend/, FastAPI): POST {IA_API_URL}/v1/ia-generativa/texto com o header
  X-API-Key. O backend e quem guarda a GEMINI_API_KEY e chama o servico externo.
- Os prompts continuam aqui no jogo (sao regra de jogo); a API e um gateway de texto.
- "Pensamento" (thinking) desligado nas chamadas de interrogatorio e avaliacao, que sao
  tarefas curtas e acontecem 7x por partida; mantido na geracao do caso, onde a coerencia
  da trama importa mais que o tempo de resposta. O jogo so informa `pensar` para a API.
- Toda chamada tem retry e, se a API ficar indisponivel, o jogo cai em MODO OFFLINE
  (caso fixo + suspeito deterministico) em vez de travar.
"""

import json
import logging
import random
import time
from pathlib import Path

import requests

import prompts
from config import IA_API_KEY, IA_API_TIMEOUT, IA_API_URL, TENTATIVAS

BASE = Path(__file__).parent
ARQUIVO_CASO_OFFLINE = BASE / "caso_offline.json"
ROTA_TEXTO = "/v1/ia-generativa/texto"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("jogo.ia")


class ErroIA(Exception):
    """Erro amigavel para exibir na interface quando a API falha ou responde algo inutilizavel."""


# ---------------------------------------------------------------- API do grupo


def _chamar(prompt: str, json_mode: bool = False, pensar: bool = True) -> str:
    """Uma chamada a API do grupo. Devolve o texto cru e garante que nao veio vazio."""
    if not IA_API_KEY.strip():
        raise ErroIA("IA_API_KEY nao configurada. Copie .env.example para .env e preencha a chave.")

    url = f"{IA_API_URL}{ROTA_TEXTO}"
    inicio = time.perf_counter()
    resposta = requests.post(
        url,
        json={"prompt": prompt, "json_mode": json_mode, "pensar": pensar},
        headers={"X-API-Key": IA_API_KEY},
        timeout=IA_API_TIMEOUT,
    )
    log.info("POST %s -> %s (%.1fs)", url, resposta.status_code, time.perf_counter() - inicio)

    if resposta.status_code in (401, 403):
        # Chave errada nao melhora com retry: vira ErroIA direto.
        raise ErroIA("A API recusou a IA_API_KEY. Confira se e igual a API_KEY do backend.")
    resposta.raise_for_status()

    texto = (resposta.json().get("texto") or "").strip()
    if not texto:
        raise ValueError("a API devolveu uma resposta vazia")
    return texto


def _com_retry(funcao, descricao: str):
    """Executa `funcao` ate TENTATIVAS vezes. Se todas falharem, levanta ErroIA."""
    ultimo_erro = None
    for _ in range(max(1, TENTATIVAS)):
        try:
            return funcao()
        except ErroIA:
            raise  # erro nosso (ex.: chave ausente) nao melhora com retry
        except Exception as exc:
            ultimo_erro = exc
    raise ErroIA(f"{descricao}: {ultimo_erro}") from ultimo_erro


# ------------------------------------------------------------- geracao do caso


def _caso_valido(caso: dict) -> list[str]:
    """Devolve a lista de campos obrigatorios ausentes ou vazios."""
    return [c for c in prompts.CAMPOS_CASO if not caso.get(c)]


def _gerar_caso_uma_vez() -> dict:
    caso = json.loads(_chamar(prompts.PROMPT_GERADOR_CASO, json_mode=True, pensar=True))
    if not isinstance(caso, dict):
        raise ValueError("o caso gerado nao e um objeto JSON")
    faltando = _caso_valido(caso)
    if faltando:
        raise ValueError(f"caso incompleto (faltou: {', '.join(faltando)})")
    return caso


def carregar_caso_offline() -> dict:
    """Caso fixo usado quando a API esta fora. Nao substitui a IA: e so o fallback."""
    try:
        caso = json.loads(ARQUIVO_CASO_OFFLINE.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ErroIA(f"O caso offline nao pode ser lido: {exc}") from exc
    faltando = _caso_valido(caso)
    if faltando:
        raise ErroIA(f"O caso offline esta incompleto (faltou: {', '.join(faltando)}).")
    caso["offline"] = True
    return caso


def gerar_caso() -> dict:
    """Gera o caso pela IA. Se a API falhar em todas as tentativas, cai no caso offline."""
    try:
        return _com_retry(_gerar_caso_uma_vez, "Nao foi possivel gerar o caso")
    except ErroIA:
        return carregar_caso_offline()


# ------------------------------------------------------------- interrogatorio


def _resposta_offline(pergunta: str, caso: dict) -> str:
    """Suspeito deterministico do modo offline: evasivo, sem entregar a mentira.

    Nao usa IA. Serve apenas para a partida continuar jogavel se a API cair no meio.
    """
    texto = pergunta.lower()
    evidencias = caso.get("evidencias") or []
    pode = caso.get("pode_revelar") or []

    if any(p in texto for p in ("onde", "lugar", "local")):
        return f"Eu ja disse: {caso['versao_oficial']} Nao tenho mais o que acrescentar."
    if any(p in texto for p in ("hora", "horario", "quando")):
        return f"Foi no horario que ja consta na ficha: {caso['horario']}. Nao olhei o relogio a toda hora."
    if any(p in texto for p in ("quem", "alguem", "testemunha", "viu")):
        return "Nao vi ninguem que possa confirmar isso. Estava sozinho."
    if any(p in texto for p in ("por que", "porque", "motivo")):
        return "Nao sei o que voce quer que eu diga. Eu nao tinha razao nenhuma para fazer isso."
    if pode:
        return f"{random.choice(pode)} Mas isso nao prova nada contra mim."
    if evidencias:
        return f"Sobre isso eu so sei que {random.choice(evidencias)}. Nada alem."
    return "Nao me lembro desse detalhe. Faz tempo e eu estava nervoso."


def perguntar_suspeito(pergunta: str, historico: list[dict], caso: dict) -> str:
    """Resposta do suspeito. No modo offline usa o suspeito deterministico."""
    if caso.get("offline"):
        return _resposta_offline(pergunta, caso)

    prompt = prompts.prompt_suspeito(caso, historico, pergunta)
    resposta = _com_retry(
        lambda: _chamar(prompt, json_mode=False, pensar=False),
        "O suspeito nao respondeu",
    )
    return resposta.strip()


# ------------------------------------------------------------------- avaliacao


CAMPOS_AVALIACAO = ["identificou_mentira", "explicou_verdade", "justificativa"]


def _avaliar_uma_vez(prompt: str) -> dict:
    resultado = json.loads(_chamar(prompt, json_mode=True, pensar=False))
    if not isinstance(resultado, dict):
        raise ValueError("a avaliacao nao e um objeto JSON")
    faltando = [c for c in CAMPOS_AVALIACAO if c not in resultado]
    if faltando:
        raise ValueError(f"avaliacao incompleta (faltou: {', '.join(faltando)})")
    return resultado


def _avaliacao_offline(resposta_mentira: str, resposta_verdade: str, caso: dict) -> dict:
    """Avaliacao local por sobreposicao de palavras. Usada so quando a API esta fora."""

    def parecido(resposta: str, gabarito: str) -> bool:
        irrelevantes = {
            "que", "com", "para", "uma", "dos", "das", "nao", "sobre", "pelo", "pela",
            "foi", "era", "mas", "por", "num", "numa", "ele", "ela", "seu", "sua",
        }
        palavras = {p for p in gabarito.lower().split() if len(p) > 3 and p not in irrelevantes}
        if not palavras:
            return False
        ditas = set(resposta.lower().split())
        return len(palavras & ditas) / len(palavras) >= 0.3

    return {
        "identificou_mentira": parecido(resposta_mentira, caso["mentira_principal"]),
        "explicou_verdade": parecido(resposta_verdade, caso["verdade"]),
        "justificativa": (
            "Avaliacao feita em MODO OFFLINE, por comparacao de palavras-chave, "
            "porque a API de IA nao respondeu. O resultado e aproximado."
        ),
        "offline": True,
    }


def avaliar_acusacao(resposta_mentira: str, resposta_verdade: str, caso: dict) -> dict:
    """Avalia a acusacao. Cai na avaliacao local se a API estiver fora."""
    if caso.get("offline"):
        return _avaliacao_offline(resposta_mentira, resposta_verdade, caso)

    prompt = prompts.prompt_avaliador(caso, resposta_mentira, resposta_verdade)
    try:
        return _com_retry(lambda: _avaliar_uma_vez(prompt), "Nao foi possivel avaliar a acusacao")
    except ErroIA:
        return _avaliacao_offline(resposta_mentira, resposta_verdade, caso)


def calcular_pontuacao(resultado: dict) -> int:
    """Soma os 2 criterios booleanos da avaliacao. A IA nunca decide a nota."""
    pontos = 0
    if resultado.get("identificou_mentira"):
        pontos += 1
    if resultado.get("explicou_verdade"):
        pontos += 1
    return pontos
