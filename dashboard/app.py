"""Nexus Analytics — Dashboard Streamlit.

Page d'accueil : KPIs globaux du projet LFL.

Lancement :
    uv run streamlit run dashboard/app.py

Variables d'environnement requises (idem pipeline) :
    GCP_PROJECT_ID   — identifiant du projet GCP
"""

import streamlit as st

from dashboard.queries import fetch_kpi_summary

st.set_page_config(
    page_title="Nexus Analytics — LFL",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🎮 Nexus Analytics — La Ligue Française")
st.caption("Données historiques LFL (D1 + D2) — 2020 à 2026 — Source : Leaguepedia")

st.markdown("---")

with st.spinner("Chargement des KPIs..."):
    try:
        kpi = fetch_kpi_summary()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Parties analysées", f"{kpi['total_games']:,}")
        col2.metric("Joueurs uniques", f"{kpi['total_players']:,}")
        col3.metric("Tournois couverts", f"{kpi['total_tournaments']:,}")
        col4.metric("Patches distincts", f"{kpi['total_patches']:,}")

        st.markdown(f"**Période couverte** : {kpi['date_min']} → {kpi['date_max']}")

    except Exception as exc:
        st.error(f"Erreur de connexion BigQuery : {exc}")
        st.info(
            "Vérifiez que GCP_PROJECT_ID est défini et que vos "
            "Application Default Credentials sont configurées."
        )

st.markdown("---")
st.markdown(
    """
### Navigation
Utilisez le menu à gauche pour explorer :

| Page | Contenu |
|------|---------|
| 🏆 Joueurs | Classement, KDA, winrate — filtrable par nombre de parties |
| 🐉 Champions | Pick rates, win rates, distribution par rôle |
| ⚔️ Drafts | Historique de draft par équipe (picks & bans) |
| 📈 Méta | Tendances méta par patch — scatter pick rate vs win rate |
"""
)

st.sidebar.markdown("## Nexus Analytics")
st.sidebar.markdown("**LFL Data Platform**")
st.sidebar.markdown("---")
st.sidebar.info(
    "Source des données : Leaguepedia Cargo API + Oracle's Elixir\n\n"
    "Pipeline : GCS Bronze → Silver → BigQuery Gold (dbt)"
)
