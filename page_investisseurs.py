"""
Page Investisseurs — Book One MVP Mobile
ROI 24 mois | Modele de revenus commission 1 EUR/transaction | Courbe de Farmer
Budget valide : 130 000 EUR | CA previsionnel : 180 000 EUR an 1
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import math
from simulation import get_simulation_data, get_roi_data, BUDGET_VALIDE, CA_PREVISIONNEL
from utils_pdf import export_page_to_pdf

# ─────────────────────────────────────────────────────────────
# GRAPHIQUES
# ─────────────────────────────────────────────────────────────

def build_roi_chart(roi: dict) -> go.Figure:
    """Courbe cumulative revenus vs couts — break-even visible."""
    mois      = [f"M{i}" for i in roi["mois"]]
    rev_cumul = []
    c = 0
    for r in roi["rev_mensuel"]:
        c += r; rev_cumul.append(c)

    charges_cumul = []
    c2 = roi["investissement"]
    for ch in roi["charges_mensuel"]:
        c2 += ch; charges_cumul.append(c2)

    cash_flow_cumul = [r - ch for r, ch in zip(rev_cumul, charges_cumul)]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=mois, y=rev_cumul, name="Revenus cumules",
        line=dict(color="#1D9E75", width=2.5),
        fill="tonexty", fillcolor="rgba(29,158,117,0.07)",
        hovertemplate="M%{pointNumber+1} — Revenus : %{y:,.0f} EUR<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=mois, y=charges_cumul, name="Couts cumules (invest. + opex)",
        line=dict(color="#E24B4A", width=2, dash="dash"),
        hovertemplate="M%{pointNumber+1} — Couts : %{y:,.0f} EUR<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=mois, y=cash_flow_cumul, name="Cash-flow net cumule",
        line=dict(color="#378ADD", width=2),
        hovertemplate="M%{pointNumber+1} — Net : %{y:,.0f} EUR<extra></extra>",
    ))

    if roi["breakeven_mois"]:
        fig.add_vline(
            x=roi["breakeven_mois"] - 1,
            line=dict(color="#BA7517", width=1.5, dash="dot"),
            annotation_text=f"Break-even M{roi['breakeven_mois']}",
            annotation_font_size=10,
        )
    fig.add_hline(y=0, line=dict(color="#888", width=0.8, dash="dot"))

    fig.update_layout(
        height=320,
        xaxis=dict(title="Mois", gridcolor="#E8EAF0", tickfont=dict(size=9)),
        yaxis=dict(title="EUR", gridcolor="#E8EAF0"),
        legend=dict(orientation="h", y=1.12, font_size=10),
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=11),
    )
    return fig


def build_ca_mensuel(sim: dict, roi: dict) -> go.Figure:
    """
    CA mensuel prevu vs reel (barres).
    Les 14 premieres periodes = semaines de dev (CA = 0).
    A partir de M15 : revenus transactions.
    """
    labels = (
        [f"S{i}" for i in range(1, 9)]           # dev (8 semaines)
        + [f"M{i}" for i in range(1, 13)]        # post-lancement
    )
    prevu = sim["ca_mensuel_prevu"][:20]
    reel  = sim["ca_mensuel_reel"][:20]

    x_labels   = labels[:len(prevu)]
    reel_clean = [r if r is not None else 0 for r in reel]
    reel_mask  = [r is not None for r in reel]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=x_labels, y=prevu, name="CA prevu",
        marker_color="#B5D4F4", opacity=0.8,
        hovertemplate="%{x} — Prevu : %{y:,.0f} EUR<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=[x for x, m in zip(x_labels, reel_mask) if m],
        y=[r for r, m in zip(reel_clean, reel_mask) if m],
        name="CA reel", marker_color="#378ADD",
        hovertemplate="%{x} — Reel : %{y:,.0f} EUR<extra></extra>",
    ))
    # Repere lancement (apres S8)
    fig.add_vrect(
        x0=7.5, x1=8.5, fillcolor="#1D9E75", opacity=0.05,
        line_width=0, annotation_text="Lancement", annotation_font_size=9,
    )
    fig.update_layout(
        barmode="group", height=280,
        xaxis=dict(tickfont=dict(size=8), tickangle=-45, gridcolor="#E8EAF0"),
        yaxis=dict(title="EUR", gridcolor="#E8EAF0"),
        legend=dict(orientation="h", y=1.1, font_size=10),
        margin=dict(l=10, r=10, t=30, b=60),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=11),
    )
    return fig


def build_farmer_curve(sim: dict) -> go.Figure:
    """
    Matrice de risques — Courbe de Farmer.
    Risques contextuels Book One : geoloc RGPD, fraude credits, refus store,
    retard critique, ressource cle.
    """
    prob_map   = {"Faible": 0.1, "Moyenne": 0.4, "Elevee": 0.7}
    impact_map = {"Faible": 3000, "Moyen": 10000, "Eleve": 25000, "Tres eleve": 50000}

    fig = go.Figure()

    # Zones de fond Farmer
    fig.add_shape(type="rect", x0=0, x1=0.3, y0=0, y1=15000,
                  fillcolor="rgba(29,158,117,0.12)", line_width=0, layer="below")
    fig.add_shape(type="rect", x0=0.3, x1=0.6, y0=0, y1=15000,
                  fillcolor="rgba(186,117,23,0.10)", line_width=0, layer="below")
    fig.add_shape(type="rect", x0=0, x1=0.3, y0=15000, y1=55000,
                  fillcolor="rgba(186,117,23,0.10)", line_width=0, layer="below")
    fig.add_shape(type="rect", x0=0.3, x1=1.0, y0=15000, y1=55000,
                  fillcolor="rgba(226,75,74,0.12)", line_width=0, layer="below")
    fig.add_shape(type="rect", x0=0.6, x1=1.0, y0=0, y1=15000,
                  fillcolor="rgba(226,75,74,0.12)", line_width=0, layer="below")

    for txt, x, y, col in [
        ("ACCEPTABLE",   0.12, 5000,  "#1D9E75"),
        ("ALARP",        0.45, 5000,  "#BA7517"),
        ("INACCEPTABLE", 0.75, 40000, "#E24B4A"),
    ]:
        fig.add_annotation(x=x, y=y, text=txt, showarrow=False,
                           font=dict(size=10, color=col), opacity=0.6)

    # Courbe de Farmer (iso-risque P × I = 8000 EUR)
    p_curve = [i / 100 for i in range(5, 95, 5)]
    farmer_seuil = 8000
    i_curve = [farmer_seuil / p for p in p_curve]
    fig.add_trace(go.Scatter(
        x=p_curve, y=i_curve, mode="lines", name="Courbe de Farmer",
        line=dict(color="#BA7517", width=2, dash="dot"), hoverinfo="skip",
    ))

    # Risques initiaux planifies (Book One)
    risques_init = [
        {"id": "R1", "titre": "Retard critique",      "prob": 0.4,  "imp": 18000, "col": "#E24B4A"},
        {"id": "R2", "titre": "Refus App Store",       "prob": 0.35, "imp": 5000,  "col": "#BA7517"},
        {"id": "R3", "titre": "RGPD geolocalisation",  "prob": 0.15, "imp": 12000, "col": "#7F77DD"},
        {"id": "R4", "titre": "Ressource cle",         "prob": 0.15, "imp": 7000,  "col": "#1D9E75"},
        {"id": "R5", "titre": "Fraude credits 1 EUR",  "prob": 0.4,  "imp": 3000,  "col": "#378ADD"},
    ]
    for r in risques_init:
        fig.add_trace(go.Scatter(
            x=[r["prob"]], y=[r["imp"]],
            mode="markers+text",
            marker=dict(size=22, color=r["col"], opacity=0.4,
                        line=dict(color=r["col"], width=1.5)),
            text=[r["id"]], textposition="middle center",
            textfont=dict(size=9, color=r["col"]),
            name=r["id"],
            hovertemplate=(
                f"<b>{r['id']} — {r['titre']}</b><br>"
                f"Prob : {r['prob']:.0%} | Impact : {r['imp']:,} EUR<extra></extra>"
            ),
        ))

    # Risques survenus (resolus = croix vertes, en cours = croix rouges)
    risques_survenus = [
        {"id": "RS1", "titre": "API Open Library quota",    "prob": 0.05, "imp": 0,    "statut": "Resolu"},
        {"id": "RS2", "titre": "Licence Figma",             "prob": 0.10, "imp": 240,  "statut": "Resolu"},
        {"id": "RS3", "titre": "Arret maladie BE",          "prob": 0.15, "imp": 2800, "statut": "Resolu"},
        {"id": "RS4", "titre": "Geoloc iOS permission",     "prob": 0.20, "imp": 500,  "statut": "Resolu"},
        {"id": "RS5", "titre": "Upgrade infra DB",          "prob": 0.25, "imp": 700,  "statut": "En cours"},
    ]
    for r in risques_survenus:
        col = "#1D9E75" if r["statut"] == "Resolu" else "#E24B4A"
        fig.add_trace(go.Scatter(
            x=[r["prob"]], y=[max(r["imp"], 500)],
            mode="markers+text",
            marker=dict(size=14, color=col, symbol="x", opacity=0.9,
                        line=dict(color=col, width=2.5)),
            text=[r["id"]], textposition="top center",
            textfont=dict(size=8, color=col),
            name=r["id"],
            hovertemplate=(
                f"<b>{r['id']} — {r['titre']}</b><br>"
                f"Statut : {r['statut']} | Cout : {r['imp']:,} EUR<extra></extra>"
            ),
        ))

    fig.update_layout(
        height=380,
        xaxis=dict(title="Probabilite", range=[-0.02, 0.85],
                   tickformat=".0%", gridcolor="#E8EAF0"),
        yaxis=dict(title="Impact financier (EUR)", range=[-500, 55000], gridcolor="#E8EAF0"),
        legend=dict(orientation="h", y=-0.2, font_size=9),
        margin=dict(l=10, r=10, t=10, b=80),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=11),
    )
    return fig


def build_leviers_chart() -> go.Figure:
    """Leviers d'optimisation budgetaire Book One — barres colorees par effort."""
    leviers = [
        {"levier": "Figma Free vs Pro",                "economie": 100,  "effort": "Faible"},
        {"levier": "Linear vs Jira (startup plan)",    "economie": 100,  "effort": "Faible"},
        {"levier": "Instances Cloud preemptibles",     "economie": 360,  "effort": "Moyen"},
        {"levier": "Emulateurs vs BrowserStack",       "economie": 130,  "effort": "Moyen"},
        {"levier": "DPO interne vs externe",           "economie": 800,  "effort": "Eleve"},
        {"levier": "Alternant sur monitoring (STG)",   "economie": 200,  "effort": "Faible"},
        {"levier": "Reduction scope Wishes en V2",     "economie": 1400, "effort": "Moyen"},
    ]
    leviers = sorted(leviers, key=lambda x: -x["economie"])
    col_eff = {"Faible": "#1D9E75", "Moyen": "#BA7517", "Eleve": "#E24B4A"}
    fig = go.Figure(go.Bar(
        x=[l["economie"] for l in leviers],
        y=[l["levier"] for l in leviers],
        orientation="h",
        marker_color=[col_eff.get(l["effort"], "#888") for l in leviers],
        text=[f"{l['economie']:,} EUR" for l in leviers],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Economie : %{x:,.0f} EUR<extra></extra>",
    ))
    fig.update_layout(
        height=280,
        xaxis=dict(title="Economie potentielle (EUR)", gridcolor="#E8EAF0"),
        yaxis=dict(title="", tickfont=dict(size=9)),
        margin=dict(l=10, r=90, t=10, b=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=11), showlegend=False,
        uniformtext=dict(mode="hide", minsize=8),
    )
    return fig


# ─────────────────────────────────────────────────────────────
# RENDER PRINCIPAL
# ─────────────────────────────────────────────────────────────

def render_investisseurs():
    # ─────────────────────────────────────────────────────────────
    # INITIALISATION SESSION STATE (Sécurisée)
    # ─────────────────────────────────────────────────────────────
    if "invest_ca" not in st.session_state:
        mois_list = [f"M{i}" for i in range(1, 25)]
        # 8 semaines = ~2 mois de dev (S1-S8)
        # On remplit jusqu'a 24 mois
        rev_def = ([0] * 2 + [1500, 3000, 6000, 9000, 12000, 15000, 18000, 20000, 22000, 25000] + [25000]*12)[:24]
        st.session_state.invest_ca = pd.DataFrame({
            "Mois": mois_list,
            "CA Prevu (EUR)": rev_def,
            "CA Realise (EUR)": [r if (r is not None and r > 0) else None for r in rev_def],
        })

    if "invest_extra_costs" not in st.session_state:
        st.session_state.invest_extra_costs = pd.DataFrame([
            {"Libelle": "Marketing lancement (App Store)", "Mois": "M15", "Montant (EUR)": 3000},
            {"Libelle": "Support utilisateurs (freelance)", "Mois": "M17", "Montant (EUR)": 1500},
            {"Libelle": "Maintenance infra mensuelle",      "Mois": "M16", "Montant (EUR)": 800},
        ])

    sim = get_simulation_data()
    roi = get_roi_data()

    # ── Editeur donnees CA & couts additionnels ───────────────
    with st.expander("Modifier les donnees de projection (CA, couts additionnels)", expanded=False):
        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown("**CA Mensuel (Prevu vs Realise)**")
            st.caption("M1-M2 = phase dev (CA = 0). Revenus a partir de M3 (lancement).")
            st.session_state.invest_ca = st.data_editor(
                st.session_state.invest_ca,
                num_rows="fixed", use_container_width=True,
                hide_index=True, key="ca_editor"
            )
        with c2:
            st.markdown("**Couts Additionnels & OPEX**")
            st.session_state.invest_extra_costs = st.data_editor(
                st.session_state.invest_extra_costs,
                num_rows="dynamic", use_container_width=True,
                hide_index=True, key="costs_editor"
            )

    # Recalcul ROI a partir des donnees editees
    ca_data    = st.session_state.invest_ca
    extra_costs = st.session_state.invest_extra_costs

    proj_rev = [r if pd.notnull(r) else p
                for r, p in zip(ca_data["CA Realise (EUR)"], ca_data["CA Prevu (EUR)"])]
    charges = [5500] * 24   # Opex mensuel post-lancement (infra + support)
    for _, row in extra_costs.iterrows():
        try:
            m_idx = int(row["Mois"].replace("M", "")) - 1
            if 0 <= m_idx < 24:
                charges[m_idx] += row["Montant (EUR)"]
        except Exception:
            pass

    roi["rev_mensuel"]    = proj_rev
    roi["charges_mensuel"] = charges

    inv   = roi["investissement"]
    cumul = -inv
    be    = None
    for i, (r, ch) in enumerate(zip(proj_rev, charges)):
        cumul += r - ch
        if cumul >= 0 and be is None:
            be = i + 1

    roi["breakeven_mois"] = be
    roi["roi_global"]     = (sum(proj_rev) - inv - sum(charges)) / inv * 100
    roi["ca_annuel_1"]    = sum(proj_rev[:12])
    roi["ca_annuel_2"]    = sum(proj_rev[12:24])

    # ── En-tete ───────────────────────────────────────────────
    c_inv1, c_inv2 = st.columns([4, 1])
    c_inv1.markdown("# Dashboard Investisseurs — Book One")

    kpis_pdf = {
        "Investissement total": f"{roi['investissement']:,} EUR",
        "ROI global 24m":       f"{roi['roi_global']:.1f}%",
        "Break-even":           f"M{roi['breakeven_mois']}" if roi["breakeven_mois"] else "Non atteint",
        "CA An 1":              f"{roi['ca_annuel_1']:,} EUR",
        "Marge nette 24m":      f"{(sum(proj_rev) - inv - sum(charges)):,} EUR",
    }
    pdf_bytes = export_page_to_pdf(
        "Dashboard Investisseurs — Book One",
        kpis_pdf,
        tables=[("Projection CA Mensuel", ca_data), ("Postes Couts Additionnels", extra_costs)],
    )
    c_inv2.download_button(
        "Rapport PDF", data=pdf_bytes,
        file_name="Rapport_Investisseurs_BookOne.pdf", mime="application/pdf",
    )

    st.caption(
        f"Investissement : **{BUDGET_VALIDE:,} EUR** | "
        f"CA previsionnel : **{CA_PREVISIONNEL:,} EUR/an** | "
        "Modele de revenus : commission 1 EUR par transaction completee (remise en main propre confirmee)"
    )

    # ── KPIs investisseurs ────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Investissement total",
              f"{roi['investissement']:,} EUR".replace(",", " "),
              "Budget + provisions")
    k2.metric("CA an 1 (prevu)",
              f"{roi['ca_annuel_1']:,} EUR".replace(",", " "),
              f"+{roi['ca_annuel_2'] - roi['ca_annuel_1']:,} EUR en an 2")
    k3.metric("ROI global 24 mois", f"{roi['roi_global']:.1f}%")
    k4.metric("Break-even",
              f"M{roi['breakeven_mois']}" if roi["breakeven_mois"] else "> M24")
    k5.metric("Marge nette 24m",
              f"{(sum(proj_rev) - inv - sum(charges)):,} EUR".replace(",", " "))

    st.markdown("---")

    # ── Courbe ROI ────────────────────────────────────────────
    r1, r2 = st.columns([3, 2])
    with r1:
        st.markdown("#### Courbe ROI — revenus vs investissement (24 mois)")
        st.caption(
            "Modele : 1 EUR de revenu par transaction completee. "
            "Chaque remise en main propre confirmee = 1 EUR debite acheteur, credite Book One."
        )
        st.plotly_chart(build_roi_chart(roi), use_container_width=True)
    with r2:
        st.markdown("#### CA mensuel prevu vs reel")
        st.plotly_chart(build_ca_mensuel(sim, roi), use_container_width=True)

    st.markdown("---")

    # ── Courbe de Farmer ──────────────────────────────────────
    st.markdown("#### Matrice de risques — Courbe de Farmer")
    st.caption(
        "Points opaques = risques initiaux planifies | "
        "Croix vertes = risques survenus et resolus | "
        "Croix rouges = risques en cours | "
        "La courbe de Farmer delimite la zone ALARP (P x I = 8 000 EUR)"
    )
    st.plotly_chart(build_farmer_curve(sim), use_container_width=True)

    st.markdown("---")

    # ── Leviers & phasage ─────────────────────────────────────
    lv1, lv2 = st.columns([2, 3])
    with lv1:
        st.markdown("#### Leviers d'optimisation budgetaire")
        st.caption("Couleur = effort de mise en oeuvre (vert = faible, rouge = eleve)")
        st.plotly_chart(build_leviers_chart(), use_container_width=True)
        total_eco = 100 + 100 + 360 + 130 + 800 + 200 + 1400
        st.metric("Economie totale potentielle",
                  f"{total_eco:,} EUR".replace(",", " "),
                  f"{total_eco / BUDGET_VALIDE * 100:.1f}% du budget")

    with lv2:
        st.markdown("#### Phasage des depenses par mois (jan-avr 2025)")
        phasage = sim["phasage_mensuel"]
        mois    = [p["mois"] for p in phasage]

        fig_dep = go.Figure()
        for label, key_plan, key_reel, col in [
            ("RH",     "planifie_rh",   "reel_rh",   "#1E2761"),
            ("Hors-RH","planifie_hors", "reel_hors", "#378ADD"),
            ("Risques", None,           "risques_mois","#E24B4A"),
        ]:
            if key_plan:
                fig_dep.add_trace(go.Scatter(
                    x=mois, y=[p[key_plan] for p in phasage],
                    name=f"{label} planifie", mode="lines+markers",
                    line=dict(dash="dash", width=1.5, color=col),
                    marker=dict(size=6), opacity=0.6,
                ))
            fig_dep.add_trace(go.Scatter(
                x=mois, y=[p[key_reel] for p in phasage],
                name=f"{label} reel", mode="lines+markers",
                line=dict(width=2, color=col), marker=dict(size=8),
            ))
        fig_dep.update_layout(
            height=300,
            xaxis=dict(gridcolor="#E8EAF0"),
            yaxis=dict(title="EUR", gridcolor="#E8EAF0"),
            legend=dict(font_size=9, orientation="h", y=-0.25),
            margin=dict(l=10, r=10, t=10, b=70),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=11),
        )
        st.plotly_chart(fig_dep, use_container_width=True)

    st.markdown("---")

    # ── Previsionnel 12 mois ──────────────────────────────────
    st.markdown("#### Previsionnel couts, revenus et risques — vision mensuelle")
    mois_labels = [
        "Jan 2025", "Fev 2025", "Mar 2025", "Avr 2025",
        "Mai 2025", "Jun 2025", "Jul 2025", "Aou 2025",
        "Sep 2025", "Oct 2025", "Nov 2025", "Dec 2025",
    ]
    # Couts projet : 4 mois de dev actif, puis opex post-lancement
    cout_proj = [28000, 42000, 35000, 16000,
                 5500,  5500,  5500,  5500,
                 5500,  5500,  5500,  5500]
    rev_proj  = [0, 0, 0, 0,
                 500, 1200, 2500, 4000,
                 6000, 8000, 10000, 11500]
    rsq_proj  = [240, 3500, 700, 4600,
                 0, 0, 0, 0,
                 0, 0, 0, 0]

    cf_mensuel = [r - c - rs for r, c, rs in zip(rev_proj, cout_proj, rsq_proj)]
    cf_cumul   = []
    c_cum = -roi["investissement"]
    for cf in cf_mensuel:
        c_cum += cf
        cf_cumul.append(c_cum)

    roi_mens = [cf / roi["investissement"] * 100 for cf in cf_cumul]

    df_prev = pd.DataFrame({
        "Mois":            mois_labels,
        "Couts (EUR)":     cout_proj,
        "Revenus (EUR)":   rev_proj,
        "Risques (EUR)":   rsq_proj,
        "CF mensuel (EUR)": cf_mensuel,
        "CF cumule (EUR)": cf_cumul,
        "ROI cumule (%)":  [f"{r:.1f}%" for r in roi_mens],
    })

    def style_cf(row):
        if row["CF mensuel (EUR)"] > 0:
            return ["", "", "", "", "color:#1D9E75;font-weight:500", "", ""]
        if row["CF mensuel (EUR)"] < -5000:
            return ["", "", "", "", "color:#E24B4A", "", ""]
        return [""] * 7

    st.dataframe(
        df_prev.style.apply(style_cf, axis=1).format({
            "Couts (EUR)":      "{:,}",
            "Revenus (EUR)":    "{:,}",
            "Risques (EUR)":    "{:,}",
            "CF mensuel (EUR)": "{:+,}",
            "CF cumule (EUR)":  "{:+,}",
        }),
        use_container_width=True, hide_index=True,
    )
