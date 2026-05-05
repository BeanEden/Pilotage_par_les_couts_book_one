"""
Page Direction Financiere — Dashboard operationnel Book One MVP
Jalons S4 / S8 | Courbes planifie/reel filtrables | Liaison temps reel
Budget valide : 130 000 EUR | Periode : jan-fev 2025
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from simulation import get_simulation_data, get_serie_hebdo, BUDGET_VALIDE, BUDGET_RH
from data import calcul_taux_jour
from utils_pdf import export_page_to_pdf

CAT_COLORS = {
    "Toutes":                 "#12182B",
    "Ressources Humaines":    "#1E2761",
    "Infrastructure & Cloud": "#378ADD",
    "Licences & Logiciels":   "#1D9E75",
    "Données & APIs":         "#BA7517",
    "Qualite & Tests":        "#D4537E",
    "Legal & Conformite":     "#7F77DD",
    "Operationnel":           "#5F5E5A",
    "Provision & Risques":    "#E24B4A",
}

# ─────────────────────────────────────────────────────────────
# GRAPHIQUES
# ─────────────────────────────────────────────────────────────

def gauge(val, max_val, title, seuil_warn=70, seuil_ok=85, suffix="%"):
    bar_color = "#1D9E75" if val >= seuil_ok else "#BA7517" if val >= seuil_warn else "#E24B4A"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=val,
        number={"suffix": suffix, "font": {"size": 24}},
        title={"text": title, "font": {"size": 11}},
        gauge={
            "axis": {"range": [0, max_val], "tickfont": {"size": 9}},
            "bar": {"color": bar_color, "thickness": 0.25},
            "bgcolor": "rgba(0,0,0,0.04)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, max_val * seuil_warn / 100], "color": "#FADADA"},
                {"range": [max_val * seuil_warn / 100, max_val * seuil_ok / 100], "color": "#FFF3CD"},
                {"range": [max_val * seuil_ok / 100, max_val], "color": "#D4EDDA"},
            ],
        },
    ))
    fig.update_layout(height=175, margin=dict(l=8, r=8, t=28, b=8),
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(size=11))
    return fig


def build_courbe_fusionnee(serie: dict, filtre_cat: str, sem_courante: int) -> go.Figure:
    """
    Courbe planifie vs reel cumulees.
    Passe (jusqu'a sem_courante) en trait plein, futur en pointille.
    Zone d'ecart coloree. Marqueurs risques survenus Book One.
    """
    sems    = serie["semaines"]
    n       = len(sems)
    plan    = serie["planifie_cum"]
    reel    = serie["reel_cum"]
    idx_cut = min(sem_courante, n)
    col_plan = CAT_COLORS.get(filtre_cat, "#378ADD")
    col_reel = "#E24B4A"

    fig = go.Figure()

    # Zone d'ecart
    fig.add_trace(go.Scatter(
        x=sems[:idx_cut] + list(reversed(sems[:idx_cut])),
        y=reel[:idx_cut] + list(reversed(plan[:idx_cut])),
        fill="toself", fillcolor="rgba(226,75,74,0.08)",
        line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))

    # Planifie passe
    fig.add_trace(go.Scatter(
        x=sems[:idx_cut], y=plan[:idx_cut],
        mode="lines+markers", name="Planifie",
        line=dict(color=col_plan, width=2.5, dash="dash"),
        marker=dict(size=6),
        hovertemplate="<b>%{x}</b> — Planifie : %{y:,.0f} EUR<extra></extra>",
    ))

    # Planifie futur
    if idx_cut < n:
        fig.add_trace(go.Scatter(
            x=sems[idx_cut - 1:], y=plan[idx_cut - 1:],
            mode="lines", name="Planifie (prevision)",
            line=dict(color=col_plan, width=1.5, dash="dot"),
            showlegend=False,
            hovertemplate="<b>%{x}</b> — Planifie prevu : %{y:,.0f} EUR<extra></extra>",
        ))

    # Reel passe
    fig.add_trace(go.Scatter(
        x=sems[:idx_cut], y=reel[:idx_cut],
        mode="lines+markers", name="Reel cumule",
        line=dict(color=col_reel, width=2.5),
        marker=dict(size=8, symbol="diamond"),
        hovertemplate="<b>%{x}</b> — Reel : %{y:,.0f} EUR<extra></extra>",
    ))

    # Tendance (regression lineaire sur les 3 dernieres semaines connues)
    if idx_cut >= 3:
        xs    = list(range(1, idx_cut + 1))
        ys    = reel[:idx_cut]
        n_pts = min(3, len(xs))
        slope = (ys[-1] - ys[-n_pts]) / (xs[-1] - xs[-n_pts]) if xs[-1] != xs[-n_pts] else 0
        sems_pred  = sems[idx_cut - 1:]
        vals_pred  = [ys[-1] + slope * i for i in range(len(sems_pred))]
        fig.add_trace(go.Scatter(
            x=sems_pred, y=vals_pred,
            mode="lines", name="Tendance reelle",
            line=dict(color="#BA7517", width=2, dash="dot"),
            hovertemplate="<b>%{x}</b> — Tendance : %{y:,.0f} EUR<extra></extra>",
        ))

    # Ligne budget valide
    fig.add_hline(
        y=BUDGET_VALIDE,
        line=dict(color="#1D9E75", width=1.5, dash="dot"),
        annotation_text=f"Budget valide : {BUDGET_VALIDE:,} EUR",
        annotation_font_size=9, annotation_position="bottom right",
    )

    # Marqueur semaine courante
    if 0 < idx_cut <= n:
        fig.add_vline(
            x=idx_cut - 1,
            line=dict(color="#888", width=1.5, dash="dot"),
            annotation_text=f"Semaine {idx_cut}",
            annotation_font_size=9,
        )

    # Marqueurs risques survenus Book One
    # RS1-2 en S3, RS3-5 en S5-S6, RS6-8 en S11-S13
    risques_sem = {3: "RS1-2", 5: "RS3", 6: "RS4-5", 11: "RS6", 13: "RS7-8"}
    for s_idx, label in risques_sem.items():
        if s_idx <= idx_cut and s_idx <= n:
            fig.add_annotation(
                x=f"S{s_idx}", y=reel[s_idx - 1],
                text="!", showarrow=True, arrowhead=2,
                arrowcolor="#E24B4A", arrowsize=0.8,
                font=dict(size=12, color="#E24B4A"),
                ay=-30, ax=0,
                hovertext=f"Risque {label} apparu",
            )

    fig.update_layout(
        height=360,
        xaxis=dict(title="Semaine", gridcolor="#E8EAF0", tickfont=dict(size=10)),
        yaxis=dict(title="Cout cumule (EUR)", gridcolor="#E8EAF0"),
        legend=dict(orientation="h", y=1.12, font_size=10),
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=11), hovermode="x unified",
    )
    return fig


def build_courbe_hebdo_cat(serie: dict, cats_select: list, sem_courante: int) -> go.Figure:
    """Depenses hebdomadaires non-cumulees par categorie — planifie vs reel."""
    sems = serie["semaines"]
    n    = len(sems)
    idx  = min(sem_courante, n)
    fig  = go.Figure()

    if not cats_select:
        fig.update_layout(title="Selectionnez au moins une categorie")
        return fig

    for cat in cats_select:
        plan_vals = serie["planifie_par_cat"].get(cat, [0] * n)
        reel_vals = serie["reel_par_cat"].get(cat, [0] * n)
        col = CAT_COLORS.get(cat, "#888")

        fig.add_trace(go.Scatter(
            x=sems, y=plan_vals, name=f"{cat} (plan)",
            mode="lines", line=dict(color=col, width=1.5, dash="dot"),
            opacity=0.5,
            hovertemplate=f"<b>%{{x}}</b> — {cat} plan : %{{y:,.0f}} EUR<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=sems[:idx], y=reel_vals[:idx], name=cat,
            mode="lines+markers", line=dict(color=col, width=2.5),
            marker=dict(size=6),
            hovertemplate=f"<b>%{{x}}</b> — {cat} reel : %{{y:,.0f}} EUR<extra></extra>",
        ))

    fig.update_layout(
        height=320,
        xaxis=dict(title="Semaine", gridcolor="#E8EAF0", tickfont=dict(size=10)),
        yaxis=dict(title="EUR / semaine", gridcolor="#E8EAF0"),
        legend=dict(orientation="h", y=1.12, font_size=9),
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=11), hovermode="x unified",
    )
    return fig


def build_chart_budget_usage_cat(serie: dict, cats_select: list, sem_courante: int) -> go.Figure:
    """Barres comparatives planifie total vs reel a date par categorie."""
    fig = go.Figure()
    for cat in cats_select:
        plan_total = sum(serie["planifie_par_cat"].get(cat, []))
        reel_total = sum(serie["reel_par_cat"].get(cat, [])[:sem_courante])
        col = CAT_COLORS.get(cat, "#888")
        fig.add_trace(go.Bar(
            name=f"{cat} plan", x=[cat], y=[plan_total],
            marker_color=col, opacity=0.4,
            hovertemplate=f"<b>{cat}</b><br>Planifie total : %{{y:,.0f}} EUR<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            name=f"{cat} reel", x=[cat], y=[reel_total],
            marker_color=col,
            hovertemplate=f"<b>{cat}</b><br>Reel a date : %{{y:,.0f}} EUR<extra></extra>",
        ))
    fig.update_layout(
        barmode="group", height=280,
        xaxis=dict(tickangle=-20, tickfont=dict(size=9)),
        yaxis=dict(title="EUR", gridcolor="#E8EAF0"),
        legend=dict(font_size=9, orientation="h", y=-0.3),
        margin=dict(l=10, r=10, t=10, b=80),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=11),
    )
    return fig


def build_chart_retard_ressource(equipe, res_sel, sem_courante):
    """Barres : jours de retard simules par ressource au jalon courant."""
    retards_sim = {
        "PM":  [0, 0],
        "BE":  [0, 5],   # arret maladie S5
        "MOB": [0, 2],
        "QA":  [0, 0],
        "FRL": [0, 1],
    }
    jalons = ["S4", "S8"]
    # Selectionner le jalon le plus proche de la semaine courante
    if sem_courante <= 4:
        idx_j = 0
    else:
        idx_j = 1

    labels = [r for r in res_sel if r in retards_sim]
    vals   = [retards_sim.get(r, [0, 0])[idx_j] for r in labels]

    res_labels = {m["id"]: m["label"] for m in equipe} if isinstance(equipe, list) else {}
    labels_aff = [res_labels.get(r, r) for r in labels]

    col_vals = ["#E24B4A" if v > 3 else "#BA7517" if v > 0 else "#1D9E75" for v in vals]
    fig = go.Figure(go.Bar(
        x=labels_aff, y=vals, marker_color=col_vals,
        text=[f"{v}j" for v in vals], textposition="outside",
        hovertemplate="%{x} — %{y} jours de retard<extra></extra>",
    ))
    fig.update_layout(
        height=240,
        xaxis=dict(tickfont=dict(size=9)),
        yaxis=dict(title="Jours de retard", gridcolor="#E8EAF0"),
        margin=dict(l=10, r=10, t=10, b=30),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=11),
    )
    return fig


def build_chart_cout_ressource(sim, res_sel):
    """Barres : cout reel vs planifie par ressource."""
    cpr    = sim["cout_par_ressource"]
    labels = [r for r in res_sel if r in cpr]
    plans  = [cpr[r]["planifie"] for r in labels]
    reels  = [cpr[r]["reel"] for r in labels]
    labels_aff = [cpr[r]["label"] for r in labels]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Planifie", x=labels_aff, y=plans,
        marker_color="#B5D4F4",
        hovertemplate="%{x} — Planifie : %{y:,.0f} EUR<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Reel", x=labels_aff, y=reels,
        marker_color="#378ADD",
        hovertemplate="%{x} — Reel : %{y:,.0f} EUR<extra></extra>",
    ))
    fig.update_layout(
        barmode="group", height=240,
        xaxis=dict(tickfont=dict(size=9)),
        yaxis=dict(title="EUR", gridcolor="#E8EAF0"),
        legend=dict(orientation="h", y=1.1, font_size=10),
        margin=dict(l=10, r=10, t=30, b=30),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=11),
    )
    return fig


def build_chart_meteo_evolution(sim, res_sel, sem_courante):
    """Courbe d'evolution du moral equipe sur les jalons S4 / S8."""
    jalons_keys = ["S4", "S8"]
    jalons_x    = [4, 8]

    fig = go.Figure()
    meteo_data = sim["meteo"]
    
    for rid in res_sel:
        # On recupere les scores pour S4 et S8
        hist = meteo_data.get(rid, {})
        scores = [hist.get("S4", 2), hist.get("S8", 2)]
        
        fig.add_trace(go.Scatter(
            x=jalons_x, y=scores,
            mode="lines+markers", name=rid,
            line=dict(width=2),
            marker=dict(size=8),
            hovertemplate=f"<b>{rid}</b> — %{{x}} : %{{y}}/3<extra></extra>",
        ))

    fig.add_hline(y=2, line=dict(color="#BA7517", width=1, dash="dot"),
                  annotation_text="Seuil vigilance", annotation_font_size=9)
    fig.update_layout(
        height=240,
        xaxis=dict(title="Semaine", tickvals=[4, 8], ticktext=["S4", "S8"],
                   gridcolor="#E8EAF0"),
        yaxis=dict(title="Moral (1-3)", range=[0.5, 3.5], gridcolor="#E8EAF0",
                   tickvals=[1, 2, 3], ticktext=["Difficile", "Correcte", "Excellente"]),
        legend=dict(orientation="h", y=1.12, font_size=10),
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=11),
    )
    return fig


# ─────────────────────────────────────────────────────────────
# RENDER PRINCIPAL
# ─────────────────────────────────────────────────────────────

def render_direction_financiere():
    st.markdown("# Dashboard Direction Financiere — Book One")
    st.caption(
        "Suivi budgetaire operationnel : planifie vs reel, ecarts, risques survenus. "
        "Jalons S4 (architecture) et S8 (livraison finale). "
        "Donnees liees en temps reel au Gantt et a l'equipe."
    )

    sim    = get_simulation_data()
    equipe = st.session_state.get("equipe", sim["equipe"])

    # ── Selecteur de semaine ─────────────────────────────────
    sem_courante = st.slider(
        "Semaine courante (simulation de l'avancement)",
        min_value=1, max_value=8, value=8,
        format="S%d", key="df_sem_courante"
    )

    # Jalon le plus proche pour les KPIs
    if sem_courante <= 4:
        jkey = "S4"
    elif sem_courante <= 8:
        jkey = "S8"
    else:
        jkey = "S14"

    jdata = sim["jalons"][jkey]
    serie = get_serie_hebdo("Toutes")

    # ── Filtre categorie ─────────────────────────────────────
    col_f1, col_f2 = st.columns([2, 3])
    filtre_cat = col_f1.selectbox(
        "Filtrer les courbes par categorie de cout",
        options=serie["categories"],
        key="df_filtre_cat"
    )

    st.markdown("---")

    # ── KPIs operationnels ───────────────────────────────────
    st.markdown(f"#### Indicateurs cles au jalon {jkey}")

    cout_plan = jdata["cout_planifie"]
    cout_reel = jdata["cout_reel"]
    ecart_abs = cout_reel - cout_plan
    ecart_pct = ecart_abs / max(1, cout_plan) * 100
    taux_ach  = jdata["taux_achevement"]
    budget_conso_pct = cout_reel / BUDGET_VALIDE * 100

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Taches terminees",
              f"{jdata['taches_terminees']} / {jdata['taches_prevues']}",
              f"{jdata['taches_retard']} en retard",
              delta_color="inverse" if jdata["taches_retard"] > 0 else "normal")
    k2.metric("Taux d'achevement",
              f"{taux_ach:.0f}%",
              "Objectif 100%")
    k3.metric("Cout planifie", f"{int(cout_plan):,} EUR".replace(",", " "))
    k4.metric("Cout reel",
              f"{int(cout_reel):,} EUR".replace(",", " "),
              f"{ecart_pct:+.1f}% vs plan",
              delta_color="inverse" if ecart_abs > 0 else "normal")
    k5.metric("Budget consomme",
              f"{budget_conso_pct:.0f}%",
              f"/ {BUDGET_VALIDE:,} EUR valide")
    k6.metric("Couts non planifies",
              f"{jdata['couts_non_planifies']:,} EUR".replace(",", " "),
              delta_color="inverse" if jdata["couts_non_planifies"] > 0 else "off")

    st.markdown("---")

    # ── Jauges ───────────────────────────────────────────────
    st.markdown("#### Jauges de pilotage")
    g1, g2, g3, g4 = st.columns(4)

    with g1:
        st.plotly_chart(gauge(taux_ach, 100, "Avancement taches"), use_container_width=True)
    with g2:
        marge_budget = max(0, 100 - budget_conso_pct)
        st.plotly_chart(
            gauge(marge_budget, 100, "Marge budgetaire restante",
                  seuil_warn=20, seuil_ok=40),
            use_container_width=True
        )
    with g3:
        # Respect du planning : 100% si pas de retard, baisse si des taches sont en retard
        nb_ret = jdata["taches_retard"]
        nb_tot = jdata["taches_prevues"]
        score_planning = max(0, (1 - nb_ret / max(1, nb_tot)) * 100)
        st.plotly_chart(gauge(score_planning, 100, "Respect du planning"), use_container_width=True)
    with g4:
        # Derive cout : 100 = dans les clous, baisse si ecart > 0
        derive = max(0, 100 - abs(ecart_pct) * 2)
        st.plotly_chart(
            gauge(derive, 100, "Maitrise des couts", seuil_warn=60, seuil_ok=80),
            use_container_width=True
        )

    st.markdown("---")

    # ── Utilisation du budget par categorie + phasage ────────
    st.markdown("#### Focus budgetaire : utilisation par categorie & phasage mensuel")

    cats_dispo = get_serie_hebdo()["categories"][1:]
    c_sel_budget = st.multiselect(
        "Selectionner les categories a analyser",
        options=cats_dispo,
        default=cats_dispo[:4],
        key="df_budget_usage_cat"
    )

    col_g, col_t = st.columns([3, 2])

    with col_g:
        st.plotly_chart(
            build_chart_budget_usage_cat(get_serie_hebdo("Toutes"), c_sel_budget, sem_courante),
            use_container_width=True
        )

    with col_t:
        all_serie = get_serie_hebdo("Toutes")
        p_par_cat = all_serie["planifie_par_cat"]
        r_par_cat = all_serie["reel_par_cat"]

        # Mois Book One : jan-avr 2025
        config_m = [
            ("Jan 2025", 1, 3),
            ("Fev 2025", 4, 7),
            ("Mar 2025", 8, 11),
            ("Avr 2025", 12, 14),
        ]

        filtered_data = []
        for mois, s_deb, s_fin in config_m:
            pm, rm = 0, 0
            for cat in c_sel_budget:
                pm += sum(p_par_cat.get(cat, [0] * 14)[s_deb - 1:s_fin])
                s_fin_reel = min(s_fin, sem_courante)
                if s_fin_reel >= s_deb:
                    rm += sum(r_par_cat.get(cat, [0] * 14)[s_deb - 1:s_fin_reel])
            filtered_data.append({"Mois": mois, "Planifie": pm, "Reel": rm, "Ecart": rm - pm})

        df_ph_f = pd.DataFrame(filtered_data)
        st.markdown("<br>", unsafe_allow_html=True)
        st.dataframe(
            df_ph_f.style
            .format({"Planifie": "{:,.0f} EUR", "Reel": "{:,.0f} EUR", "Ecart": "{:+,.0f} EUR"})
            .apply(lambda x: ["color:#E24B4A" if x["Ecart"] > 2000 else "" for _ in x], axis=1),
            use_container_width=True, hide_index=True,
        )
        t_reel = df_ph_f["Reel"].sum()
        t_plan = df_ph_f["Planifie"].sum()
        st.metric("Total selection (reel a date)",
                  f"{t_reel:,.0f} EUR".replace(",", " "),
                  f"{t_reel - t_plan:+,.0f} EUR vs plan total".replace(",", " "),
                  delta_color="inverse")

    st.markdown("---")

    # ── Courbe principale & Risques ──────────────────────────
    st.markdown("#### Analyse de la tendance : couts & risques survenus")
    c_graph, c_risks = st.columns([2, 1])

    with c_graph:
        st.markdown(f"**Couts planifies vs reels — {filtre_cat}**")
        st.caption(
            "Trait plein = passe | Pointille = prevision | "
            "! = risque survenu | Zone rouge = ecart"
        )
        st.plotly_chart(
            build_courbe_fusionnee(get_serie_hebdo(filtre_cat), filtre_cat, sem_courante),
            use_container_width=True,
        )

    with c_risks:
        st.markdown(f"**Journal des risques (S1 a S{sem_courante})**")
        risques_visibles = []
        for jk, jd in sim["jalons"].items():
            if jd["semaine"] <= sem_courante:
                risques_visibles.extend(jd["risques"])

        if not risques_visibles:
            st.info("Aucun risque majeur survenu a ce stade.")
        else:
            cat_icons = {
                "Ressources humaines": "Collaborateur",
                "Technologie": "Technique",
                "MOA / Conformite": "Conformite",
            }
            for r in risques_visibles:
                col_r   = {"Faible": "#1D9E75", "Moyen": "#BA7517", "Eleve": "#E24B4A"}.get(r["impact"], "#888")
                cat_lbl = cat_icons.get(r["categorie"], r["categorie"])
                st.markdown(
                    f"<div style='padding:6px 10px;margin-bottom:4px;border-left:3px solid {col_r};"
                    f"background:var(--color-background-secondary);border-radius:0 4px 4px 0'>"
                    f"<div style='font-weight:500;font-size:12px'>{r['id']} — {r['titre']}</div>"
                    f"<div style='font-size:10px;color:var(--color-text-secondary)'>"
                    f"{cat_lbl} | {r['impact']} | {r['statut']}"
                    + (f" | +{r['cout']:,} EUR" if r["cout"] > 0 else "")
                    + f"</div></div>",
                    unsafe_allow_html=True,
                )

    # ── Depenses hebdomadaires par categorie ─────────────────
    st.markdown("#### Depenses hebdomadaires par categorie (non cumule)")
    cats_dispo = get_serie_hebdo()["categories"][1:]
    cats_sel   = st.multiselect(
        "Selectionner les categories a comparer",
        options=cats_dispo,
        default=cats_dispo[:3],
        key="df_multi_cats"
    )
    st.plotly_chart(
        build_courbe_hebdo_cat(get_serie_hebdo("Toutes"), cats_sel, sem_courante),
        use_container_width=True,
    )

    st.markdown("---")

    # ── Analyse par ressource ────────────────────────────────
    st.markdown("#### Analyse par ressource : retards & couts")
    res_ids    = [m["id"] for m in equipe]
    res_labels = {m["id"]: m["label"] for m in equipe}

    res_sel = st.multiselect(
        "Selectionner les ressources a analyser",
        options=res_ids,
        default=res_ids[:4],
        format_func=lambda x: res_labels.get(x, x),
        key="df_res_analyse_dual"
    )

    rc1, rc2 = st.columns(2)
    with rc1:
        st.markdown("**Suivi des retards (jours)**")
        st.plotly_chart(
            build_chart_retard_ressource(equipe, res_sel, sem_courante),
            use_container_width=True
        )
    with rc2:
        st.markdown("**Cout reel vs planifie (EUR)**")
        st.plotly_chart(
            build_chart_cout_ressource(sim, res_sel),
            use_container_width=True
        )

    st.markdown("---")

    # ── Meteo equipe ─────────────────────────────────────────
    st.markdown("#### Meteo & evolution de l'equipe")

    meteo         = jdata["meteo"]
    meteo_res_ids = list(meteo.keys())
    m_labels_map  = {m["id"]: m["label"] for m in equipe}

    m_sel = st.multiselect(
        "Selectionner les collaborateurs a suivre",
        options=meteo_res_ids,
        default=meteo_res_ids[:4],
        format_func=lambda x: m_labels_map.get(x, x),
        key="df_meteo_dual"
    )

    col_evol, col_stat = st.columns([2, 1])

    with col_evol:
        st.markdown("**Evolution du moral (S4 / S8)**")
        st.plotly_chart(
            build_chart_meteo_evolution(sim, m_sel, sem_courante),
            use_container_width=True
        )

    def _meteo_icon(s):
        if s >= 2.5: return "soleil", "#1D9E75"
        if s >= 1.5: return "mitige", "#BA7517"
        return "difficile", "#E24B4A"

    with col_stat:
        st.markdown(f"**Etat au jalon {jkey}**")
        for mid in m_sel:
            # meteo est jdata["meteo"], qui est un dict {resource_id: score_int}
            score = meteo.get(mid, 2)
            # Securite au cas ou la structure changerait
            if isinstance(score, dict):
                score = score.get(jkey, 2)
            
            _, col_c = _meteo_icon(score)
            label_s  = {1: "Difficile", 2: "Correcte", 3: "Excellente"}.get(score, "—")
            label_nm = m_labels_map.get(mid, mid)
            st.markdown(
                f"<div style='display:flex;align-items:center;padding:6px 10px;margin-bottom:5px;"
                f"background:var(--color-background-secondary);border-radius:6px;"
                f"border:1px solid var(--color-border-tertiary)'>"
                f"<div style='flex:1'>"
                f"<div style='font-size:11px;font-weight:600'>{label_nm}</div>"
                f"<div style='font-size:10px;color:{col_c}'>{label_s}</div>"
                f"</div>"
                f"<div style='font-size:12px;font-weight:700;color:var(--color-text-secondary)'>{score}/3</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # ── Export PDF ───────────────────────────────────────────
    kpis_pdf = {
        "Jalon":          jkey,
        "Avancement":     f"{taux_ach:.0f}%",
        "Cout planifie":  f"{int(cout_plan):,} EUR",
        "Cout reel":      f"{int(cout_reel):,} EUR",
        "Ecart":          f"{ecart_pct:+.1f}%",
        "Budget valide":  f"{BUDGET_VALIDE:,} EUR",
    }
    pdf_bytes = export_page_to_pdf("Dashboard Direction Financiere — Book One", kpis_pdf)
    st.download_button(
        "Telecharger le rapport PDF",
        data=pdf_bytes,
        file_name="Rapport_DF_BookOne.pdf",
        mime="application/pdf",
    )
