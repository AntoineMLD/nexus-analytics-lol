"""Page Comparaison — deux joueurs LFL côte à côte."""

import plotly.graph_objects as go
import streamlit as st

from dashboard.queries import (
    fetch_player_champion_pool,
    fetch_player_names,
    fetch_player_stats_by_name,
)

st.set_page_config(page_title="Comparaison — Nexus Analytics", page_icon="⚖️", layout="wide")

st.title("⚖️ Comparaison de joueurs")
st.caption("Mettez deux joueurs côte à côte pour comparer leurs statistiques de carrière")

# ─── Sélection des deux joueurs ──────────────────────────────────────────────

with st.spinner("Chargement des joueurs..."):
    player_names = fetch_player_names()

if not player_names:
    st.error("Aucun joueur trouvé en base.")
    st.stop()

col_left, col_right = st.columns(2)
with col_left:
    player_a = st.selectbox("Joueur A", options=player_names, index=0)
with col_right:
    player_b = st.selectbox("Joueur B", options=player_names, index=min(1, len(player_names) - 1))

if player_a == player_b:
    st.warning("Sélectionnez deux joueurs différents.")
    st.stop()

with st.spinner("Chargement des profils..."):
    stats_a = fetch_player_stats_by_name(player_a)
    stats_b = fetch_player_stats_by_name(player_b)
    pool_a = fetch_player_champion_pool(player_a)
    pool_b = fetch_player_champion_pool(player_b)

if not stats_a or not stats_b:
    st.error("Données manquantes pour l'un des joueurs.")
    st.stop()

# ─── KPIs côte à côte ────────────────────────────────────────────────────────


def kda(s: dict) -> float:
    return round((s["avg_kills"] + s["avg_assists"]) / max(s["avg_deaths"], 1), 2)


st.markdown("---")
st.markdown("### Statistiques de carrière")

metrics = [
    ("Parties jouées", "total_games", lambda s: int(s["total_games"]), None),
    ("Win rate (%)", "win_rate_pct", lambda s: s["win_rate_pct"], None),
    ("KDA", "kda", kda, None),
    ("Kills moy.", "avg_kills", lambda s: round(s["avg_kills"], 2), None),
    ("Deaths moy.", "avg_deaths", lambda s: round(s["avg_deaths"], 2), None),
    ("Assists moy.", "avg_assists", lambda s: round(s["avg_assists"], 2), None),
    ("CS moyen", "avg_cs", lambda s: round(s["avg_cs"], 0), None),
]

col_l, col_m, col_r = st.columns([2, 1, 2])
with col_m:
    st.markdown("<br>", unsafe_allow_html=True)
    for label, _, _, _ in metrics:
        st.markdown(
            f"<p style='text-align:center; font-weight:bold; margin:18px 0'>{label}</p>",
            unsafe_allow_html=True,
        )

with col_l:
    st.markdown(
        f"<h3 style='text-align:center; color:#1f77b4'>{player_a}</h3>", unsafe_allow_html=True
    )
    for _label, _, fn, _ in metrics:
        val_a = fn(stats_a)
        val_b = fn(stats_b)
        delta = round(val_a - val_b, 2) if isinstance(val_a, int | float) else None
        st.metric(label="", value=val_a, delta=delta, label_visibility="collapsed")

with col_r:
    st.markdown(
        f"<h3 style='text-align:center; color:#ff7f0e'>{player_b}</h3>", unsafe_allow_html=True
    )
    for _label, _, fn, _ in metrics:
        val_a = fn(stats_a)
        val_b = fn(stats_b)
        delta = round(val_b - val_a, 2) if isinstance(val_a, int | float) else None
        st.metric(label="", value=val_b, delta=delta, label_visibility="collapsed")

# ─── Radar chart ─────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("### Profil radar")
st.caption(
    "Normalisation relative aux deux joueurs — met en évidence les forces/faiblesses de chacun."
)

radar_metrics = {
    "Win rate": ("win_rate_pct", 1),
    "KDA": ("kda_computed", 1),
    "Kills": ("avg_kills", 1),
    "Assists": ("avg_assists", 1),
    "CS": ("avg_cs", 1),
}

stats_a["kda_computed"] = kda(stats_a)
stats_b["kda_computed"] = kda(stats_b)

categories = list(radar_metrics.keys())
values_a, values_b = [], []

for _cat, (key, _direction) in radar_metrics.items():
    va = stats_a.get(key, 0) or 0
    vb = stats_b.get(key, 0) or 0
    mx = max(va, vb, 1)
    values_a.append(round(va / mx * 100, 1))
    values_b.append(round(vb / mx * 100, 1))

fig = go.Figure()
fig.add_trace(
    go.Scatterpolar(
        r=values_a + [values_a[0]],
        theta=categories + [categories[0]],
        fill="toself",
        name=player_a,
        line_color="#1f77b4",
        opacity=0.7,
    )
)
fig.add_trace(
    go.Scatterpolar(
        r=values_b + [values_b[0]],
        theta=categories + [categories[0]],
        fill="toself",
        name=player_b,
        line_color="#ff7f0e",
        opacity=0.7,
    )
)
fig.update_layout(
    polar={"radialaxis": {"visible": True, "range": [0, 100]}},
    height=400,
    showlegend=True,
)
st.plotly_chart(fig, width="stretch")

# ─── Comparaison champion pools ──────────────────────────────────────────────

st.markdown("---")
st.markdown("### Champions en commun vs exclusifs")

if not pool_a.empty and not pool_b.empty:
    champs_a = set(pool_a["champion"])
    champs_b = set(pool_b["champion"])
    common = champs_a & champs_b
    only_a = champs_a - champs_b
    only_b = champs_b - champs_a

    col1, col2, col3 = st.columns(3)
    col1.metric(f"Exclusifs {player_a}", len(only_a))
    col2.metric("Champions en commun", len(common))
    col3.metric(f"Exclusifs {player_b}", len(only_b))

    if common:
        st.markdown("#### Champions joués par les deux")
        comp = (
            pool_a[pool_a["champion"].isin(common)][["champion", "games", "win_rate_pct"]]
            .rename(
                columns={"games": f"Parties ({player_a})", "win_rate_pct": f"Win% ({player_a})"}
            )
            .merge(
                pool_b[pool_b["champion"].isin(common)][
                    ["champion", "games", "win_rate_pct"]
                ].rename(
                    columns={"games": f"Parties ({player_b})", "win_rate_pct": f"Win% ({player_b})"}
                ),
                on="champion",
            )
        )
        st.dataframe(
            comp.rename(columns={"champion": "Champion"}), hide_index=True, width="stretch"
        )
