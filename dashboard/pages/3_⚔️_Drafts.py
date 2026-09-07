"""Page Drafts — compositions et stratégies de draft par équipe."""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.queries import (
    fetch_team_compositions,
    fetch_team_draft,
    fetch_team_pick_order,
    fetch_teams,
)
from dashboard.utils import question_metier

st.set_page_config(page_title="Drafts — Nexus Analytics", page_icon="⚔️", layout="wide")

st.title("⚔️ Analyse de draft adverse")
st.caption("Compositions, ordre de pick et bans prioritaires — outil de préparation match")

question_metier(
    "Quelles sont les 5 dernières compositions jouées par notre prochain adversaire cette saison "
    "— quels champions pick-t-il le plus souvent et dans quel ordre ?",
    "Yasmine Karim — Analyste senior (§Besoins fonctionnels)",
)

# ─── Sélecteur d'équipe ───────────────────────────────────────────────────────

with st.spinner("Chargement des équipes..."):
    teams = fetch_teams()

if not teams:
    st.error("Aucune équipe trouvée en base.")
    st.stop()

selected_team = st.selectbox("⚔️ Équipe adverse à analyser", options=teams)

with st.spinner(f"Analyse de {selected_team}..."):
    df_compo = fetch_team_compositions(selected_team, limit=10)
    df_pick_order = fetch_team_pick_order(selected_team)
    df_all = fetch_team_draft(selected_team)

if df_compo.empty:
    st.warning(f"Aucune donnée de draft pour {selected_team}.")
    st.stop()

# ─── KPIs ────────────────────────────────────────────────────────────────────

total_games = len(df_compo)
wins = int(df_compo["team_won"].sum()) if "team_won" in df_compo.columns else 0
win_rate = round(wins * 100 / total_games, 1) if total_games else 0
blue_side = int((df_compo["team_side"] == "Blue").sum()) if "team_side" in df_compo.columns else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Matchs analysés", total_games)
col2.metric("Victoires", wins)
col3.metric("Win rate", f"{win_rate}%")
col4.metric("Matchs côté Bleu", blue_side)

st.markdown("---")

# ─── Section 1 : 5 dernières compositions ────────────────────────────────────

st.markdown("### 🃏 Dernières compositions jouées")
st.caption(
    "Chaque ligne = un match. Les 5 champions sont listés dans l'ordre de draft (pick 1 → pick 5)."
)


def _result_icon(won: bool | None) -> str:
    if won is True:
        return "✅ Victoire"
    if won is False:
        return "❌ Défaite"
    return "—"


compo_display = df_compo.copy()
compo_display["Résultat"] = compo_display["team_won"].apply(_result_icon)
compo_display["Date"] = compo_display["datetime_utc"].astype(str).str[:10]

display_cols = [
    "Date",
    "patch",
    "team_side",
    "Résultat",
    "pick_1",
    "pick_2",
    "pick_3",
    "pick_4",
    "pick_5",
]
display_cols = [c for c in display_cols if c in compo_display.columns]

st.dataframe(
    compo_display[display_cols].rename(
        columns={
            "patch": "Patch",
            "team_side": "Côté",
            "pick_1": "Pick 1",
            "pick_2": "Pick 2",
            "pick_3": "Pick 3",
            "pick_4": "Pick 4",
            "pick_5": "Pick 5",
        }
    ),
    hide_index=True,
    width="stretch",
)

st.markdown("---")

# ─── Section 2 : Champions les plus pickés et ordre habituel ─────────────────

st.markdown("### 🎯 Champions les plus pickés — dans quel ordre ?")
st.caption(
    "Fréquence de pick par champion et par position (1 = premier pick, 5 = dernier). "
    "Révèle les priorités de draft de l'équipe adverse."
)

if not df_pick_order.empty:
    # Agrégation : fréquence totale par champion
    top_picks = (
        df_pick_order.groupby("champion")
        .agg(total_picks=("freq", "sum"), avg_win_rate=("win_rate_pct", "mean"))
        .reset_index()
        .sort_values("total_picks", ascending=False)
        .head(15)
    )

    col_left, col_right = st.columns([3, 2])

    with col_left:
        fig_picks = px.bar(
            top_picks,
            x="total_picks",
            y="champion",
            orientation="h",
            color="avg_win_rate",
            color_continuous_scale="RdYlGn",
            color_continuous_midpoint=50,
            text="total_picks",
            labels={
                "total_picks": "Nombre de picks",
                "champion": "Champion",
                "avg_win_rate": "Win rate moyen (%)",
            },
        )
        fig_picks.update_layout(
            yaxis={"categoryorder": "total ascending"},
            height=420,
            coloraxis_showscale=True,
        )
        st.plotly_chart(fig_picks, width="stretch")

    with col_right:
        st.markdown("#### Position de pick habituelle")
        st.caption("Pour chaque champion, à quelle position il est typiquement sélectionné.")

        # Top 10 champions par fréquence, position médiane
        top10_names = top_picks.head(10)["champion"].tolist()
        order_detail = df_pick_order[df_pick_order["champion"].isin(top10_names)]

        for champ in top10_names:
            rows = order_detail[order_detail["champion"] == champ].sort_values(
                "freq", ascending=False
            )
            if rows.empty:
                continue
            main_pos = int(rows.iloc[0]["pick_position"])
            freq = int(rows.iloc[0]["freq"])
            wr = rows.iloc[0]["win_rate_pct"]
            st.markdown(
                f"**{champ}** — pick {main_pos} habituel "
                f"<span style='color:#888; font-size:0.85em'>({freq}×, {wr}% WR)</span>",
                unsafe_allow_html=True,
            )

    # Heatmap champion × position
    st.markdown("#### Heatmap — Champion × Position de pick")
    st.caption("Intensité = nombre de picks dans cette position.")

    top15_names = top_picks["champion"].tolist()
    heatmap_df = df_pick_order[df_pick_order["champion"].isin(top15_names)].pivot_table(
        index="champion", columns="pick_position", values="freq", fill_value=0
    )
    # Ordonner par fréquence totale
    heatmap_df = heatmap_df.loc[top15_names[::-1]]

    fig_heat = go.Figure(
        go.Heatmap(
            z=heatmap_df.values,
            x=[f"Pick {c}" for c in heatmap_df.columns],
            y=heatmap_df.index.tolist(),
            colorscale="Blues",
            text=heatmap_df.values,
            texttemplate="%{text}",
            showscale=False,
        )
    )
    fig_heat.update_layout(height=420)
    st.plotly_chart(fig_heat, width="stretch")

st.markdown("---")

# ─── Section 3 : Bans prioritaires ───────────────────────────────────────────

st.markdown("### 🚫 Bans prioritaires")
st.caption(
    "Champions que l'équipe adverse interdit en priorité — signale ses peurs et ses axes stratégiques."
)

df_bans = df_all[df_all["action_type"] == "ban"] if "action_type" in df_all.columns else df_all

if not df_bans.empty:
    top_bans = (
        df_bans.groupby("champion")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(15)
    )
    fig_bans = px.bar(
        top_bans,
        x="count",
        y="champion",
        orientation="h",
        color="count",
        color_continuous_scale="Reds",
        text="count",
        labels={"count": "Nombre de bans", "champion": "Champion"},
    )
    fig_bans.update_layout(
        yaxis={"categoryorder": "total ascending"},
        height=380,
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_bans, width="stretch")
