import base64
from html import escape
from pathlib import Path

import streamlit as st

import ia
from config import IA_API_URL, NUM_PERGUNTAS, PONTUACAO_MAXIMA

BASE = Path(__file__).parent
ASSETS = BASE / "assets"

st.set_page_config(page_title="O Interrogatório", page_icon=str(ASSETS / "icone.jpg"), layout="wide")


@st.cache_resource
def _data_uri(nome: str) -> str:
    dados = base64.b64encode((ASSETS / nome).read_bytes()).decode()
    return f"data:image/jpeg;base64,{dados}"


def aplicar_estilo(fundo: str):
    """Injeta o CSS e define a imagem de fundo (menu: cena do crime; demais telas: suspeito)."""
    css = (BASE / "estilo.css").read_text(encoding="utf-8")
    st.markdown(
        f'<style>{css}\n:root {{ --bg-img: url("{_data_uri(fundo)}"); }}</style><div class="fundo-ativo"></div>',
        unsafe_allow_html=True,
    )


def iniciar_nova_partida():
    with st.spinner("Montando o caso..."):
        try:
            caso = ia.gerar_caso()
        except ia.ErroIA as exc:
            st.session_state["erro"] = str(exc)
            return
    st.session_state["caso"] = caso
    st.session_state["historico"] = []
    st.session_state["perguntas_restantes"] = NUM_PERGUNTAS
    st.session_state["fase"] = "interrogatorio"
    st.session_state["resultado"] = None
    st.session_state.pop("erro", None)


def tela_menu():
    aplicar_estilo("cena_crime.jpg")
    st.markdown(
        f"""
        <div class="menu">
          <img class="icone" src="{_data_uri('icone.jpg')}" alt="">
          <h1>O Interrogatório</h1>
          <div class="sub">Detetive de Mentiras</div>
          <div class="slogan">"Descubra a mentira. Encontre a verdade."</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _, centro, _ = st.columns([1, 2, 1])
    with centro:
        if st.button("Começar partida", type="primary", width="stretch"):
            iniciar_nova_partida()
            st.rerun()
    st.markdown(
        f"""
        <div class="protocolo">
          <div class="titulo">COMO JOGAR · 3 ETAPAS</div>
          <div class="passo"><div class="num">01</div><div><b>Faça até {NUM_PERGUNTAS} perguntas livres</b>
            <span>Interrogue o suspeito com texto livre e coloque a história dele à prova.</span></div></div>
          <div class="passo"><div class="num">02</div><div><b>Encontre a contradição</b>
            <span>Compare horários, detalhes e hesitações nas respostas.</span></div></div>
          <div class="passo"><div class="num">03</div><div><b>Acuse com precisão</b>
            <span>Aponte a mentira exata e explique o que realmente aconteceu.</span></div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(f"IA generativa via API do grupo: `{IA_API_URL}{ia.ROTA_TEXTO}`")


def ficha_do_caso(caso: dict) -> str:
    return (
        '<div class="ficha"><div class="rotulo">FICHA DO CASO</div>'
        f'<div class="crime">{escape(caso["crime"])}</div>'
        f'<div class="linha">LOCAL: <b>{escape(caso["local"])}</b></div>'
        f'<div class="linha">HORÁRIO: <b>{escape(caso["horario"])}</b></div>'
        f'<div class="linha">SUSPEITO: <b>{escape(caso["suspeito"])}</b></div></div>'
    )


def aviso_offline(caso: dict):
    """Deixa claro para o jogador quando a IA caiu e o jogo esta no fallback local."""
    if caso.get("offline"):
        st.warning(
            "**MODO OFFLINE** — a API do grupo (backend) nao respondeu, entao o jogo esta usando um caso "
            "fixo e um suspeito deterministico (sem IA). A partida continua jogavel. "
            "Clique em *Nova partida* para tentar gerar um caso com IA novamente.",
            icon="⚠️",
        )


def tela_interrogatorio(caso: dict):
    aplicar_estilo("suspeito.jpg")
    aviso_offline(caso)
    restantes = st.session_state["perguntas_restantes"]
    historico = st.session_state["historico"]

    bolas = "".join(
        f'<div class="bola{" cheia" if i < restantes else ""}"></div>' for i in range(NUM_PERGUNTAS)
    )
    st.markdown(
        f'<div class="hud">{ficha_do_caso(caso)}'
        '<div class="contador"><div class="rotulo">PERGUNTAS RESTANTES</div>'
        f'<div class="bolas">{bolas}<span class="num">{restantes}/{NUM_PERGUNTAS}</span></div></div></div>',
        unsafe_allow_html=True,
    )

    if historico:
        legenda = f'<div class="legenda">“{escape(historico[-1]["resposta"])}”</div>'
        falante = f'<div class="falante">● {escape(caso["suspeito"]).upper()} · DEPOIMENTO</div>'
    else:
        legenda = '<div class="legenda dica">Faça sua primeira pergunta ao suspeito.</div>'
        falante = ""
    st.markdown(f'<div class="palco">{falante}{legenda}</div>', unsafe_allow_html=True)

    if historico:
        with st.expander(f"Histórico da sessão ({len(historico)} registros)"):
            for turno in historico:
                with st.chat_message("user"):
                    st.write(turno["pergunta"])
                with st.chat_message("assistant", avatar="🕵️"):
                    st.write(turno["resposta"])

    if restantes > 0:
        pergunta = st.chat_input("Faça sua próxima pergunta ao suspeito...")
        if pergunta:
            with st.spinner(f"{caso['suspeito']} está pensando..."):
                try:
                    resposta = ia.perguntar_suspeito(pergunta, historico, caso)
                except ia.ErroIA as exc:
                    st.error(f"Erro ao falar com o suspeito: {exc} (a pergunta não foi consumida)")
                    return
            historico.append({"pergunta": pergunta, "resposta": resposta})
            st.session_state["perguntas_restantes"] -= 1
            st.rerun()
    else:
        st.warning("Suas perguntas acabaram. Hora de apresentar sua acusação.")
        if st.button("Fazer acusação final", type="primary"):
            st.session_state["fase"] = "acusacao"
            st.rerun()


def tela_acusacao(caso: dict):
    aplicar_estilo("suspeito.jpg")
    aviso_offline(caso)
    _, centro, _ = st.columns([1, 3, 1])
    with centro:
        st.markdown(
            '<div class="cartao-topo">PROTOCOLO DE ACUSAÇÃO</div><div class="cartao-titulo">Acusação final</div>',
            unsafe_allow_html=True,
        )
        st.markdown(ficha_do_caso(caso), unsafe_allow_html=True)

        with st.form("form_acusacao"):
            mentira = st.text_area(
                "1. Qual foi a mentira do suspeito?",
                placeholder="Aponte a inconsistência ou o álibi falso declarado durante o interrogatório.",
            )
            verdade = st.text_area(
                "2. O que realmente aconteceu?",
                placeholder="Explique como o crime foi executado.",
            )
            enviado = st.form_submit_button("Acusar e concluir caso", type="primary", width="stretch")

        if enviado:
            if not (mentira.strip() and verdade.strip()):
                st.error("Preencha as duas respostas antes de acusar.")
                return
            with st.spinner("Avaliando sua acusação..."):
                try:
                    resultado = ia.avaliar_acusacao(mentira, verdade, caso)
                except ia.ErroIA as exc:
                    st.error(f"Erro ao avaliar a acusação: {exc}")
                    return
            st.session_state["resultado"] = resultado
            st.session_state["fase"] = "resultado"
            st.toast("Caso concluido. Montando o veredito...", icon="🕵️")
            st.rerun()


def linha_criterio(texto: str, acertou: bool) -> str:
    classe, icone, pts = ("ok", "✓", "+1 PONTO") if acertou else ("erro", "✕", "0 PONTOS")
    return (
        f'<div class="criterio {classe}"><div class="icone">{icone}</div>'
        f"<div><b>{texto}</b></div><div class=\"pts\">{pts}</div></div>"
    )


def tela_resultado(caso: dict):
    aplicar_estilo("suspeito.jpg")
    resultado = st.session_state["resultado"]
    pontuacao = ia.calcular_pontuacao(resultado)

    _, centro, _ = st.columns([1, 3, 1])
    with centro:
        st.markdown(
            '<div class="cartao-topo">VEREDITO</div>'
            f'<div class="cartao-titulo">Resultado: {pontuacao}/{PONTUACAO_MAXIMA}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            linha_criterio("Identificou a mentira", bool(resultado.get("identificou_mentira")))
            + linha_criterio("Explicou o que aconteceu", bool(resultado.get("explicou_verdade"))),
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="parecer"><div class="rotulo">PARECER DA IA</div>'
            f'{escape(str(resultado.get("justificativa", "")))}</div>',
            unsafe_allow_html=True,
        )

        if resultado.get("offline"):
            st.caption(
                "Esta acusacao foi avaliada em modo offline (comparacao local de palavras-chave), "
                "porque a API de IA nao respondeu."
            )

        with st.expander("Ver a verdade completa do caso"):
            st.write(f"**O que realmente aconteceu:** {caso['verdade']}")
            st.write(f"**A mentira do suspeito:** {caso['mentira_principal']}")

        if st.session_state.get("erro"):
            st.error(st.session_state["erro"])
        if st.button("Nova partida", type="primary", width="stretch"):
            iniciar_nova_partida()
            st.rerun()


if "fase" not in st.session_state:
    tela_menu()
    if st.session_state.get("erro"):
        st.error(st.session_state["erro"])
else:
    caso = st.session_state["caso"]
    fase = st.session_state["fase"]

    if fase == "interrogatorio":
        tela_interrogatorio(caso)
    elif fase == "acusacao":
        tela_acusacao(caso)
    elif fase == "resultado":
        tela_resultado(caso)
