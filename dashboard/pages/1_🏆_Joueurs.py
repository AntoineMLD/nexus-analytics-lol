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
        "teams_count",
        "total_games_in_team",
        "last_game_date",
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
            "teams_count": "Nb équipes",
            "total_games_in_team": "Parties (équipe actuelle)",
            "last_game_date": "Dernier match",
            "total_games": "Parties (carrière)",
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
        "Nb équipes": st.column_config.NumberColumn("Équipes jouées", format="%d"),
        "Parties (équipe actuelle)": st.column_config.NumberColumn(format="%d"),
    },
)

# ─── Historique d'équipe par joueur ──────────────────────────────────────────

st.markdown("---")
st.markdown("### 🔄 Trajectoire d'un joueur")
st.caption("Sélectionnez un joueur pour voir l'historique complet de ses équipes.")

if "teams_history" in df.columns and "player_name" in df.columns:
    selected = st.selectbox(
        "Joueur",
        options=df["player_name"].tolist(),
        key="player_team_history",
    )
    row = df[df["player_name"] == selected].iloc[0]

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Équipe actuelle", row.get("current_team") or "—")
    col_b.metric(
        "Parties dans l'équipe",
        int(row["total_games_in_team"]) if row.get("total_games_in_team") else "—",
    )
    col_c.metric(
        "Équipes jouées au total", int(row["teams_count"]) if row.get("teams_count") else "—"
    )

    history = row.get("teams_history") or ""
    if history:
        st.markdown(
            f"<div style='background:#f8f8f8; border:1px solid #ddd; border-radius:8px; "
            f"padding:14px 20px; font-size:1.05em; margin-top:8px'>"
            f"<strong>Parcours :</strong> {history}"
            f"</div>",
            unsafe_allow_html=True,
        )

# ─── Mobilité des joueurs ─────────────────────────────────────────────────────

st.markdown("---")
st.markdown("### 📊 Mobilité des joueurs")
st.caption("Joueurs ayant changé le plus souvent d'équipe sur leur carrière LFL.")

if "teams_count" in df.columns:
    mobile = (
        df[df["teams_count"] > 1]
        .sort_values("teams_count", ascending=False)
        .head(15)[["player_name", "current_team", "teams_count", "teams_history", "total_games"]]
    )
    if not mobile.empty:
        fig_mob = px.bar(
            mobile,
            x="player_name",
            y="teams_count",
            color="teams_count",
            color_continuous_scale="Oranges",
            text="teams_count",
            hover_data={"teams_history": True, "current_team": True, "total_games": True},
            labels={
                "player_name": "Joueur",
                "teams_count": "Nombre d'équipes",
                "teams_history": "Parcours",
            },
        )
        fig_mob.update_traces(textposition="outside")
        fig_mob.update_layout(height=380, coloraxis_showscale=False)
        st.plotly_chart(fig_mob, width="stretch")
    else:
        st.info("Tous les joueurs affichés n'ont évolué que dans une seule équipe.")
