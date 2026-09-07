"""Page Champions — pick rates, win rates et distribution par rôle."""

import plotly.express as px
import streamlit as st

from dashboard.queries import fetch_champions, fetch_seasons

st.set_page_config(page_title="Champions — Nexus Analytics", page_icon="🐉", layout="wide")

st.title("🐉 Champions LFL")
st.caption("Pick rates, win rates et distribution par rôle — toutes saisons")

# ─── Filtres ────────────────────────────────────────────────────────────────

with st.spinner("Chargement des saisons..."):
    seasons = fetch_seasons()

col_f0, col_f1, col_f2 = st.columns([3, 2, 2])
with col_f0:
    selected_season = st.selectbox("Saison", options=["Toutes les saisons"] + seasons)
with col_f1:
    min_games = st.slider("Parties minimum", min_value=1, max_value=50, value=5, step=1)
with col_f2:
    role_filter = st.selectbox(
        "Rôle principal",
        options=["Tous", "Top", "Jungle", "Mid", "Bot", "Support"],
    )

season_filter = None if selected_season == "Toutes les saisons" else selected_season

with st.spinner("Chargement..."):
    df = fetch_champions(min_games=min_games, season=season_filter)

if df.empty:
    st.warning("Aucun champion trouvé.")
    st.stop()

# Filtre rôle : rôle principal = rôle avec le plus de picks
if role_filter != "Tous":
    role_col = f"picks_{role_filter.lower()}"
    if role_col in df.columns:
        df["main_role"] = (
            df[["picks_top", "picks_jungle", "picks_mid", "picks_bot", "picks_support"]]
            .idxmax(axis=1)
            .str.replace("picks_", "")
            .str.capitalize()
        )
        df = df[df["main_role"] == role_filter]

if df.empty:
    st.warning(f"Aucun champion trouvé pour le rôle {role_filter}.")
    st.stop()

# ─── Scatter : pick rate vs win rate ────────────────────────────────────────

st.markdown("### Pick rate vs Win rate")
st.caption("Chaque point = un champion. Taille = nombre de parties jouées.")

fig = px.scatter(
    df,
    x="pick_rate_pct",
    y="win_rate_pct",
    size="total_games_played",
    text="champion",
    color="win_rate_pct",
    color_continuous_scale="RdYlGn",
    labels={
        "pick_rate_pct": "Pick rate (%)",
        "win_rate_pct": "Win rate (%)",
        "total_games_played": "Parties",
    },
    hover_data={"champion": True, "total_games_played": True},
)
fig.add_hline(y=50, line_dash="dash", line_color="gray", opacity=0.5)
fig.update_traces(textposition="top center", textfont_size=9)
fig.update_layout(height=500, coloraxis_showscale=False)
st.plotly_chart(fig, width="stretch")

# ─── Top 15 champions (barres) ───────────────────────────────────────────────

st.markdown("### Top 15 champions par nombre de parties")

top15 = df.head(15)
fig2 = px.bar(
    top15,
    x="total_games_played",
    y="champion",
    orientation="h",
    color="win_rate_pct",
    color_continuous_scale="RdYlGn",
    labels={
        "total_games_played": "Parties jouées",
        "champion": "Champion",
        "win_rate_pct": "Win rate (%)",
    },
    text="total_games_played",
)
fig2.update_layout(yaxis={"categoryorder": "total ascending"}, height=450, coloraxis_showscale=True)
st.plotly_chart(fig2, width="stretch")

# ─── Tableau ─────────────────────────────────────────────────────────────────

with st.expander("Tableau détaillé"):
    st.dataframe(
        df[
            [
                "champion",
                "total_games_played",
                "pick_rate_pct",
                "win_rate_pct",
                "avg_kills",
                "avg_deaths",
                "avg_assists",
            ]
        ].rename(
            columns={
                "champion": "Champion",
                "total_games_played": "Parties",
                "pick_rate_pct": "Pick %",
                "win_rate_pct": "Win %",
                "avg_kills": "K",
                "avg_deaths": "D",
                "avg_assists": "A",
            }
        ),
        width="stretch",
        hide_index=True,
    )
