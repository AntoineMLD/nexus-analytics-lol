"""Page Alerte Méta — champions avec winrate anormal sur les 2 derniers patches.

Répond au besoin exprimé par Thomas (chargé clients) :
"une section alerte méta si un champion a un winrate anormal sur les 2 derniers patches".
"""

import plotly.express as px
import streamlit as st

from dashboard.queries import fetch_meta_alerts
from dashboard.utils import question_metier

st.set_page_config(page_title="Alerte Méta — Nexus Analytics", page_icon="🚨", layout="wide")

st.title("🚨 Alerte Méta")
st.caption(
    "Champions avec un winrate anormalement haut ou bas sur les 2 derniers patches "
    "— signal d'alerte pour la préparation de matchs."
)

question_metier(
    "Quel champion a un win rate anormalement haut ou bas sur les 2 derniers patches "
    "— y a-t-il des picks à prioriser ou à éviter absolument en draft cette semaine ?",
    "Thomas Bourgeois — Chargé clients (§Vision)",
)

# ─── Paramètres ──────────────────────────────────────────────────────────────

min_picks = st.slider("Picks minimum (fiabilité)", min_value=3, max_value=20, value=5, step=1)

with st.spinner("Analyse de la méta en cours..."):
    df = fetch_meta_alerts(min_picks=min_picks)

if df.empty:
    st.warning("Aucune donnée disponible. Vérifiez que fact_meta_trend est peuplée.")
    st.stop()

patches = sorted(df["patch"].dropna().unique(), reverse=True)
avg_wr = df.groupby("patch")["avg_wr_patch"].first().to_dict()

# ─── KPIs globaux ────────────────────────────────────────────────────────────

st.markdown(f"**Patches analysés :** {' · '.join(patches)}")

threshold = 7.0  # déviation en points de % pour déclencher une alerte

over = df[df["deviation"] >= threshold]
under = df[df["deviation"] <= -threshold]

col1, col2, col3 = st.columns(3)
col1.metric("Patches couverts", len(patches))
col2.metric("⬆️ Surperformants", len(over), help=f"Winrate ≥ moyenne + {threshold}%")
col3.metric("⬇️ Sous-performants", len(under), help=f"Winrate ≤ moyenne − {threshold}%")

st.markdown("---")

# ─── Surperformants ──────────────────────────────────────────────────────────

st.markdown("### ⬆️ Champions surperformants")
st.caption(
    f"Winrate supérieur de +{threshold} points à la moyenne du patch — à surveiller en pick/ban."
)

if over.empty:
    st.info("Aucun champion ne dépasse le seuil sur ces patches.")
else:
    fig_over = px.bar(
        over.sort_values("deviation", ascending=False),
        x="champion",
        y="deviation",
        color="win_rate_pct",
        color_continuous_scale="Greens",
        text="win_rate_pct",
        hover_data={"picks": True, "patch": True, "avg_wr_patch": True},
        labels={
            "champion": "Champion",
            "deviation": "Écart vs moyenne patch (%)",
            "win_rate_pct": "Win rate (%)",
        },
    )
    fig_over.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig_over.update_layout(height=350, coloraxis_showscale=False, showlegend=False)
    st.plotly_chart(fig_over, width="stretch")

# ─── Sous-performants ────────────────────────────────────────────────────────

st.markdown("### ⬇️ Champions sous-performants")
st.caption(
    f"Winrate inférieur de {threshold} points à la moyenne — champions à éviter ou à exploiter."
)

if under.empty:
    st.info("Aucun champion ne descend sous le seuil sur ces patches.")
else:
    under_sorted = under.sort_values("deviation")
    fig_under = px.bar(
        under_sorted,
        x="champion",
        y="deviation",
        color="win_rate_pct",
        color_continuous_scale="Reds_r",
        text="win_rate_pct",
        hover_data={"picks": True, "patch": True, "avg_wr_patch": True},
        labels={
            "champion": "Champion",
            "deviation": "Écart vs moyenne patch (%)",
            "win_rate_pct": "Win rate (%)",
        },
    )
    fig_under.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig_under.update_layout(height=350, coloraxis_showscale=False, showlegend=False)
    st.plotly_chart(fig_under, width="stretch")

# ─── Tableau complet ─────────────────────────────────────────────────────────

st.markdown("---")
with st.expander("Tableau complet — tous les champions analysés"):
    st.dataframe(
        df.rename(
            columns={
                "patch": "Patch",
                "champion": "Champion",
                "picks": "Picks",
                "win_rate_pct": "Win rate (%)",
                "pick_rate_pct": "Pick rate (%)",
                "avg_wr_patch": "Moy. patch (%)",
                "deviation": "Écart (%)",
            }
        ).sort_values("Écart (%)", ascending=False),
        hide_index=True,
        width="stretch",
        column_config={
            "Win rate (%)": st.column_config.ProgressColumn(
                "Win rate (%)", min_value=0, max_value=100, format="%.1f%%"
            ),
            "Écart (%)": st.column_config.NumberColumn(format="%.1f"),
        },
    )
