"""Page Méta — tendances par patch (pick rate vs win rate)."""

import plotly.express as px
import streamlit as st

from dashboard.queries import fetch_meta_by_patch, fetch_patches

st.set_page_config(page_title="Méta — Nexus Analytics", page_icon="📈", layout="wide")

st.title("📈 Tendances méta")
st.caption("Pick rate et win rate par champion et par patch LFL")

# ─── Sélecteur de patch ─────────────────────────────────────────────────────

with st.spinner("Chargement des patches..."):
    patches = fetch_patches()

if not patches:
    st.error("Aucun patch trouvé en base.")
    st.stop()

col_f1, col_f2 = st.columns([2, 3])
with col_f1:
    selected_patch = st.selectbox(
        "Patch",
        options=["Tous les patches"] + patches,
    )

patch_filter = None if selected_patch == "Tous les patches" else selected_patch

with st.spinner("Chargement des tendances méta..."):
    df = fetch_meta_by_patch(patch=patch_filter)

if df.empty:
    st.warning("Aucune donnée méta pour cette sélection.")
    st.stop()

# Quand plusieurs patches sont présents, on agrège par champion
# pour éviter plusieurs barres/points par champion dans les graphiques.
if patch_filter is None and "patch" in df.columns:
    total_picks_all = df["picks"].sum()
    df = df.groupby("champion", as_index=False).agg(picks=("picks", "sum"), wins=("wins", "sum"))
    df["pick_rate_pct"] = (df["picks"] / total_picks_all * 100).round(2)
    df["win_rate_pct"] = (df["wins"] / df["picks"] * 100).round(1)

with col_f2:
    min_picks = st.slider(
        "Picks minimum (filtre les champions rares)",
        min_value=1,
        max_value=int(df["picks"].max()) if not df.empty else 20,
        value=max(1, int(df["picks"].quantile(0.25))),
    )

df = df[df["picks"] >= min_picks]

if df.empty:
    st.warning("Aucun champion avec ce nombre de picks minimum.")
    st.stop()

# ─── Scatter : pick rate vs win rate ────────────────────────────────────────

st.markdown("### Pick rate vs Win rate")
st.caption("Quadrant haut-droite = champions dominants (souvent picked ET gagnants).")

fig = px.scatter(
    df,
    x="pick_rate_pct",
    y="win_rate_pct",
    size="picks",
    text="champion",
    color="win_rate_pct",
    color_continuous_scale="RdYlGn",
    hover_data={"champion": True, "picks": True, "wins": True},
    labels={
        "pick_rate_pct": "Pick rate (%)",
        "win_rate_pct": "Win rate (%)",
        "picks": "Picks",
    },
)

avg_pick = df["pick_rate_pct"].mean()
avg_win = df["win_rate_pct"].mean()

fig.add_hline(
    y=avg_win,
    line_dash="dash",
    line_color="gray",
    opacity=0.4,
    annotation_text=f"Win rate moy. {avg_win:.1f}%",
)
fig.add_vline(
    x=avg_pick,
    line_dash="dash",
    line_color="gray",
    opacity=0.4,
    annotation_text=f"Pick rate moy. {avg_pick:.1f}%",
)

fig.update_traces(textposition="top center", textfont_size=9)
fig.update_layout(height=550, coloraxis_showscale=False)
st.plotly_chart(fig, width="stretch")

# ─── Top 10 champions du patch ───────────────────────────────────────────────

col_a, col_b = st.columns(2)

with col_a:
    st.markdown("#### Top 10 — Pick rate")
    top_pick = df.nlargest(10, "pick_rate_pct")[["champion", "pick_rate_pct", "picks"]]
    fig2 = px.bar(
        top_pick,
        x="pick_rate_pct",
        y="champion",
        orientation="h",
        color="pick_rate_pct",
        color_continuous_scale="Blues",
        labels={"pick_rate_pct": "Pick rate (%)", "champion": ""},
        text_auto=".1f",
    )
    fig2.update_layout(
        yaxis={"categoryorder": "total ascending"}, height=350, coloraxis_showscale=False
    )
    st.plotly_chart(fig2, width="stretch")

with col_b:
    st.markdown("#### Top 10 — Win rate (≥ pick moyen)")
    top_win = df[df["pick_rate_pct"] >= avg_pick].nlargest(10, "win_rate_pct")[
        ["champion", "win_rate_pct", "picks"]
    ]
    fig3 = px.bar(
        top_win,
        x="win_rate_pct",
        y="champion",
        orientation="h",
        color="win_rate_pct",
        color_continuous_scale="RdYlGn",
        labels={"win_rate_pct": "Win rate (%)", "champion": ""},
        text_auto=".1f",
    )
    fig3.update_layout(
        yaxis={"categoryorder": "total ascending"}, height=350, coloraxis_showscale=False
    )
    st.plotly_chart(fig3, width="stretch")

# ─── Tableau ─────────────────────────────────────────────────────────────────

with st.expander("Données brutes"):
    st.dataframe(
        df[["champion", "patch", "picks", "wins", "pick_rate_pct", "win_rate_pct"]].rename(
            columns={
                "champion": "Champion",
                "patch": "Patch",
                "picks": "Picks",
                "wins": "Victoires",
                "pick_rate_pct": "Pick %",
                "win_rate_pct": "Win %",
            }
        ),
        width="stretch",
        hide_index=True,
    )
