"""Page Profil Joueur — pool de champions, stats détaillées, équipes jouées."""

import plotly.express as px
import streamlit as st

from dashboard.queries import (
    fetch_player_champion_pool,
    fetch_player_names,
    fetch_player_stats_by_name,
)

st.set_page_config(page_title="Profil Joueur — Nexus Analytics", page_icon="🔍", layout="wide")

st.title("🔍 Profil joueur")
st.caption("Pool de champions, statistiques de carrière et équipes jouées")

# ─── Sélecteur joueur ────────────────────────────────────────────────────────

with st.spinner("Chargement des joueurs..."):
    player_names = fetch_player_names()

if not player_names:
    st.error("Aucun joueur trouvé en base.")
    st.stop()

selected_player = st.selectbox("Joueur", options=player_names)

with st.spinner(f"Chargement du profil de {selected_player}..."):
    stats = fetch_player_stats_by_name(selected_player)
    pool = fetch_player_champion_pool(selected_player)

if not stats:
    st.warning(f"Aucune donnée agrégée pour {selected_player}.")
    st.stop()

# ─── KPIs joueur ─────────────────────────────────────────────────────────────

kda = round((stats["avg_kills"] + stats["avg_assists"]) / max(stats["avg_deaths"], 1), 2)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Parties jouées", int(stats["total_games"]))
col2.metric("Win rate", f"{stats['win_rate_pct']}%")
col3.metric("KDA moyen", kda)
col4.metric(
    "Kills / Deaths / Assists",
    f"{stats['avg_kills']:.1f}/{stats['avg_deaths']:.1f}/{stats['avg_assists']:.1f}",
)
col5.metric("CS moyen", f"{stats['avg_cs']:.0f}")

st.markdown("---")

# ─── Pool de champions ───────────────────────────────────────────────────────

if pool.empty:
    st.info("Aucun détail de champion disponible.")
    st.stop()

col_a, col_b = st.columns([3, 2])

with col_a:
    st.markdown("### Pool de champions")

    fig = px.bar(
        pool.head(15),
        x="games",
        y="champion",
        orientation="h",
        color="win_rate_pct",
        color_continuous_scale="RdYlGn",
        text="games",
        labels={
            "games": "Parties jouées",
            "champion": "Champion",
            "win_rate_pct": "Win rate (%)",
        },
        hover_data={
            "win_rate_pct": True,
            "avg_kills": True,
            "avg_deaths": True,
            "avg_assists": True,
        },
    )
    fig.update_layout(
        yaxis={"categoryorder": "total ascending"},
        height=450,
        coloraxis_showscale=True,
    )
    st.plotly_chart(fig, width="stretch")

with col_b:
    st.markdown("### Répartition par rôle")

    if "role" in pool.columns and not pool["role"].isna().all():
        role_counts = pool.groupby("role")["games"].sum().reset_index()
        fig2 = px.pie(
            role_counts,
            values="games",
            names="role",
            color_discrete_sequence=px.colors.qualitative.Set2,
            hole=0.4,
        )
        fig2.update_layout(height=300)
        st.plotly_chart(fig2, width="stretch")

    st.markdown("#### Top 5 par win rate")
    st.dataframe(
        pool.nlargest(5, "win_rate_pct")[["champion", "games", "win_rate_pct"]].rename(
            columns={"champion": "Champion", "games": "Parties", "win_rate_pct": "Win %"}
        ),
        hide_index=True,
        width="stretch",
    )

# ─── Tableau pool complet ─────────────────────────────────────────────────────

with st.expander("Pool complet"):
    st.dataframe(
        pool.rename(
            columns={
                "champion": "Champion",
                "games": "Parties",
                "win_rate_pct": "Win %",
                "role": "Rôle",
                "avg_kills": "K",
                "avg_deaths": "D",
                "avg_assists": "A",
            }
        ),
        hide_index=True,
        width="stretch",
    )
