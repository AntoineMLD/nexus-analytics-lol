"""Page Équipes — performances LFL par équipe et par saison."""

import plotly.express as px
import streamlit as st

from dashboard.utils import question_metier

st.set_page_config(page_title="Équipes — Nexus Analytics", page_icon="🛡️", layout="wide")

st.title("🛡️ Équipes LFL")
st.caption("Performances par équipe — win rate, gold diff, durée moyenne des parties")

question_metier(
    "Quelles sont les performances historiques de chaque équipe LFL cette saison "
    "— win rate, avantage gold moyen, durée des matchs ?",
    "Thomas Bourgeois — Chargé clients (§Retours clients)",
)


@st.cache_data(ttl=600, show_spinner=False)
def fetch_team_stats(season_filter: str | None = None):
    import os

    from google.cloud import bigquery

    project = os.environ.get("GCP_PROJECT_ID", "")
    client = bigquery.Client(project=project, location="europe-west1")

    where = f"AND STARTS_WITH(overview_page, '{season_filter}')" if season_filter else ""

    sql = f"""
        SELECT
            win_team                                        AS team,
            overview_page,
            COUNT(*)                                        AS wins,
            ROUND(AVG(gamelength_seconds) / 60.0, 1)       AS avg_game_min,
            ROUND(AVG(CASE WHEN win_team = team1
                          THEN team1_gold - team2_gold
                          ELSE team2_gold - team1_gold END))
                                                            AS avg_gold_diff
        FROM `{project}.gold_staging.stg_lfl_matches`
        WHERE win_team IS NOT NULL
        {where}
        GROUP BY win_team, overview_page
    """

    wins_df = client.query(sql).to_dataframe()

    sql2 = f"""
        SELECT
            team1 AS team, overview_page, COUNT(*) AS games_played
        FROM `{project}.gold_staging.stg_lfl_matches`
        WHERE 1=1 {where}
        GROUP BY team1, overview_page
        UNION ALL
        SELECT
            team2 AS team, overview_page, COUNT(*) AS games_played
        FROM `{project}.gold_staging.stg_lfl_matches`
        WHERE 1=1 {where}
        GROUP BY team2, overview_page
    """
    games_df = client.query(sql2).to_dataframe()
    games_agg = games_df.groupby("team", as_index=False)["games_played"].sum()
    wins_agg = wins_df.groupby("team", as_index=False).agg(
        wins=("wins", "sum"),
        avg_game_min=("avg_game_min", "mean"),
        avg_gold_diff=("avg_gold_diff", "mean"),
    )

    df = games_agg.merge(wins_agg, on="team", how="left").fillna(0)
    df["win_rate_pct"] = (df["wins"] / df["games_played"] * 100).round(1)
    df["avg_game_min"] = df["avg_game_min"].round(1)
    df["avg_gold_diff"] = df["avg_gold_diff"].round(0).astype(int)
    return df.sort_values("win_rate_pct", ascending=False)


@st.cache_data(ttl=600, show_spinner=False)
def fetch_seasons() -> list[str]:
    import os

    from google.cloud import bigquery

    project = os.environ.get("GCP_PROJECT_ID", "")
    client = bigquery.Client(project=project, location="europe-west1")
    sql = f"""
        SELECT DISTINCT REGEXP_EXTRACT(overview_page, r'^[^/]+/[^/]+') AS season
        FROM `{project}.gold_staging.stg_lfl_matches`
        WHERE overview_page IS NOT NULL
        ORDER BY season DESC
        LIMIT 30
    """
    rows = client.query(sql).to_dataframe()
    return [r for r in rows["season"].tolist() if r]


# ─── Filtres ────────────────────────────────────────────────────────────────

with st.spinner("Chargement des saisons..."):
    seasons = fetch_seasons()

col_f1, _ = st.columns([3, 2])
with col_f1:
    selected_season = st.selectbox(
        "Saison / Tournoi",
        options=["Toutes les saisons"] + seasons,
    )

season_filter = None if selected_season == "Toutes les saisons" else selected_season

with st.spinner("Chargement des stats équipes..."):
    df = fetch_team_stats(season_filter=season_filter)

if df.empty:
    st.warning("Aucune donnée pour cette sélection.")
    st.stop()

# ─── KPIs ────────────────────────────────────────────────────────────────────

best_team = df.iloc[0]
col1, col2, col3 = st.columns(3)
col1.metric("Meilleure équipe", best_team["team"], f"{best_team['win_rate_pct']}% win rate")
col2.metric("Équipes présentes", len(df))
col3.metric("Durée moy. partie", f"{df['avg_game_min'].mean():.1f} min")

# ─── Classement win rate ──────────────────────────────────────────────────────

st.markdown("### Classement par win rate")

fig = px.bar(
    df,
    x="win_rate_pct",
    y="team",
    orientation="h",
    color="win_rate_pct",
    color_continuous_scale="RdYlGn",
    text="win_rate_pct",
    labels={"win_rate_pct": "Win rate (%)", "team": "Équipe"},
    hover_data={"wins": True, "games_played": True},
)
fig.add_vline(x=50, line_dash="dash", line_color="gray", opacity=0.5)
fig.update_layout(
    yaxis={"categoryorder": "total ascending"},
    height=max(300, len(df) * 30),
    coloraxis_showscale=False,
)
fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
st.plotly_chart(fig, width="stretch")

# ─── Gold diff vs Win rate ────────────────────────────────────────────────────

col_a, col_b = st.columns(2)

with col_a:
    st.markdown("### Gold diff moyen")
    st.caption("Or moyen gagné/perdu par partie (positif = dominant)")

    fig2 = px.bar(
        df.sort_values("avg_gold_diff", ascending=False),
        x="avg_gold_diff",
        y="team",
        orientation="h",
        color="avg_gold_diff",
        color_continuous_scale="RdYlGn",
        labels={"avg_gold_diff": "Gold diff moyen", "team": "Équipe"},
        text="avg_gold_diff",
    )
    fig2.add_vline(x=0, line_color="gray", opacity=0.5)
    fig2.update_layout(
        yaxis={"categoryorder": "total ascending"},
        height=max(300, len(df) * 30),
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig2, width="stretch")

with col_b:
    st.markdown("### Durée moyenne des parties (min)")

    fig3 = px.bar(
        df.sort_values("avg_game_min"),
        x="avg_game_min",
        y="team",
        orientation="h",
        color="avg_game_min",
        color_continuous_scale="Blues_r",
        labels={"avg_game_min": "Durée moy. (min)", "team": "Équipe"},
        text="avg_game_min",
    )
    fig3.update_layout(
        yaxis={"categoryorder": "total ascending"},
        height=max(300, len(df) * 30),
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig3, width="stretch")

# ─── Tableau ─────────────────────────────────────────────────────────────────

with st.expander("Tableau complet"):
    st.dataframe(
        df.rename(
            columns={
                "team": "Équipe",
                "games_played": "Parties",
                "wins": "Victoires",
                "win_rate_pct": "Win %",
                "avg_game_min": "Durée moy. (min)",
                "avg_gold_diff": "Gold diff moy.",
            }
        ),
        hide_index=True,
        width="stretch",
    )
