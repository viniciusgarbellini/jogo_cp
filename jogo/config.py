import os

from dotenv import load_dotenv

load_dotenv()

# O jogo nao conhece mais a chave do Gemini: ele so fala com a API do grupo (pasta backend/).
IA_API_URL = os.environ.get("IA_API_URL", "http://127.0.0.1:8000").rstrip("/")
IA_API_KEY = os.environ.get("IA_API_KEY", "")

# Tempo maximo de espera por resposta da API (a geracao do caso com "thinking" leva ~10 s).
IA_API_TIMEOUT = float(os.environ.get("IA_API_TIMEOUT", "90"))

NUM_PERGUNTAS = 6
PONTUACAO_MAXIMA = 2

# Quantas vezes tentar cada chamada antes de desistir (1 = sem retry).
TENTATIVAS = 2
