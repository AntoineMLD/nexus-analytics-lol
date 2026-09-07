"""Page Profil Joueur — pool de champions, stats détaillées, équipes jouées."""

import plotly.express as px
import streamlit as st

from dashboard.queries import (
    fetch_player_champion_pool,
    fetch_player_names,
    fetch_player_oe_gold_diff_trend,
    fetch_player_oe_stats,
    fetch_player_stats_by_name,
)
from dashboard.utils import question_metier

st.set_page_config(page_title="Profil Joueur — Nexus Analytics", page_icon="🔍", layout="wide")

st.title("🔍 Profil joueur")
st.caption("Pool de champions, statistiques de carrière et équipes jouées")

question_metier(
    "Quel est le profil champion d'un joueur adverse "
    "— quels sont ses picks de prédilection, son rôle principal et ses statistiques clés ?",
    "Thomas Bourgeois — Chargé clients (§Besoins non exprimés)",
)

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
    oe_stats = fetch_player_oe_stats(selected_player)
    oe_trend = fetch_player_oe_gold_diff_trend(selected_player)

if not stats:
    st.warning(f"Aucune donnée agrégée pour {selected_player}.")
    st.stop()

# ─── Équipe actuelle ─────────────────────────────────────────────────────────

current_team = stats.get("current_team") or "—"
teams_history = stats.get("teams_history") or ""

team_badge = (
    f"<span style='background:#1f77b4; color:white; padding:4px 14px; "
    f"border-radius:20px; font-weight:600; font-size:1em'>{current_team}</span>"
)
st.markdown(f"**Équipe actuelle :** {team_badge}", unsafe_allow_html=True)

if teams_history and " · " in teams_history:
    st.caption(f"Équipes jouées : {teams_history}")

st.markdown("---")

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

# ─── Métriques avancées Oracle's Elixir ──────────────────────────────────────

st.markdown("---")
st.markdown("### Métriques avancées — Oracle's Elixir")
st.caption(
    "Source : Oracle's Elixir CSV — données non disponibles dans Leaguepedia (CS/min, DPM, gold diff à 15 min)"
)

if oe_stats is None:
    st.info(
        "Données Oracle's Elixir non disponibles pour ce joueur. "
        "Le pipeline Oracle's Elixir doit être exécuté (`uv run python -m pipeline.silver_transforms.oracle_elixir --all-years`)."
    )
else:
    games_note = ""
    if oe_stats["games_with_diff_metrics"] < oe_stats["games_oe"]:
        games_note = (
            f" (diff. à 15 min disponible sur {oe_stats['games_with_diff_metrics']}/"
            f"{oe_stats['games_oe']} parties — données partielles avant 2021)"
        )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Parties OE",
        int(oe_stats["games_oe"]),
        help="Nombre de parties avec données Oracle's Elixir",
    )
    col2.metric(
        "CS / min",
        f"{oe_stats['avg_cs_per_min']:.2f}" if oe_stats["avg_cs_per_min"] else "—",
        help="CS par minute en moyenne sur toutes les parties OE",
    )
    col3.metric(
        "DPM",
        f"{int(oe_stats['avg_dpm'])}" if oe_stats["avg_dpm"] else "—",
        help="Dégâts par minute en moyenne",
    )
    col4.metric(
        "Gold diff. à 15 min",
        f"{int(oe_stats['avg_gold_diff_15']):+d}" if oe_stats["avg_gold_diff_15"] else "—",
        help="Différentiel d'or à 15 min vs adversaire même rôle (positif = avance)" + games_note,
        delta=int(oe_stats["avg_gold_diff_15"]) if oe_stats["avg_gold_diff_15"] else None,
        delta_color="normal",
    )

    if not oe_trend.empty and len(oe_trend) > 1:
        st.markdown("#### Évolution du gold diff à 15 min par saison")
        fig_trend = px.bar(
            oe_trend,
            x="season",
            y="avg_gold_diff_15",
            text="avg_gold_diff_15",
            color="avg_gold_diff_15",
            color_continuous_scale="RdYlGn",
            labels={
                "season": "Saison",
                "avg_gold_diff_15": "Gold diff. moyen à 15 min",
            },
        )
        fig_trend.add_hline(y=0, line_dash="dash", line_color="gray")
        fig_trend.update_traces(texttemplate="%{text:+,.0f}")
        fig_trend.update_layout(
            height=300,
            coloraxis_showscale=False,
            xaxis_title=None,
        )
        st.plotly_chart(fig_trend, width="stretch")

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
