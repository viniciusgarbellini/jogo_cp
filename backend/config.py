import os

from dotenv import load_dotenv

load_dotenv()

# Chave do servico externo (Gemini). So o backend conhece essa chave.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

# Chave que os clientes (o jogo) precisam mandar no header X-API-Key.
API_KEY = os.environ.get("API_KEY", "")

# Origens liberadas no CORS, separadas por virgula. Padrao: o Streamlit local.
CORS_ORIGINS = [
    origem.strip()
    for origem in os.environ.get("CORS_ORIGINS", "http://localhost:8501").split(",")
    if origem.strip()
]
