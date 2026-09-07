"""Page Méta — pick rate, ban rate et win rate sur les 3 derniers patches."""

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.queries import fetch_ban_rates, fetch_meta_by_patch, fetch_patches
from dashboard.utils import question_metier

st.set_page_config(page_title="Méta — Nexus Analytics", page_icon="📈", layout="wide")

st.title("📈 Tendances méta")
st.caption("Pick rate, ban rate et win rate par champion — 3 derniers patches LFL")

question_metier(
    "Quel est le pick rate, ban rate et win rate par champion sur les 3 derniers patches "
    "— la méta a-t-elle changé depuis le dernier patch ?",
    "Yasmine Karim — Analyste senior (§Besoins fonctionnels)",
)

# ─── Chargement des 3 derniers patches ───────────────────────────────────────

with st.spinner("Chargement des patches..."):
    patches = fetch_patches()

if not patches:
    st.error("Aucun patch trouvé en base.")
    st.stop()

last_3 = patches[:3]
current_patch = last_3[0]

col_f1, col_f2 = st.columns([3, 2])
with col_f1:
    selected_patch = st.selectbox(
        "Patch affiché",
        options=last_3 + [p for p in patches[3:] if p not in last_3],
        help="Les 3 derniers patches sont pré-chargés pour la comparaison d'évolution.",
    )
with col_f2:
    min_picks = st.slider("Picks minimum", min_value=1, max_value=30, value=5)

# Chargement du patch sélectionné (picks + bans)
with st.spinner("Chargement des données méta..."):
    df_picks = fetch_meta_by_patch(patch=selected_patch)
    df_bans = fetch_ban_rates(patch=selected_patch)

if df_picks.empty:
    st.warning("Aucune donnée méta pour ce patch.")
    st.stop()

# Fusion picks + bans
df = pd.merge(
    df_picks[["champion", "picks", "wins", "pick_rate_pct", "win_rate_pct"]],
    df_bans[df_bans["patch"] == selected_patch][["champion", "bans", "ban_rate_pct"]],
    on="champion",
    how="left",
).fillna({"bans": 0, "ban_rate_pct": 0.0})

df = df[df["picks"] >= min_picks].copy()

if df.empty:
    st.warning("Aucun champion avec ce nombre de picks minimum.")
    st.stop()

# ─── KPIs du patch ───────────────────────────────────────────────────────────

st.markdown(f"### Patch `{selected_patch}`")

avg_wr = round(df["win_rate_pct"].mean(), 1)
top_pick = df.nlargest(1, "pick_rate_pct").iloc[0]
top_ban = df_bans[df_bans["patch"] == selected_patch].nlargest(1, "ban_rate_pct")
top_win = df[df["picks"] >= df["picks"].quantile(0.5)].nlargest(1, "win_rate_pct").iloc[0]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Champion le plus pické", top_pick["champion"], f"{top_pick['pick_rate_pct']:.1f}%")
col2.metric(
    "Champion le plus banni",
    top_ban.iloc[0]["champion"] if not top_ban.empty else "—",
    f"{top_ban.iloc[0]['ban_rate_pct']:.1f}%" if not top_ban.empty else "",
)
col3.metric(
    "Meilleur win rate (parmi populaires)", top_win["champion"], f"{top_win['win_rate_pct']:.1f}%"
)
col4.metric("Win rate moyen du patch", f"{avg_wr}%")

st.markdown("---")

# ─── Scatter : pick rate vs win rate + ban rate ───────────────────────────────

st.markdown("### Pick rate × Win rate (taille bulle = ban rate)")
st.caption(
    "Quadrant haut-droite = champions dominants. "
    "Grande bulle = souvent banni — confirme leur menace perçue."
)

df["ban_size"] = (df["ban_rate_pct"] + 1).clip(lower=1)  # évite size=0

fig = px.scatter(
    df,
    x="pick_rate_pct",
    y="win_rate_pct",
    size="ban_size",
    text="champion",
    color="win_rate_pct",
    color_continuous_scale="RdYlGn",
    color_continuous_midpoint=50,
    hover_data={"picks": True, "bans": True, "ban_rate_pct": True, "ban_size": False},
    labels={
        "pick_rate_pct": "Pick rate (%)",
        "win_rate_pct": "Win rate (%)",
        "ban_size": "Ban rate",
    },
)
avg_pick = df["pick_rate_pct"].mean()
fig.add_hline(y=50, line_dash="dash", line_color="gray", opacity=0.4, annotation_text="50% WR")
fig.add_vline(
    x=avg_pick,
    line_dash="dash",
    line_color="gray",
    opacity=0.4,
    annotation_text=f"Pick moy. {avg_pick:.1f}%",
)
fig.update_traces(textposition="top center", textfont_size=9)
fig.update_layout(height=520, coloraxis_showscale=False)
st.plotly_chart(fig, width="stretch")

# ─── Top champions : picks, bans, wins ───────────────────────────────────────

st.markdown("---")
col_a, col_b, col_c = st.columns(3)

with col_a:
    st.markdown("#### 🎯 Top pick rate")
    top10_pick = df.nlargest(10, "pick_rate_pct")[["champion", "pick_rate_pct", "picks"]]
    fig2 = px.bar(
        top10_pick,
        x="pick_rate_pct",
        y="champion",
        orientation="h",
        color="pick_rate_pct",
        color_continuous_scale="Blues",
        text_auto=".1f",
        labels={"pick_rate_pct": "Pick %", "champion": ""},
    )
    fig2.update_layout(
        yaxis={"categoryorder": "total ascending"}, height=320, coloraxis_showscale=False
    )
    st.plotly_chart(fig2, width="stretch")

with col_b:
    st.markdown("#### 🚫 Top ban rate")
    top10_ban = df.nlargest(10, "ban_rate_pct")[["champion", "ban_rate_pct", "bans"]]
    fig3 = px.bar(
        top10_ban,
        x="ban_rate_pct",
        y="champion",
        orientation="h",
        color="ban_rate_pct",
        color_continuous_scale="Reds",
        text_auto=".1f",
        labels={"ban_rate_pct": "Ban %", "champion": ""},
    )
    fig3.update_layout(
        yaxis={"categoryorder": "total ascending"}, height=320, coloraxis_showscale=False
    )
    st.plotly_chart(fig3, width="stretch")

with col_c:
    st.markdown("#### 🏆 Top win rate (picks suffisants)")
    top10_win = df[df["picks"] >= max(3, int(df["picks"].quantile(0.4)))].nlargest(
        10, "win_rate_pct"
    )[["champion", "win_rate_pct", "picks"]]
    fig4 = px.bar(
        top10_win,
        x="win_rate_pct",
        y="champion",
        orientation="h",
        color="win_rate_pct",
        color_continuous_scale="RdYlGn",
        text_auto=".1f",
        labels={"win_rate_pct": "Win %", "champion": ""},
    )
    fig4.update_layout(
        yaxis={"categoryorder": "total ascending"}, height=320, coloraxis_showscale=False
    )
    st.plotly_chart(fig4, width="stretch")

# ─── La méta a-t-elle changé ? Comparaison 3 patches ────────────────────────

st.markdown("---")
st.markdown("### 🔄 Évolution de la méta — 3 derniers patches")
st.caption(
    "Champions dont le pick rate ou le win rate a le plus évolué entre les 3 derniers patches. "
    "Signal clé pour la préparation de matchs."
)

if len(last_3) < 2:
    st.info("Pas assez de patches pour comparer l'évolution.")
else:
    with st.spinner("Chargement des 3 patches pour comparaison..."):
        frames = []
        for p in last_3:
            dp = fetch_meta_by_patch(patch=p)
            db = fetch_ban_rates(patch=p)
            if dp.empty:
                continue
            merged_p = pd.merge(
                dp[["champion", "picks", "pick_rate_pct", "win_rate_pct"]],
                db[db["patch"] == p][["champion", "ban_rate_pct"]],
                on="champion",
                how="left",
            ).fillna({"ban_rate_pct": 0.0})
            merged_p["patch"] = p
            frames.append(merged_p)

    if len(frames) >= 2:
        all_patches_df = pd.concat(frames, ignore_index=True)

        # Champions présents dans au moins 2 patches
        champ_counts = all_patches_df.groupby("champion")["patch"].count()
        common = champ_counts[champ_counts >= 2].index.tolist()
        evo_df = all_patches_df[all_patches_df["champion"].isin(common)]

        # Évolution pick rate : patch[0] vs patch[1]
        pivot_pr = evo_df.pivot_table(index="champion", columns="patch", values="pick_rate_pct")
        if last_3[0] in pivot_pr.columns and last_3[1] in pivot_pr.columns:
            pivot_pr["delta_pick"] = (pivot_pr[last_3[0]] - pivot_pr[last_3[1]]).round(2)
            movers = pivot_pr["delta_pick"].dropna().sort_values(key=abs, ascending=False).head(12)

            fig_evo = px.bar(
                movers.reset_index(),
                x="champion",
                y="delta_pick",
                color="delta_pick",
                color_continuous_scale="RdYlGn",
                color_continuous_midpoint=0,
                text="delta_pick",
                labels={
                    "champion": "Champion",
                    "delta_pick": f"Δ Pick rate ({last_3[0]} vs {last_3[1]})",
                },
                title=f"Variation du pick rate entre {last_3[1]} et {last_3[0]}",
            )
            fig_evo.update_traces(texttemplate="%{text:+.1f}%", textposition="outside")
            fig_evo.update_layout(height=380, coloraxis_showscale=False)
            st.plotly_chart(fig_evo, width="stretch")

        # Tableau comparatif des 3 patches
        with st.expander("Tableau comparatif complet — 3 patches"):
            pivot_full = all_patches_df.pivot_table(
                index="champion",
                columns="patch",
                values=["pick_rate_pct", "win_rate_pct", "ban_rate_pct"],
            )
            pivot_full.columns = [f"{v} — {p}" for v, p in pivot_full.columns]
            st.dataframe(
                pivot_full.reset_index().rename(columns={"champion": "Champion"}),
                hide_index=True,
                width="stretch",
            )
    else:
        st.info("Données insuffisantes pour comparer les patches.")

# ─── Données brutes ───────────────────────────────────────────────────────────

with st.expander("Données brutes — patch sélectionné"):
    st.dataframe(
        df[["champion", "picks", "wins", "pick_rate_pct", "bans", "ban_rate_pct", "win_rate_pct"]]
        .rename(
            columns={
                "champion": "Champion",
                "picks": "Picks",
                "wins": "Victoires",
                "pick_rate_pct": "Pick %",
                "bans": "Bans",
                "ban_rate_pct": "Ban %",
                "win_rate_pct": "Win %",
            }
        )
        .sort_values("Pick %", ascending=False),
        width="stretch",
        hide_index=True,
    )
