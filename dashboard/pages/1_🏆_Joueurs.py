"""Page Joueurs — classement LFL par stats de carrière."""

import plotly.express as px
import streamlit as st

from dashboard.queries import fetch_players, fetch_seasons
from dashboard.utils import question_metier

st.set_page_config(page_title="Joueurs — Nexus Analytics", page_icon="🏆", layout="wide")

st.title("🏆 Joueurs LFL")
st.caption("Statistiques agrégées sur toute la carrière LFL (D1 + D2)")

question_metier(
    "Quels sont les résultats et statistiques individuelles des joueurs LFL "
    "— qui sont les joueurs les plus performants cette saison, dans quelle équipe évoluent-ils ?",
    "Brief §3.2 + Yasmine Karim — Analyste senior",
)

# ─── Filtres ────────────────────────────────────────────────────────────────

with st.spinner("Chargement des saisons..."):
    seasons = fetch_seasons()

col_f0, col_f1, col_f2 = st.columns([3, 2, 2])
with col_f0:
    selected_season = st.selectbox("Saison", options=["Toutes les saisons"] + seasons)
with col_f1:
    min_games = st.slider("Parties minimum", min_value=1, max_value=100, value=10, step=5)
with col_f2:
    sort_col = st.selectbox(
        "Trier par",
        options=["total_games", "win_rate_pct", "kda", "avg_kills", "avg_cs"],
        format_func=lambda x: {
            "total_games": "Parties jouées",
            "win_rate_pct": "Win rate %",
            "kda": "KDA",
            "avg_kills": "Kills moyens",
            "avg_cs": "CS moyen",
        }[x],
    )

season_filter = None if selected_season == "Toutes les saisons" else selected_season

with st.spinner("Chargement..."):
    df = fetch_players(min_games=min_games, season=season_filter)

if df.empty:
    st.warning("Aucun joueur trouvé avec ces critères.")
    st.stop()

df = df.sort_values(sort_col, ascending=False)

# ─── Top 10 graphique ────────────────────────────────────────────────────────

st.markdown("### Top 10 joueurs")

top10 = df.head(10)
label_map = {
    "total_games": "Parties jouées",
    "win_rate_pct": "Win rate (%)",
    "kda": "KDA",
    "avg_kills": "Kills moyens",
    "avg_cs": "CS moyen",
}

fig = px.bar(
    top10,
    x="player_name",
    y=sort_col,
    color=sort_col,
    color_continuous_scale="Blues",
    labels={"player_name": "Joueur", sort_col: label_map[sort_col]},
    text_auto=".2f",
)
fig.update_layout(showlegend=False, coloraxis_showscale=False, height=400)
fig.update_traces(textposition="outside")
st.plotly_chart(fig, width="stretch")

# ─── Tableau complet ─────────────────────────────────────────────────────────

st.markdown(f"### Classement complet ({len(df)} joueurs)")

cols_display = [
    c
    for c in [
        "player_name",
        "current_team",
        "total_games",
        "win_rate_pct",
        "kda",
        "avg_kills",
        "avg_deaths",
        "avg_assists",
        "avg_cs",
    ]
    if c in df.columns
]

st.dataframe(
    df[cols_display].rename(
        columns={
            "player_name": "Joueur",
            "current_team": "Équipe actuelle",
            "total_games": "Parties",
            "win_rate_pct": "Win% ",
            "kda": "KDA",
            "avg_kills": "Kills moy.",
            "avg_deaths": "Morts moy.",
            "avg_assists": "Assists moy.",
            "avg_cs": "CS moy.",
        }
    ),
    width="stretch",
    hide_index=True,
    column_config={
        "Win% ": st.column_config.ProgressColumn(
            "Win %", min_value=0, max_value=100, format="%.1f%%"
        ),
        "KDA": st.column_config.NumberColumn(format="%.2f"),
    },
)
