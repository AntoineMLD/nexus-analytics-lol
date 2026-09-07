"""Page LFL vs EMEA Masters — comparaison méta inter-compétitions.

Répond au besoin de l'équipe EMEA Masters (via Thomas) :
"elle veut des comparaisons entre la méta LFL et la méta EMEA Masters
pour calibrer sa préparation avant les qualifications".

Et à la demande de Yasmine :
"quels champions émergent en LFL avant d'apparaître en EMEA ?"
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.queries import fetch_meta_by_competition
from dashboard.utils import question_metier

st.set_page_config(page_title="LFL vs EMEA — Nexus Analytics", page_icon="🌍", layout="wide")

st.title("🌍 LFL vs EMEA Masters")
st.caption(
    "Comparaison des métas entre la LFL et l'EMEA Masters "
    "— quels champions émergent en LFL avant d'apparaître en EMEA ?"
)

question_metier(
    "Quels champions émergent en LFL avant d'apparaître en EMEA Masters "
    "— comment calibrer la préparation avant les qualifications EMEA ?",
    "Yasmine Karim — Analyste senior (§Attentes) + Thomas Bourgeois (§Retours clients EMEA)",
)

# ─── Chargement ──────────────────────────────────────────────────────────────

min_picks = st.slider("Picks minimum par compétition", min_value=1, max_value=15, value=3)

with st.spinner("Chargement des données..."):
    df = fetch_meta_by_competition(min_picks=min_picks)

if df.empty:
    st.warning("Aucune donnée disponible.")
    st.stop()

competitions = df["competition"].unique().tolist()

if "EMEA Masters" not in competitions:
    st.info(
        "Aucune donnée EMEA Masters détectée dans la base. "
        "Le pipeline Silver est actuellement filtré sur la LFL uniquement. "
        "Pour activer cette vue, étendre le filtre Silver aux tournois EMEA Masters."
    )
    st.stop()

# ─── Pivot pour comparaison côte à côte ──────────────────────────────────────

lfl = df[df["competition"] == "LFL"][["champion", "picks", "win_rate_pct", "pick_rate_pct"]].rename(
    columns={"picks": "picks_lfl", "win_rate_pct": "wr_lfl", "pick_rate_pct": "pr_lfl"}
)
emea = df[df["competition"] == "EMEA Masters"][
    ["champion", "picks", "win_rate_pct", "pick_rate_pct"]
].rename(columns={"picks": "picks_emea", "win_rate_pct": "wr_emea", "pick_rate_pct": "pr_emea"})

merged = pd.merge(lfl, emea, on="champion", how="outer").fillna(0)
merged["pr_diff"] = round(merged["pr_lfl"] - merged["pr_emea"], 2)
merged["wr_diff"] = round(merged["wr_lfl"] - merged["wr_emea"], 1)

# ─── KPIs ────────────────────────────────────────────────────────────────────

only_lfl = merged[(merged["picks_lfl"] > 0) & (merged["picks_emea"] == 0)]
only_emea = merged[(merged["picks_emea"] > 0) & (merged["picks_lfl"] == 0)]
both = merged[(merged["picks_lfl"] > 0) & (merged["picks_emea"] > 0)]

col1, col2, col3 = st.columns(3)
col1.metric("Champions exclusifs LFL", len(only_lfl))
col2.metric("Champions communs", len(both))
col3.metric("Champions exclusifs EMEA", len(only_emea))

st.markdown("---")

# ─── Scatter : pick rate LFL vs EMEA ─────────────────────────────────────────

st.markdown("### Pick rate LFL vs EMEA Masters")
st.caption(
    "Champions dans le coin haut-gauche = forts en LFL mais absents en EMEA. "
    "Coin bas-droit = spécialités EMEA absentes en LFL."
)

scatter_df = both.copy()
fig = px.scatter(
    scatter_df,
    x="pr_lfl",
    y="pr_emea",
    text="champion",
    size="wr_lfl",
    color="wr_diff",
    color_continuous_scale="RdYlGn",
    color_continuous_midpoint=0,
    labels={
        "pr_lfl": "Pick rate LFL (%)",
        "pr_emea": "Pick rate EMEA (%)",
        "wr_diff": "Écart WR (LFL − EMEA)",
    },
    hover_data={"wr_lfl": True, "wr_emea": True, "picks_lfl": True, "picks_emea": True},
)
fig.update_traces(textposition="top center", marker={"sizemin": 6})
fig.add_hline(y=scatter_df["pr_emea"].mean(), line_dash="dot", line_color="gray", opacity=0.5)
fig.add_vline(x=scatter_df["pr_lfl"].mean(), line_dash="dot", line_color="gray", opacity=0.5)
fig.update_layout(height=500)
st.plotly_chart(fig, width="stretch")

st.markdown("---")

# ─── Champions qui émergent en LFL (fort LFL, faible EMEA) ───────────────────

st.markdown("### 🇫🇷 Émergents LFL — forts en France, peu joués en EMEA")
st.caption(
    "Pick rate LFL > EMEA de plus de 2 points — piste de préparation avant les qualifications."
)

emerging_lfl = both[both["pr_diff"] > 2].sort_values("pr_diff", ascending=False).head(15)
if not emerging_lfl.empty:
    st.dataframe(
        emerging_lfl[["champion", "pr_lfl", "wr_lfl", "pr_emea", "wr_emea", "pr_diff"]].rename(
            columns={
                "champion": "Champion",
                "pr_lfl": "Pick% LFL",
                "wr_lfl": "Win% LFL",
                "pr_emea": "Pick% EMEA",
                "wr_emea": "Win% EMEA",
                "pr_diff": "Écart pick% (LFL−EMEA)",
            }
        ),
        hide_index=True,
        width="stretch",
    )
else:
    st.info("Aucun champion avec un écart supérieur à 2 points.")

st.markdown("---")

# ─── Champions EMEA importés (fort EMEA, faible LFL) ─────────────────────────

st.markdown("### 🌍 Spécialités EMEA — peu joués en LFL, populaires en EMEA")
st.caption("À surveiller pour la préparation des qualifications EMEA Masters.")

emerging_emea = both[both["pr_diff"] < -2].sort_values("pr_diff").head(15)
if not emerging_emea.empty:
    st.dataframe(
        emerging_emea[["champion", "pr_emea", "wr_emea", "pr_lfl", "wr_lfl", "pr_diff"]].rename(
            columns={
                "champion": "Champion",
                "pr_emea": "Pick% EMEA",
                "wr_emea": "Win% EMEA",
                "pr_lfl": "Pick% LFL",
                "wr_lfl": "Win% LFL",
                "pr_diff": "Écart pick% (LFL−EMEA)",
            }
        ),
        hide_index=True,
        width="stretch",
    )
else:
    st.info("Aucun champion avec un écart inverse supérieur à 2 points.")

# ─── Tableau complet ─────────────────────────────────────────────────────────

st.markdown("---")
with st.expander("Tableau complet — tous les champions communs"):
    st.dataframe(
        both[["champion", "pr_lfl", "wr_lfl", "pr_emea", "wr_emea", "pr_diff", "wr_diff"]]
        .rename(
            columns={
                "champion": "Champion",
                "pr_lfl": "Pick% LFL",
                "wr_lfl": "Win% LFL",
                "pr_emea": "Pick% EMEA",
                "wr_emea": "Win% EMEA",
                "pr_diff": "Δ Pick%",
                "wr_diff": "Δ Win%",
            }
        )
        .sort_values("Δ Pick%", ascending=False),
        hide_index=True,
        width="stretch",
    )
