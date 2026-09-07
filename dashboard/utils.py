"""Utilitaires partagés pour le dashboard Streamlit Nexus Analytics."""

import streamlit as st


def question_metier(question: str, source: str) -> None:
    """Affiche la question métier qui justifie la page.

    Args:
        question: La question posée par Nexus Analytics, telle qu'exprimée dans les entretiens.
        source: Qui a posé la question (ex. "Yasmine — Analyste senior").
    """
    st.markdown(
        f"<div style='"
        f"background:#f0f6ff; border-left:4px solid #1f77b4; "
        f"padding:12px 18px; border-radius:0 6px 6px 0; margin:8px 0 20px 0'>"
        f"<span style='color:#1f77b4; font-weight:600; font-size:0.9em'>"
        f"📋 Question métier</span>"
        f"<span style='color:#888; font-size:0.82em; margin-left:10px'>{source}</span><br>"
        f"<span style='font-size:1em; color:#1a1a1a'><em>{question}</em></span>"
        f"</div>",
        unsafe_allow_html=True,
    )
