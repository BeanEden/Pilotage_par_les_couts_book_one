"""
Page Budget Global & Risques — Book One MVP Mobile
Postes de coûts hors-RH adaptés au contexte startup (pas de GPU IA,
ajout API ISBN/FCM, publication stores, DPO RGPD géolocalisation).
Mois du projet : jan-fev 2025 (8 semaines).
"""

import streamlit as st
from persistence import save_state
import plotly.graph_objects as go
import pandas as pd
from copy import deepcopy
from simulation import (
    DUREE_SEMAINES, MOIS_PROJET, MOIS_SEMAINES, POIDS_MENSUEL,
    BUDGET_RH, BUDGET_VALIDE
)

# ─────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────

CATEGORIES_POSTES = [
    "Infrastructure & Cloud",
    "Licences & Logiciels",
    "Données & APIs",
    "Qualité & Tests",
    "Légal & Conformité",
    "Opérationnel",
    "Coûts cachés",
    "Provision & Risques",
    "Autre",
]

CAT_COLORS = {
    "Infrastructure & Cloud": "#378ADD",
    "Licences & Logiciels":   "#1D9E75",
    "Données & APIs":         "#BA7517",
    "Qualité & Tests":        "#D4537E",
    "Légal & Conformité":     "#7F77DD",
    "Opérationnel":           "#5F5E5A",
    "Coûts cachés":           "#993C1D",
    "Provision & Risques":    "#E24B4A",
    "Autre":                  "#B4B2A9",
    "Ressources Humaines":    "#1E2761",
}

PROB_OPTIONS   = ["Faible", "Moyenne", "Elevee"]
IMPACT_OPTIONS = ["Faible", "Moyen", "Eleve", "Tres eleve"]
TYPE_STRAT     = ["Prevention", "Mitigation", "Contingence", "Provision", "Optimisation"]
STRAT_COLORS   = {
    "Prevention":   "#1D9E75", "Mitigation":  "#BA7517",
    "Contingence":  "#7F77DD", "Provision":   "#E24B4A", "Optimisation": "#378ADD",
}
RISK_PALETTE = [
    "#E24B4A","#BA7517","#7F77DD","#1D9E75","#378ADD",
    "#D4537E","#534AB7","#5F5E5A","#993C1D","#185FA5",
]

# ─────────────────────────────────────────────────────────────
# POSTES HORS-RH PAR DÉFAUT — Book One
# GPU supprimé (hors scope MVP). Ajout API ISBN + notifications FCM.
# ─────────────────────────────────────────────────────────────

POSTES_DEFAULT = [
    {"categorie": "Infrastructure & Cloud", "sous_cat": "Hebergement Cloud",
     "description": "VM, Cloud Run, containers (staging + prod) sur 14 semaines",
     "retenu": 900, "ressources_rh": ["TL"],
     "justification": "2 environnements x 14 sem. sur GCP — startup tier"},
    {"categorie": "Infrastructure & Cloud", "sous_cat": "Base de donnees managee",
     "description": "PostgreSQL manage + stockage S3 (photos couvertures livres)",
     "retenu": 400, "ressources_rh": ["BE"],
     "justification": "PostgreSQL Cloud SQL 10 Go + bucket GCS images"},
    {"categorie": "Infrastructure & Cloud", "sous_cat": "CDN & Reseau",
     "description": "CDN images couvertures, bande passante API",
     "retenu": 150, "ressources_rh": [],
     "justification": "Cloudflare Free + bande passante beta limitee"},
    {"categorie": "Licences & Logiciels", "sous_cat": "Gestion de projet",
     "description": "Jira Software (9 utilisateurs x 14 semaines)",
     "retenu": 160, "ressources_rh": ["PM"],
     "justification": "Jira Cloud Standard ~8 EUR/user/mois x 9 x 3,5 mois"},
    {"categorie": "Licences & Logiciels", "sous_cat": "Outils de developpement",
     "description": "IDE, GitHub Team, outils CI/CD",
     "retenu": 140, "ressources_rh": ["TL", "BE", "MOB"],
     "justification": "GitHub Team + Actions minutes — forfait equipe"},
    {"categorie": "Licences & Logiciels", "sous_cat": "Outils de collaboration",
     "description": "Slack Pro, Figma Pro, Notion",
     "retenu": 220, "ressources_rh": ["PM", "UX"],
     "justification": "Slack Pro 9 users + Figma Pro UX x 4 mois"},
    {"categorie": "Licences & Logiciels", "sous_cat": "Outils de test",
     "description": "BrowserStack, Cypress Cloud — tests iOS/Android",
     "retenu": 180, "ressources_rh": ["QA", "ALT"],
     "justification": "BrowserStack Automate + Cypress Cloud — 14 semaines"},
    {"categorie": "Données & APIs", "sous_cat": "API ISBN — catalogue livres",
     "description": "Open Library API (gratuit) + Google Books API (quota eleve)",
     "retenu": 120, "ressources_rh": ["BE"],
     "justification": "Quota Google Books API eleve : ~120 EUR/mois x 1 mois de pic"},
    {"categorie": "Données & APIs", "sous_cat": "Notifications push (FCM/APNs)",
     "description": "Firebase Cloud Messaging (gratuit) + Apple Push Notification",
     "retenu": 0, "ressources_rh": ["BE"],
     "justification": "FCM gratuit jusqu'a 1M notifs/mois — pas de cout en beta"},
    {"categorie": "Données & APIs", "sous_cat": "Passerelle de paiement Stripe",
     "description": "Stripe sandbox — frais fixes dev et tests",
     "retenu": 50, "ressources_rh": ["FRL", "BE"],
     "justification": "Stripe sandbox gratuit — frais marginaux en beta"},
    {"categorie": "Données & APIs", "sous_cat": "Geolocalisation (Google Maps)",
     "description": "Google Maps SDK Mobile — affichage carte livres autour de moi",
     "retenu": 200, "ressources_rh": ["MOB"],
     "justification": "200 USD/mois de credit gratuit Google Maps — depassement marginal"},
    {"categorie": "Qualité & Tests", "sous_cat": "Audit securite paiement",
     "description": "Pentest flux Stripe + rapport conformite PCI-DSS simplifie",
     "retenu": 800, "ressources_rh": ["FRL"],
     "justification": "Rapport formel audit — complement mission freelance"},
    {"categorie": "Qualité & Tests", "sous_cat": "Monitoring erreurs",
     "description": "Sentry Team — monitoring erreurs app mobile + API",
     "retenu": 150, "ressources_rh": ["STG", "TL"],
     "justification": "Sentry Team 2 projets x 4 mois"},
    {"categorie": "Légal & Conformité", "sous_cat": "Conformite RGPD geolocalisation",
     "description": "Conseil DPO externe, redaction politique confidentialite, PIA geoloc",
     "retenu": 1200, "ressources_rh": [],
     "justification": "DPO externe 2 jours + documentation RGPD geoloc — risque eleve"},
    {"categorie": "Légal & Conformité", "sous_cat": "Licences open source",
     "description": "Audit licences open source — conformite MIT/Apache/GPL",
     "retenu": 100, "ressources_rh": ["STG"],
     "justification": "Outil FOSSA ou equivalant — verification automatisee"},
    {"categorie": "Légal & Conformité", "sous_cat": "Publication App Stores",
     "description": "Apple Developer Program + Google Play — frais annuels",
     "retenu": 125, "ressources_rh": ["MOB"],
     "justification": "Apple 99 USD/an + Google 25 USD one-shot"},
    {"categorie": "Opérationnel", "sous_cat": "Deplacements & reunions",
     "description": "Transports, salles de reunion, reunions equipe/CEO",
     "retenu": 300, "ressources_rh": ["PM"],
     "justification": "Estime 2 deplacements/mois x 4 mois — startup parisienne"},
    {"categorie": "Opérationnel", "sous_cat": "Formation",
     "description": "Formation Flutter, securite paiement mobile",
     "retenu": 500, "ressources_rh": ["MOB", "BE"],
     "justification": "1 formation Flutter + 1 atelier securite paiement"},
    {"categorie": "Opérationnel", "sous_cat": "Communication projet",
     "description": "Reunions de pilotage, outils de reporting",
     "retenu": 100, "ressources_rh": ["PM"],
     "justification": "Couts marginaux — tableaux de bord internes"},
    {"categorie": "Provision & Risques", "sous_cat": "Enveloppe de risque",
     "description": "Provision pour aleas techniques, retards, surcouts imprevus",
     "retenu": 1500, "ressources_rh": [],
     "justification": "~20% du budget hors-RH — prudence pour un MVP startup"},
]

RISQUES_DEFAULT = [
    {
        "id": "R1", "titre": "Retard sur le chemin critique",
        "description": (
            "Blocage sur T5 (API Auth), T8 (catalogue geo), T14 (logique credit) ou T15 (Stripe) "
            "— chaque semaine de retard = charges supplementaires."
        ),
        "probabilite": "Moyenne", "impact": "Eleve", "provision": 18000, "couleur": "#E24B4A",
        "strategies": [
            {"titre": "Buffer de planning (+2 semaines)", "type": "Prevention", "budget": 12000,
             "description": "Integrer 2 semaines de marge dans le planning officiel."},
            {"titre": "Renforcement ponctuel freelance", "type": "Mitigation", "budget": 6000,
             "description": "Contrat de reserve avec un dev back-end senior activable sous 48h."},
            {"titre": "Decoupage en livrables partiels", "type": "Contingence", "budget": 0,
             "description": "Preparer une version sans messagerie ni wishes si retard > 2 sem."},
        ],
    },
    {
        "id": "R2", "titre": "Rejet App Store (Apple)",
        "description": (
            "Apple refuse la beta : achat conditionnel a 1 EUR, scan ISBN ou politique donnees "
            "geoloc non conformes aux guidelines. Chaque cycle = 1 a 2 semaines."
        ),
        "probabilite": "Moyenne", "impact": "Moyen", "provision": 5000, "couleur": "#BA7517",
        "strategies": [
            {"titre": "Revue guidelines Apple (S10)", "type": "Prevention", "budget": 300,
             "description": "Audit interne Apple HIG + politique achats in-app a S10."},
            {"titre": "Distribution TestFlight en beta", "type": "Contingence", "budget": 0,
             "description": "TestFlight pour la beta interne — contourne la validation store."},
            {"titre": "Provision corrections store", "type": "Provision", "budget": 4700,
             "description": "2 cycles de correction (Dev Mobile 5j + QA 3j)."},
        ],
    },
    {
        "id": "R3", "titre": "Non-conformite RGPD — geolocalisation",
        "description": (
            "La collecte de la position GPS des utilisateurs expose Book One a un risque RGPD eleve "
            "(PIA obligatoire, DPO, base legale). Amende potentielle CNIL."
        ),
        "probabilite": "Faible", "impact": "Tres eleve", "provision": 12000, "couleur": "#7F77DD",
        "strategies": [
            {"titre": "Privacy by Design des T1", "type": "Prevention", "budget": 500,
             "description": "Integrer exigences RGPD dans specs T3 et architecture T1."},
            {"titre": "PIA geoloc en S2", "type": "Mitigation", "budget": 1200,
             "description": "Realiser le PIA avec DPO externe des la S2 pour ne pas bloquer."},
            {"titre": "Provision correction architecture", "type": "Provision", "budget": 10000,
             "description": "Reserve si refonte partielle du modele de donnees geoloc."},
        ],
    },
    {
        "id": "R4", "titre": "Depart d'une ressource cle",
        "description": "Tech Lead ou Dev Back-End (>35 j/h sur chemin critique) indisponible.",
        "probabilite": "Faible", "impact": "Eleve", "provision": 7000, "couleur": "#1D9E75",
        "strategies": [
            {"titre": "Contrat freelance de back-up", "type": "Prevention", "budget": 200,
             "description": "Pre-qualifier un freelance back-end disponible sous 1 semaine."},
            {"titre": "Documentation continue (T27)", "type": "Prevention", "budget": 0,
             "description": "Couvrir tous les choix d'architecture pour un onboarding rapide."},
            {"titre": "Provision remplacement", "type": "Provision", "budget": 6800,
             "description": "8 jours de freelance senior en urgence (850 EUR/j x 8j)."},
        ],
    },
    {
        "id": "R5", "titre": "Fraude sur le mecanisme de credit 1 EUR",
        "description": (
            "Un utilisateur cree de faux comptes pour simuler des scans et obtenir des credits d'achat "
            "sans deposer de livres reels. Impact financier + reputationnel."
        ),
        "probabilite": "Moyenne", "impact": "Moyen", "provision": 3000, "couleur": "#378ADD",
        "strategies": [
            {"titre": "Verification ISBN reel (Open Library)", "type": "Prevention", "budget": 200,
             "description": "Valider que l'ISBN scanne existe dans la base Open Library."},
            {"titre": "Limite de credits par compte / periode", "type": "Mitigation", "budget": 0,
             "description": "Plafond de 3 credits/mois par compte en phase beta."},
            {"titre": "Provision pertes fraude beta", "type": "Provision", "budget": 2800,
             "description": "Reserve pour absorber les transactions frauduleuses en beta."},
        ],
    },
]

# ─────────────────────────────────────────────────────────────
# GRAPHIQUES (repris tels quels — generiques)
# ─────────────────────────────────────────────────────────────

def build_donut(postes, budget_rh, selected_cats=None):
    cats = {"Ressources Humaines": budget_rh}
    for p in postes:
        cats[p["categorie"]] = cats.get(p["categorie"], 0) + p["retenu"]
    
    if selected_cats:
        cats = {k: v for k, v in cats.items() if k in selected_cats}
        if not cats:
            return go.Figure()

    colors = [CAT_COLORS.get(c, "#888") for c in cats]
    fig = go.Figure(go.Pie(
        labels=list(cats.keys()), values=list(cats.values()),
        hole=0.52, marker=dict(colors=colors),
        hovertemplate="%{label}<br>%{value:,} EUR (%{percent})<extra></extra>",
        textinfo="percent", textfont_size=11,
    ))
    fig.update_layout(height=340, margin=dict(l=5, r=5, t=10, b=10),
                      paper_bgcolor="rgba(0,0,0,0)",
                      legend=dict(font_size=10), font=dict(size=11))
    return fig


def build_weekly_histogram(postes, budget_rh, selected_cats=None):
    """Histogramme des coûts par semaine (14 semaines)."""
    cats_all = ["Ressources Humaines"] + list(dict.fromkeys(p["categorie"] for p in postes))
    totaux   = {"Ressources Humaines": budget_rh}
    for p in postes:
        totaux[p["categorie"]] = totaux.get(p["categorie"], 0) + p["retenu"]
    
    if selected_cats:
        cats_to_plot = [c for c in cats_all if c in selected_cats]
    else:
        cats_to_plot = cats_all

    fig = go.Figure()
    
    # On distribue le budget mensuel sur les semaines
    sems = list(range(1, 15))
    labels_sems = [f"S{s}" for s in sems]
    
    for cat in cats_to_plot:
        total_cat = totaux.get(cat, 0)
        poids_mois = POIDS_MENSUEL.get(cat, [0.25, 0.25, 0.25, 0.25])
        
        vals_sem = [0] * 14
        for i_mois, mois in enumerate(MOIS_PROJET):
            s_deb, s_fin = MOIS_SEMAINES[mois]
            nb_sems = s_fin - s_deb + 1
            cout_mensuel = total_cat * poids_mois[i_mois]
            cout_hebdo = cout_mensuel / nb_sems
            for s in range(s_deb, s_fin + 1):
                vals_sem[s-1] = cout_hebdo
        
        col = CAT_COLORS.get(cat, "#888")
        fig.add_trace(go.Bar(
            name=cat, x=labels_sems, y=vals_sem, marker_color=col,
            hovertemplate="<b>%{x}</b><br>"+f"{cat}<br>"+"Montant : %{y:,.0f} EUR<extra></extra>",
        ))

    fig.update_layout(
        barmode="stack", height=340,
        xaxis=dict(title="Semaine"),
        yaxis=dict(title="EUR", gridcolor="#E8EAF0"),
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=11), legend=dict(orientation="h", y=-0.2, font_size=10),
    )
    return fig


def build_postes_chart(postes, budget_rh, filtre_cat="Toutes"):
    """Bar chart horizontal des postes — filtrable par catégorie."""
    fig = go.Figure()

    if filtre_cat in ("Toutes", "Ressources Humaines"):
        equipe = st.session_state.get("equipe", [])
        from data import calcul_taux_jour
        from calculs import calcul_cout_tache
        taches = st.session_state.get("taches", [])
        eq_idx = {m["id"]: m for m in equipe}
        jps    = st.session_state.get("config", {}).get("jours_par_semaine", 5)

        if filtre_cat == "Ressources Humaines" and equipe:
            par_res = {}
            for t in taches:
                rid = t["res"]
                par_res[rid] = par_res.get(rid, 0) + calcul_cout_tache(t, eq_idx, jps)
            for rid, cout in sorted(par_res.items(), key=lambda x: -x[1]):
                m   = eq_idx.get(rid, {})
                lbl = m.get("label", rid)
                col = "#" + m.get("couleur", "1E2761")
                fig.add_trace(go.Bar(
                    y=[lbl], x=[cout], orientation="h", marker_color=col,
                    text=[f"{int(cout):,} EUR"], textposition="outside",
                    name=lbl, showlegend=False,
                    hovertemplate=f"<b>{lbl}</b><br>{int(cout):,} EUR<extra></extra>",
                ))
        else:
            fig.add_trace(go.Bar(
                y=["Ressources Humaines"], x=[budget_rh], orientation="h",
                marker_color="#1E2761",
                text=[f"{budget_rh:,} EUR"], textposition="outside",
                name="RH", showlegend=False,
                hovertemplate=f"<b>Ressources Humaines</b><br>{budget_rh:,} EUR<extra></extra>",
            ))

    postes_filtres = [p for p in postes
                      if filtre_cat == "Toutes" or p["categorie"] == filtre_cat]
    postes_tries   = sorted(postes_filtres, key=lambda p: -p["retenu"])

    for p in postes_tries:
        col     = CAT_COLORS.get(p["categorie"], "#888")
        res_lbl = ", ".join(p.get("ressources_rh", [])) or "—"
        fig.add_trace(go.Bar(
            y=[p["sous_cat"]], x=[p["retenu"]], orientation="h",
            marker_color=col,
            text=[f"{p['retenu']:,} EUR"], textposition="outside",
            name=p["sous_cat"], showlegend=False,
            hovertemplate=(
                f"<b>{p['sous_cat']}</b><br>"
                f"Categorie : {p['categorie']}<br>"
                f"Montant : {p['retenu']:,} EUR<br>"
                f"Ressources RH : {res_lbl}<br>"
                f"{p['description']}<extra></extra>"
            ),
        ))

    nb  = len(postes_tries) + (1 if filtre_cat != "Ressources Humaines" else 0)
    hgt = max(280, nb * 36 + 60)
    fig.update_layout(
        barmode="group", height=hgt,
        xaxis=dict(title="EUR", gridcolor="#E8EAF0"),
        yaxis=dict(title="", tickfont=dict(size=10)),
        margin=dict(l=10, r=90, t=10, b=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=11), showlegend=False,
        uniformtext=dict(mode="hide", minsize=9),
    )
    return fig


def build_weekly_budget_df(postes, budget_rh):
    """Génère un tableau des coûts par catégorie et par semaine."""
    cats_all = ["Ressources Humaines"] + CATEGORIES_POSTES
    totaux = {"Ressources Humaines": budget_rh}
    for p in postes:
        totaux[p["categorie"]] = totaux.get(p["categorie"], 0) + p["retenu"]
    
    rows = []
    for cat in cats_all:
        total_cat = totaux.get(cat, 0)
        poids_mois = POIDS_MENSUEL.get(cat, [0.5, 0.5])
        
        row = {"Catégorie": cat}
        for i_mois, mois in enumerate(MOIS_PROJET):
            s_deb, s_fin = MOIS_SEMAINES[mois]
            nb_sems = s_fin - s_deb + 1
            cout_hebdo = (total_cat * poids_mois[i_mois]) / nb_sems
            for s in range(s_deb, s_fin + 1):
                row[f"S{s}"] = int(cout_hebdo)
        
        row["TOTAL (€)"] = int(total_cat)
        rows.append(row)
    
    return pd.DataFrame(rows)


def build_phasage_chart(postes, budget_rh):
    """Bar chart empilé du phasage budgétaire mensuel (jan-fev 2025)."""
    cats_all = ["Ressources Humaines"] + list(dict.fromkeys(p["categorie"] for p in postes))
    totaux   = {"Ressources Humaines": budget_rh}
    for p in postes:
        totaux[p["categorie"]] = totaux.get(p["categorie"], 0) + p["retenu"]

    fig = go.Figure()
    for cat in cats_all:
        total_cat = totaux.get(cat, 0)
        poids     = POIDS_MENSUEL.get(cat, [0.5, 0.5])
        vals_mois = [total_cat * w for w in poids]
        col       = CAT_COLORS.get(cat, "#888")
        fig.add_trace(go.Bar(
            name=cat, x=MOIS_PROJET, y=vals_mois, marker_color=col,
            hovertemplate=(
                "<b>%{x}</b><br>"
                f"{cat}<br>"
                "Montant : %{y:,.0f} EUR<extra></extra>"
            ),
            text=[f"{v:,.0f}" for v in vals_mois],
            textposition="inside",
            textfont=dict(size=8, color="white"),
        ))

    totaux_mois = [
        sum(totaux.get(cat, 0) * POIDS_MENSUEL.get(cat, [0.25]*4)[i] for cat in cats_all)
        for i in range(4)
    ]
    fig.add_trace(go.Scatter(
        x=MOIS_PROJET, y=totaux_mois, mode="lines+markers+text",
        name="Total", line=dict(color="#12182B", width=2.5, dash="dot"),
        marker=dict(size=9), text=[f"{v:,.0f}" for v in totaux_mois],
        textposition="top center", textfont=dict(size=9, color="#12182B"),
        hovertemplate="<b>%{x}</b> — Total : %{y:,.0f} EUR<extra></extra>",
    ))
    fig.update_layout(
        barmode="stack", height=360,
        xaxis=dict(title="Mois"),
        yaxis=dict(title="EUR", gridcolor="#E8EAF0"),
        legend=dict(orientation="h", y=-0.25, font_size=9),
        margin=dict(l=10, r=10, t=10, b=100),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=11),
    )
    return fig


def build_risques_matrix(risques):
    """Matrice probabilité × impact avec bulles (taille = provision)."""
    prob_map   = {"Faible": 1, "Moyenne": 2, "Elevee": 3}
    impact_map = {"Faible": 1, "Moyen": 2, "Eleve": 3, "Tres eleve": 4}

    fig = go.Figure()
    # Zones de couleur
    for x0, x1, y0, y1, col in [
        (0.5, 1.5, 0.5, 2.5, "rgba(29,158,117,0.10)"),
        (0.5, 2.5, 0.5, 1.5, "rgba(29,158,117,0.10)"),
        (1.5, 2.5, 1.5, 2.5, "rgba(186,117,23,0.10)"),
        (0.5, 1.5, 2.5, 4.5, "rgba(186,117,23,0.10)"),
        (2.5, 3.5, 0.5, 2.5, "rgba(186,117,23,0.10)"),
        (1.5, 3.5, 2.5, 4.5, "rgba(226,75,74,0.12)"),
        (2.5, 3.5, 2.5, 4.5, "rgba(226,75,74,0.18)"),
    ]:
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                      fillcolor=col, line_width=0, layer="below")

    for r in risques:
        px = prob_map.get(r["probabilite"], 1)
        py = impact_map.get(r["impact"], 1)
        sz = max(20, min(50, r["provision"] / 500))
        fig.add_trace(go.Scatter(
            x=[px], y=[py], mode="markers+text",
            marker=dict(size=sz, color=r["couleur"], opacity=0.75,
                        line=dict(color=r["couleur"], width=2)),
            text=[r["id"]], textposition="middle center",
            textfont=dict(size=9, color="white"),
            name=r["id"],
            hovertemplate=(
                f"<b>{r['id']} — {r['titre']}</b><br>"
                f"Proba : {r['probabilite']} | Impact : {r['impact']}<br>"
                f"Provision : {r['provision']:,} EUR<extra></extra>"
            ),
        ))

    fig.update_layout(
        height=320,
        xaxis=dict(title="Probabilite", tickvals=[1,2,3],
                   ticktext=["Faible","Moyenne","Elevee"], range=[0.3, 3.7]),
        yaxis=dict(title="Impact", tickvals=[1,2,3,4],
                   ticktext=["Faible","Moyen","Eleve","Tres eleve"], range=[0.3, 4.7]),
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=11), showlegend=False,
    )
    return fig


def _build_leviers():
    """Leviers d'optimisation budgétaire contextualisés Book One."""
    return [
        {"levier": "Passer FCM en tier gratuit (deja 0 EUR)", "economie": 0,  "effort": "Faible",  "cat": "Données & APIs"},
        {"levier": "Figma Free a la place de Figma Pro",       "economie": 100, "effort": "Faible",  "cat": "Licences & Logiciels"},
        {"levier": "Remplacer Jira par Linear (startup plan)", "economie": 100, "effort": "Faible",  "cat": "Licences & Logiciels"},
        {"levier": "Instances Cloud preemptibles (-40%)",      "economie": 360, "effort": "Moyen",   "cat": "Infrastructure & Cloud"},
        {"levier": "Remplacer BrowserStack par emulateurs",    "economie": 130, "effort": "Moyen",   "cat": "Qualité & Tests"},
        {"levier": "DPO interne vs externe",                   "economie": 800, "effort": "Eleve",   "cat": "Légal & Conformité"},
        {"levier": "Alternant sur monitoring vs STG",          "economie": 200, "effort": "Faible",  "cat": "Ressources Humaines"},
        {"levier": "Reduction scope Wishes a V2",              "economie": 1400,"effort": "Moyen",   "cat": "Ressources Humaines"},
        {"levier": "Remplacer Dev Backend Expert par Junior",  "economie": 6500, "effort": "Eleve",  "cat": "Ressources Humaines"},
    ]


def build_weekly_balance_df(risques, leviers):
    """Calcule la balance Risques vs Leviers par semaine."""
    # Mapping temporel des risques (simplifié pour démo)
    risk_weeks = {
        "R1": list(range(3, 8)),  # Paiement/Géo
        "R2": list(range(1, 9)),  # Retards CEO
        "R3": list(range(6, 9)),  # Tests
        "R4": list(range(2, 9)),  # Freelance
    }
    
    sems = [f"S{i}" for i in range(1, 15)]
    rows = []
    
    # Ligne Risques
    row_risks = {"Indicateur": "⚠️ Coût Provision Risques (EUR)"}
    for s in sems: row_risks[s] = 0
    for r in risques:
        w_list = risk_weeks.get(r["id"], list(range(1, 9)))
        prov_hebdo = r["provision"] / len(w_list)
        for w in w_list:
            if f"S{w}" in row_risks: row_risks[f"S{w}"] += prov_hebdo
    rows.append(row_risks)
    
    # Ligne Leviers
    row_leviers = {"Indicateur": "💡 Gains Optimisation (EUR)"}
    for s in sems: row_leviers[s] = 0
    for l in leviers:
        # On spread l'économie sur les 14 semaines
        eco_hebdo = l["economie"] / 14
        for s in sems:
            row_leviers[s] += eco_hebdo
    rows.append(row_leviers)
    
    # Ligne Solde
    row_solde = {"Indicateur": "⚖️ SOLDE NET (Risque - Levier)"}
    for s in sems:
        row_solde[s] = row_risks[s] - row_leviers[s]
    rows.append(row_solde)
    
    df = pd.DataFrame(rows)
    # Ajouter TOTAL
    df["TOTAL"] = df.iloc[:, 1:].sum(axis=1)
    return df


def build_leviers_chart():
    leviers = _build_leviers()
    leviers = sorted(leviers, key=lambda x: -x["economie"])
    col_eff = {"Faible": "#1D9E75", "Moyen": "#BA7517", "Eleve": "#E24B4A"}
    fig = go.Figure(go.Bar(
        x=[l["economie"] for l in leviers],
        y=[l["levier"] for l in leviers],
        orientation="h",
        marker_color=[col_eff.get(l["effort"], "#888") for l in leviers],
        text=[f"{l['economie']:,} EUR" for l in leviers],
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Economie : %{x:,.0f} EUR<extra></extra>"
        ),
    ))
    fig.update_layout(
        height=320,
        xaxis=dict(title="Economie potentielle (EUR)", gridcolor="#E8EAF0"),
        yaxis=dict(title="", tickfont=dict(size=9)),
        margin=dict(l=10, r=90, t=10, b=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=11), showlegend=False,
        uniformtext=dict(mode="hide", minsize=8),
    )
    return fig


def _save_budget():
    """Persistance après modification des postes ou des risques."""
    save_state({
        "taches":       st.session_state.get("taches", []),
        "equipe":       st.session_state.get("equipe", []),
        "config":       st.session_state.get("config", {}),
        "postes_couts": st.session_state.get("postes_couts"),
        "risques":      st.session_state.get("risques"),
    })


# ─────────────────────────────────────────────────────────────
# RENDER PRINCIPAL
# ─────────────────────────────────────────────────────────────

def render_budget_global():
    st.markdown("# Budget Global & Risques — Book One")
    st.caption(
        "Vision complete du budget projet : RH + hors-RH + provisions risques. "
        "Les postes hors-RH sont modifiables et lies au dashboard financier."
    )

    # Initialisation session_state
    if st.session_state.get("postes_couts") is None:
        st.session_state.postes_couts = deepcopy(POSTES_DEFAULT)
    if st.session_state.get("risques") is None:
        st.session_state.risques = deepcopy(RISQUES_DEFAULT)

    postes = st.session_state.postes_couts
    risques = st.session_state.risques

    # Budget RH dynamique
    from calculs import calcul_cout_tache
    taches  = st.session_state.get("taches", [])
    equipe  = st.session_state.get("equipe", [])
    eq_idx  = {m["id"]: m for m in equipe}
    jps     = st.session_state.get("config", {}).get("jours_par_semaine", 5)
    budget_rh = int(sum(calcul_cout_tache(t, eq_idx, jps) for t in taches)) or BUDGET_RH

    total_hors_rh     = sum(p["retenu"] for p in postes)
    total_global      = budget_rh + total_hors_rh
    total_provisions  = sum(r["provision"] for r in risques)
    total_avec_risques = total_global + total_provisions

    # ── KPIs budget ──────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Budget RH", f"{budget_rh:,} EUR".replace(",", " "),
              f"{budget_rh/total_global*100:.0f}% du total" if total_global else "")
    k2.metric("Hors-RH", f"{total_hors_rh:,} EUR".replace(",", " "),
              f"{len(postes)} postes")
    k3.metric("Budget de base", f"{total_global:,} EUR".replace(",", " "))
    k4.metric("Budget + provisions", f"{total_avec_risques:,} EUR".replace(",", " "),
              f"+{total_provisions:,} EUR risques")

    st.markdown("---")

    # ── Section 1 : Synthèse graphique ───────────────────────
    st.markdown("## 1 - Répartition budgétaire")
    
    cats_all = ["Ressources Humaines"] + CATEGORIES_POSTES
    sel_cats = st.multiselect("Filtrer par catégories (Donut & Hebdo)", options=cats_all, 
                             default=cats_all, key="bg_multiselect_cats")
    
    c1, c2 = st.columns([2, 3])
    with c1:
        st.markdown("**Répartition par catégorie**")
        st.plotly_chart(build_donut(postes, budget_rh, sel_cats), use_container_width=True)
    with c2:
        st.markdown("**Échéancier hebdomadaire des coûts**")
        st.plotly_chart(build_weekly_histogram(postes, budget_rh, sel_cats), use_container_width=True)

    st.markdown("---")

    # ── Section 2 : Postes hors-RH ───────────────────────────
    st.markdown("## 2 - Postes hors-RH")
    cats_dispo = ["Toutes", "Ressources Humaines"] + CATEGORIES_POSTES
    filtre_cat = st.selectbox("Filtrer par categorie", cats_dispo, key="bg_filtre_cat")
    st.plotly_chart(build_postes_chart(postes, budget_rh, filtre_cat), use_container_width=True)

    # Tableau des postes
    with st.expander("Tableau detail des postes hors-RH", expanded=False):
        df_postes = pd.DataFrame([{
            "Categorie":   p["categorie"],
            "Poste":       p["sous_cat"],
            "Montant (EUR)": p["retenu"],
            "Ressources":  ", ".join(p.get("ressources_rh", [])) or "—",
            "Justification": p.get("justification", ""),
        } for p in postes])
        st.dataframe(df_postes.sort_values("Montant (EUR)", ascending=False),
                     use_container_width=True, hide_index=True)

    # Ajout / modification de postes
    with st.expander("Ajouter ou modifier un poste", expanded=False):
        pa1, pa2, pa3 = st.columns(3)
        new_cat  = pa1.selectbox("Categorie", CATEGORIES_POSTES, key="np_cat")
        new_sc   = pa1.text_input("Sous-categorie", key="np_sc")
        new_desc = pa2.text_area("Description", key="np_desc", height=68)
        new_mont = pa3.number_input("Montant (EUR)", 0, 100_000, 0, step=50, key="np_mont")
        new_just = pa3.text_input("Justification", key="np_just")
        if st.button("Ajouter le poste", type="primary", key="btn_add_poste"):
            if new_sc.strip():
                st.session_state.postes_couts.append({
                    "categorie":    new_cat,
                    "sous_cat":     new_sc.strip(),
                    "description":  new_desc.strip(),
                    "retenu":       int(new_mont),
                    "ressources_rh": [],
                    "justification": new_just.strip(),
                })
                _save_budget()
                st.rerun()
            else:
                st.error("La sous-categorie est obligatoire.")

    st.markdown("---")

    # ── Section 3 : Phasage hebdomadaire ─────────────────────
    st.markdown("## 3 - Phasage budgétaire hebdomadaire (EUR)")
    df_phasage = build_weekly_budget_df(postes, budget_rh)
    
    # Ajout d'une ligne de total
    df_total = df_phasage.select_dtypes(include=['number']).sum()
    df_total["Catégorie"] = "TOTAL GÉNÉRAL"
    df_phasage = pd.concat([df_phasage, pd.DataFrame([df_total])], ignore_index=True)
    
    # Application du style Heatmap
    cols_sems = [f"S{s}" for s in range(1, DUREE_SEMAINES + 1)]
    styled_df = df_phasage.style.background_gradient(
        cmap='Oranges', subset=cols_sems
    ).format(
        {c: "{:,.0f}" for c in cols_sems + ["TOTAL (€)"]}
    )

    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    # ── Section 4 : Leviers d'optimisation ───────────────────
    st.markdown("## 4 - Leviers d'optimisation")
    leviers = _build_leviers()
    st.plotly_chart(build_leviers_chart(), use_container_width=True)

    df_lev = pd.DataFrame([{
        "Levier":        l["levier"],
        "Economie (EUR)": l["economie"],
        "Effort":        l["effort"],
        "Categorie":     l["cat"],
    } for l in sorted(leviers, key=lambda x: -x["economie"])])
    effort_col = {"Faible": "color:#1D9E75", "Moyen": "color:#BA7517", "Eleve": "color:#E24B4A"}
    def style_lev(row):
        ec = effort_col.get(row["Effort"], "")
        return ["", "", ec, ""]
    st.dataframe(
        df_lev.style.apply(style_lev, axis=1).format({"Economie (EUR)": "{:,}"}),
        use_container_width=True, hide_index=True,
    )
    st.markdown("### Balance Risques vs Leviers d'Optimisation")
    st.caption("Vision hebdomadaire de l'exposition aux risques contrebalancée par les leviers d'économie.")
    
    df_balance = build_weekly_balance_df(risques, leviers)
    cols_sems = [f"S{s}" for s in range(1, 15)]
    
    # Style conditionnel : Vert pour économie, Rouge pour risque
    def style_balance(val):
        if isinstance(val, (int, float)):
            if val > 0: return "color: #E24B4A" # Risque (positif car provision)
            if val < 0: return "color: #1D9E75" # Gain (négatif car économie)
        return ""

    # Pour le solde net on veut une heatmap
    # On inverse pour le solde net : positif = danger (rouge), négatif = sécurité (vert)
    styled_balance = df_balance.style.map(style_balance, subset=cols_sems + ["TOTAL"])\
        .background_gradient(cmap="RdYlGn_r", subset=pd.IndexSlice[2, cols_sems])\
        .format({c: "{:,.0f}" for c in cols_sems + ["TOTAL"]})

    st.dataframe(styled_balance, use_container_width=True, hide_index=True)

    eco_faible = sum(l["economie"] for l in leviers if l["effort"] == "Faible")
    eco_moyen  = sum(l["economie"] for l in leviers if l["effort"] in ("Faible", "Moyen"))
    st.info(
        f"L'application des leviers d'effort faible permet de couvrir **{eco_faible:,} EUR** de risques. "
        f"Le solde net hebdomadaire (ligne 3) indique ton exposition réelle résiduelle.",
        icon="⚖️",
    )

    st.markdown("---")

    # ── Section 5 : Risques ───────────────────────────────────
    st.markdown("## 5 - Risques pouvant impacter le budget")
    st.caption(f"{len(risques)} risques identifies")

    with st.expander("Ajouter un risque", expanded=False):
        ra1, ra2 = st.columns(2)
        nr_titre = ra1.text_input("Titre du risque", key="nr_titre")
        nr_prob  = ra2.selectbox("Probabilite", PROB_OPTIONS, key="nr_prob")
        ra3, ra4 = st.columns(2)
        nr_imp   = ra3.selectbox("Impact", IMPACT_OPTIONS, key="nr_imp")
        nr_prov  = ra4.number_input("Provision (EUR)", 0, 500_000, 5000, step=500, key="nr_prov")
        nr_desc  = st.text_area("Description", key="nr_desc", height=68)
        n_strats = st.number_input("Nombre de strategies", 1, 5, 3, key="nr_n_strats")
        strats_new = []
        for si in range(int(n_strats)):
            s1, s2, s3 = st.columns([2, 1, 1])
            s_titre  = s1.text_input(f"Strategie {si+1}", key=f"ns_{si}_titre")
            s_type   = s2.selectbox("Type", TYPE_STRAT, key=f"ns_{si}_type")
            s_budget = s3.number_input("Budget (EUR)", -100_000, 500_000, 0, step=100, key=f"ns_{si}_budget")
            s_desc   = st.text_input(f"Description {si+1}", key=f"ns_{si}_desc")
            strats_new.append({
                "titre": s_titre.strip() or f"Strategie {si+1}",
                "type": s_type, "budget": int(s_budget),
                "description": s_desc.strip() or "—",
            })
        cb1, cb2 = st.columns([1, 4])
        if cb1.button("Ajouter", type="primary", key="btn_add_risk"):
            if not nr_titre.strip():
                cb2.error("Titre obligatoire.")
            else:
                ids    = {r["id"] for r in risques}
                n_id   = len(risques) + 1
                new_id = f"R{n_id}"
                while new_id in ids:
                    n_id += 1; new_id = f"R{n_id}"
                st.session_state.risques.append({
                    "id": new_id, "titre": nr_titre.strip(),
                    "description": nr_desc.strip(),
                    "probabilite": nr_prob, "impact": nr_imp,
                    "provision": int(nr_prov),
                    "couleur": RISK_PALETTE[len(risques) % len(RISK_PALETTE)],
                    "strategies": strats_new,
                })
                _save_budget()
                st.rerun()

    st.markdown("### Matrice Probabilite x Impact")
    st.plotly_chart(build_risques_matrix(risques), use_container_width=True)

    prob_icon   = {"Faible": "🟢", "Moyenne": "🟡", "Elevee": "🔴"}
    impact_icon = {"Faible": "🟢", "Moyen": "🟡", "Eleve": "🔴", "Tres eleve": "🔴"}
    to_del_risk = None

    for ri, r in enumerate(risques):
        pi    = prob_icon.get(r["probabilite"], "⚪")
        ii    = impact_icon.get(r["impact"], "⚪")
        rcol  = r["couleur"]
        st.markdown(
            f"<div style='border-left:4px solid {rcol};padding:6px 12px;"
            f"background:var(--color-background-secondary);"
            f"border-radius:0 8px 8px 0;margin-bottom:4px'>"
            f"<span style='font-size:15px;font-weight:500;color:{rcol}'>"
            f"{r['id']} — {r['titre']}</span>&nbsp;&nbsp;"
            f"{pi} {r['probabilite']} &nbsp;|&nbsp; {ii} {r['impact']} &nbsp;|&nbsp; "
            f"<b>Provision : {r['provision']:,} EUR</b></div>",
            unsafe_allow_html=True,
        )
        with st.expander("Detail & strategies", expanded=False):
            st.markdown(f"**Description :** {r['description']}")
            ed1, ed2, ed3, ed4 = st.columns([2, 1, 1, 1])
            new_prob = ed1.selectbox("Probabilite", PROB_OPTIONS,
                index=PROB_OPTIONS.index(r["probabilite"]) if r["probabilite"] in PROB_OPTIONS else 0,
                key=f"r{ri}_prob")
            new_imp  = ed2.selectbox("Impact", IMPACT_OPTIONS,
                index=IMPACT_OPTIONS.index(r["impact"]) if r["impact"] in IMPACT_OPTIONS else 0,
                key=f"r{ri}_imp")
            new_prov = ed3.number_input("Provision (EUR)", 0, 500_000,
                value=r["provision"], step=500, key=f"r{ri}_prov")
            if ed4.button("Mettre a jour", key=f"r{ri}_upd"):
                st.session_state.risques[ri].update({
                    "probabilite": new_prob, "impact": new_imp, "provision": int(new_prov)
                })
                _save_budget(); st.rerun()
            st.markdown("**Strategies :**")
            for strat in r.get("strategies", []):
                tc  = STRAT_COLORS.get(strat["type"], "#888")
                bgt = (f"Economie : {abs(strat['budget']):,} EUR" if strat["budget"] < 0
                       else f"Budget : {strat['budget']:,} EUR" if strat["budget"] > 0
                       else "Sans surcout")
                st.markdown(
                    f"<div style='margin:4px 0;padding:7px 12px;"
                    f"background:var(--color-background-primary);"
                    f"border:1px solid var(--color-border-tertiary);border-radius:8px'>"
                    f"<span style='background:{tc};color:white;font-size:10px;"
                    f"font-weight:500;padding:2px 8px;border-radius:10px'>{strat['type']}</span>"
                    f"&nbsp;<b>{strat['titre']}</b> — <i>{bgt}</i><br>"
                    f"<span style='font-size:12px;color:var(--color-text-secondary)'>"
                    f"{strat['description']}</span></div>",
                    unsafe_allow_html=True,
                )
            if st.button(f"Supprimer {r['id']}", key=f"r{ri}_del"):
                to_del_risk = ri

    if to_del_risk is not None:
        st.session_state.risques.pop(to_del_risk)
        _save_budget(); st.rerun()

    # Section 6 — Synthèse risques
    st.markdown("## 6 - Budget des strategies de gestion des risques")
    rows_rb = [{"Risque": r["id"], "Strategie": s["titre"], "Type": s["type"], "Budget (EUR)": s["budget"]}
               for r in risques for s in r.get("strategies", [])]
    if rows_rb:
        df_rb = pd.DataFrame(rows_rb)
        def style_rb(row):
            if row["Budget (EUR)"] < 0: return ["color:#1D9E75;font-style:italic"] * len(row)
            if row["Budget (EUR)"] == 0: return ["color:var(--color-text-secondary)"] * len(row)
            return [""] * len(row)
        st.dataframe(df_rb.style.apply(style_rb, axis=1).format({"Budget (EUR)": "{:,}"}),
                     use_container_width=True, hide_index=True)
        st.markdown(f"**Total engage dans les strategies : {df_rb['Budget (EUR)'].sum():,} EUR**")

    st.divider()
    st.markdown("### Budget final recommande")
    fin1, fin2, fin3 = st.columns(3)
    fin1.metric("Budget de base", f"{total_global:,} EUR".replace(",", " "), "RH + Hors-RH")
    fin2.metric("Provisions risques", f"{total_provisions:,} EUR".replace(",", " "),
                f"{len(risques)} risques - {total_provisions/total_global*100:.0f}%" if total_global else "")
    fin3.metric("BUDGET TOTAL RECOMMANDE", f"{total_avec_risques:,} EUR".replace(",", " "))
    st.info(
        f"Demandez une enveloppe de **{total_avec_risques:,} EUR** au CEO. "
        f"Les provisions ({total_provisions:,} EUR) ne sont engagees que si les risques se materialisent — "
        f"le budget nominal attendu reste **{total_global:,} EUR**.",
        icon="💡",
    )
