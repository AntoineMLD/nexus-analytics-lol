"""Page Drafts — historique de draft par équipe."""

import plotly.express as px
import streamlit as st

from dashboard.queries import fetch_team_draft, fetch_teams

st.set_page_config(page_title="Drafts — Nexus Analytics", page_icon="⚔️", layout="wide")

st.title("⚔️ Historique de draft")
st.caption("Picks et bans par équipe — toutes saisons LFL")

# ─── Filtres ────────────────────────────────────────────────────────────────

with st.spinner("Chargement des équipes..."):
    teams = fetch_teams()

if not teams:
    st.error("Aucune équipe trouvée en base.")
    st.stop()

col_f1, col_f2 = st.columns([3, 2])
with col_f1:
    selected_team = st.selectbox("Équipe", options=teams)
with col_f2:
    action_type = st.radio(
        "Type d'action",
        options=["Tous", "pick", "ban"],
        horizontal=True,
    )

action_filter = None if action_type == "Tous" else action_type

with st.spinner(f"Chargement des drafts de {selected_team}..."):
    df = fetch_team_draft(team=selected_team, action_type=action_filter)

if df.empty:
    st.warning(f"Aucune donnée de draft pour {selected_team}.")
    st.stop()

# ─── KPIs équipe ─────────────────────────────────────────────────────────────

total_picks = len(df[df["action_type"] == "pick"]) if "action_type" in df.columns else 0
total_bans = len(df[df["action_type"] == "ban"]) if "action_type" in df.columns else 0
win_rate = (
    round(df["team_won"].mean() * 100, 1)
    if "team_won" in df.columns and not df["team_won"].isna().all()
    else None
)

col1, col2, col3 = st.columns(3)
col1.metric("Picks totaux", total_picks)
col2.metric("Bans totaux", total_bans)
if win_rate is not None:
    col3.metric("Win rate (parties draftées)", f"{win_rate}%")

# ─── Top champions draftés ────────────────────────────────────────────────────

st.markdown(f"### Champions les plus draftés par {selected_team}")

top_champs = (
    df.groupby("champion")
    .size()
    .reset_index(name="count")
    .sort_values("count", ascending=False)
    .head(15)
)

fig = px.bar(
    top_champs,
    x="count",
    y="champion",
    orientation="h",
    color="count",
    color_continuous_scale="Blues",
    labels={"count": "Nombre de drafts", "champion": "Champion"},
    text="count",
)
fig.update_layout(
    yaxis={"categoryorder": "total ascending"},
    height=450,
    coloraxis_showscale=False,
)
st.plotly_chart(fig, use_container_width=True)

# ─── Tableau historique ───────────────────────────────────────────────────────

st.markdown("### Historique détaillé")

display_cols = ["datetime_utc", "patch", "action_type", "champion", "action_order", "team_side"]
display_cols = [c for c in display_cols if c in df.columns]

st.dataframe(
    df[display_cols].rename(
        columns={
            "datetime_utc": "Date",
            "patch": "Patch",
            "action_type": "Action",
            "champion": "Champion",
            "action_order": "Ordre",
            "team_side": "Côté",
        }
    ),
    use_container_width=True,
    hide_index=True,
)
