"""
Moteur de simulation — données réelles semaine par semaine (S1→S8).
Projet : Book One MVP Mobile — jan 2025 → fev 2025.
"""

from data import (
    get_taches_default, get_equipe_default, calcul_taux_jour,
    JOURS_OUVRES_PAR_AN,
)

# ─────────────────────────────────────────────────────────────
# CONSTANTES TEMPORELLES & CONFIGURATION
# ─────────────────────────────────────────────────────────────

DUREE_SEMAINES = 8
MOIS_PROJET    = ["Jan 2025", "Fev 2025"]
MOIS_SEMAINES  = {
    "Jan 2025": (1, 4),
    "Fev 2025": (5, 8),
}

# Poids de consommation mensuelle par catégorie (jan / fev)
POIDS_MENSUEL = {
    "Ressources Humaines":    [0.45, 0.55],
    "Infrastructure & Cloud": [0.40, 0.60],
    "Licences & Logiciels":   [0.50, 0.50],
    "Données & APIs":         [0.30, 0.70],
    "Qualité & Tests":        [0.10, 0.90],
    "Légal & Conformité":     [0.60, 0.40],
    "Opérationnel":           [0.50, 0.50],
    "Coûts cachés":           [0.40, 0.60],
    "Provision & Risques":    [0.30, 0.70],
    "Autre":                  [0.50, 0.50],
}

# ─────────────────────────────────────────────────────────────
# CONSTANTES FINANCIÈRES
# ─────────────────────────────────────────────────────────────

BUDGET_VALIDE   = 130_000   
CA_PREVISIONNEL = 180_000   
BUDGET_RH       = 112_000   
BUDGET_HORS_RH  =   7_200   
BUDGET_RISQUES  =  10_800   

CATEGORIES_HORS_RH = {
    "Infrastructure & Cloud": {
        "total": 1800,
        "poids": [0.10, 0.15, 0.15, 0.15, 0.15, 0.10, 0.10, 0.10],
    },
    "Licences & Logiciels": {
        "total": 700,
        "poids": [1/8]*8,
    },
    "Données & APIs": {
        "total": 400,
        "poids": [0.05, 0.10, 0.15, 0.20, 0.20, 0.15, 0.10, 0.05],
    },
    "Qualité & Tests": {
        "total": 800,
        "poids": [0.02, 0.03, 0.05, 0.10, 0.20, 0.25, 0.20, 0.15],
    },
    "Légal & Conformité": {
        "total": 1100,
        "poids": [0.20, 0.15, 0.10, 0.10, 0.10, 0.15, 0.10, 0.10],
    },
    "Opérationnel": {
        "total": 900,
        "poids": [0.15, 0.10, 0.10, 0.15, 0.10, 0.10, 0.15, 0.15],
    },
    "Provision & Risques": {
        "total": 1500,
        "poids": [0.05, 0.10, 0.15, 0.20, 0.20, 0.15, 0.10, 0.05],
    },
}

FACTEURS_REEL = {
    "rh": [0.95, 0.98, 1.00, 1.05, 1.15, 1.10, 1.08, 1.10],
    "Infrastructure & Cloud": [1.0, 1.0, 1.0, 1.1, 1.3, 1.2, 1.1, 1.0],
    "Licences & Logiciels":   [1.0, 1.1, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
    "Données & APIs":         [1.0, 1.0, 1.0, 1.0, 1.2, 1.0, 1.0, 1.0],
    "Qualité & Tests":        [1.0, 1.0, 1.0, 1.0, 1.0, 1.3, 1.5, 1.2],
    "Légal & Conformité":     [1.0, 1.0, 1.0, 1.0, 1.0, 1.2, 1.0, 1.0],
    "Opérationnel":           [1.0, 1.0, 1.1, 1.0, 1.0, 1.0, 1.2, 1.1],
    "Provision & Risques":    [0.0, 0.0, 1.0, 2.0, 0.0, 1.5, 0.0, 1.0],
}

RISQUES_SURVENUS = {
    "S4": [
        {"id": "RS1", "titre": "API ISBN : limite de taux dépassée", "categorie": "Technique", "impact": "Moyen", "statut": "Resolu", "cout": 450},
        {"id": "RS2", "titre": "DPO : recommandation sur stockage images", "categorie": "Légal", "impact": "Faible", "statut": "Resolu", "cout": 200},
    ],
    "S8": [
        {"id": "RS3", "titre": "Stripe : délai validation compte pro", "categorie": "Paiement", "impact": "Élevé", "statut": "En cours", "cout": 1200},
        {"id": "RS4", "titre": "Dérive charge Dev Mobile (S7)", "categorie": "RH", "impact": "Moyen", "statut": "En cours", "cout": 2800},
    ]
}

def get_serie_hebdo(filtre_cat="Toutes", taches=None, equipe_index=None, jps=5):
    import streamlit as st
    from calculs import calcul_cout_tache
    
    if taches is None: taches = st.session_state.get("taches", [])
    if equipe_index is None:
        eq = st.session_state.get("equipe", [])
        equipe_index = {m["id"]: m for m in eq}

    plan_par_cat = {}
    reel_par_cat = {}
    cats_list = ["Ressources Humaines"] + list(CATEGORIES_HORS_RH.keys())
    for c in cats_list:
        plan_par_cat[c] = [0.0] * DUREE_SEMAINES
        reel_par_cat[c] = [0.0] * DUREE_SEMAINES

    # RH
    for t in taches:
        cout = calcul_cout_tache(t, equipe_index, jps)
        s_deb = t["semaine"]
        s_fin = int(t["semaine"] + t["duree"] + 0.9) - 1
        nb_s  = max(1, s_fin - s_deb + 1)
        cout_s = cout / nb_s
        for s in range(s_deb, s_fin + 1):
            if s <= DUREE_SEMAINES:
                plan_par_cat["Ressources Humaines"][s-1] += cout_s
                reel_par_cat["Ressources Humaines"][s-1] += cout_s * FACTEURS_REEL["rh"][s-1]

    # Hors-RH
    for cat, data in CATEGORIES_HORS_RH.items():
        for i, p in enumerate(data["poids"]):
            val_p = data["total"] * p
            plan_par_cat[cat][i] += val_p
            reel_par_cat[cat][i] += val_p * FACTEURS_REEL.get(cat, [1.0]*8)[i]

    # Global
    plan_sem = [sum(plan_par_cat[c][i] for c in cats_list) for i in range(DUREE_SEMAINES)]
    reel_sem = [sum(reel_par_cat[c][i] for c in cats_list) for i in range(DUREE_SEMAINES)]

    plan_cum, reel_cum, cp, cr = [], [], 0, 0
    for p, r in zip(plan_sem, reel_sem):
        cp += p; cr += r
        plan_cum.append(cp); reel_cum.append(cr)

    if filtre_cat != "Toutes":
        final_plan_sem = plan_par_cat.get(filtre_cat, [0.0]*8)
        final_reel_sem = reel_par_cat.get(filtre_cat, [0.0]*8)
        plan_cum, reel_cum, cp, cr = [], [], 0, 0
        for p, r in zip(final_plan_sem, final_reel_sem):
            cp += p; cr += r
            plan_cum.append(cp); reel_cum.append(cr)

    return {
        "semaines": list(range(1, DUREE_SEMAINES + 1)),
        "planifie_cum": plan_cum,
        "reel_cum": reel_cum,
        "planifie_par_cat": plan_par_cat,
        "reel_par_cat": reel_par_cat,
        "total_planifie": plan_cum[-1] if plan_cum else 0,
        "total_reel": reel_cum[-1] if reel_cum else 0,
        "categories": ["Toutes"] + cats_list
    }

def get_simulation_data():
    import streamlit as st
    from calculs import calcul_cout_tache
    
    serie = get_serie_hebdo("Toutes")
    taches = st.session_state.get("taches", [])
    equipe = st.session_state.get("equipe", [])
    eq_idx = {m["id"]: m for m in equipe}
    jps = st.session_state.get("config", {}).get("jours_par_semaine", 5)

    cpr = {}
    for m in equipe:
        tr = [t for t in taches if t["res"] == m["id"]]
        p = sum(calcul_cout_tache(t, eq_idx, jps) for t in tr)
        cpr[m["id"]] = {"planifie": p, "reel": p * 1.08, "label": m["label"]}

    # Phasage mensuel (Jan: S1-S4, Fev: S5-S8)
    jan_rh_p = sum(serie["planifie_par_cat"]["Ressources Humaines"][i] for i in range(4))
    jan_rh_r = sum(serie["reel_par_cat"]["Ressources Humaines"][i] for i in range(4))
    fev_rh_p = sum(serie["planifie_par_cat"]["Ressources Humaines"][i] for i in range(4, 8))
    fev_rh_r = sum(serie["reel_par_cat"]["Ressources Humaines"][i] for i in range(4, 8))

    jan_hr_p = sum(sum(serie["planifie_par_cat"][c][i] for c in serie["planifie_par_cat"] if c != "Ressources Humaines") for i in range(4))
    jan_hr_r = sum(sum(serie["reel_par_cat"][c][i] for c in serie["reel_par_cat"] if c != "Ressources Humaines") for i in range(4))
    fev_hr_p = sum(sum(serie["planifie_par_cat"][c][i] for c in serie["planifie_par_cat"] if c != "Ressources Humaines") for i in range(4, 8))
    fev_hr_r = sum(sum(serie["reel_par_cat"][c][i] for c in serie["reel_par_cat"] if c != "Ressources Humaines") for i in range(4, 8))

    phasage_list = [
        {
            "mois": "Jan 2025", 
            "planifie_rh": jan_rh_p, "reel_rh": jan_rh_r,
            "planifie_hors": jan_hr_p, "reel_hors": jan_hr_r,
            "risques_mois": 650
        },
        {
            "mois": "Fev 2025", 
            "planifie_rh": fev_rh_p, "reel_rh": fev_rh_r,
            "planifie_hors": fev_hr_p, "reel_hors": fev_hr_r,
            "risques_mois": 4000
        },
    ]
    
    return {
        "taches": taches,
        "equipe": equipe,
        "ca_mensuel_prevu": [0]*8 + [1500, 3000, 6000, 9000, 12000, 15000, 18000, 20000, 22000, 25000] + [25000]*6,
        "ca_mensuel_reel":  [0]*8 + [1200, 2800, 5500, None, None, None, None, None, None, None],
        "cout_par_ressource": cpr,
        "phasage_mensuel": phasage_list,
        "jalons": {
            "S4": {
                "semaine": 4, "taches_terminees": 8, "taches_prevues": 10, "taches_retard": 2,
                "taux_achevement": 33, "risques": RISQUES_SURVENUS["S4"],
                "cout_planifie": serie["planifie_cum"][3], "cout_reel": serie["reel_cum"][3],
                "couts_non_planifies": 650,
                "meteo": {rid: 3 for rid in eq_idx}
            },
            "S8": {
                "semaine": 8, "taches_terminees": 24, "taches_prevues": 24, "taches_retard": 0,
                "taux_achevement": 100, "risques": RISQUES_SURVENUS["S8"],
                "cout_planifie": serie["planifie_cum"][7], "cout_reel": serie["reel_cum"][7],
                "couts_non_planifies": 4000,
                "meteo": {rid: 2 for rid in eq_idx}
            },
        },
        "meteo": {rid: {"S4": 3, "S8": 2} for rid in eq_idx},
    }

def get_roi_data():
    import streamlit as st
    from calculs import calcul_cout_tache
    eq = st.session_state.get("equipe", [])
    eq_idx = {m["id"]: m for m in eq}
    taches = st.session_state.get("taches", [])
    jps = st.session_state.get("config", {}).get("jours_par_semaine", 5)
    total_rh = sum(calcul_cout_tache(t, eq_idx, jps) for t in taches)
    invest = total_rh + 7200 + 10800
    rev_mensuel = ([0]*2 + [1500, 3000, 6000, 9000, 12000, 15000, 18000, 20000, 22000, 25000] + [25000]*12)[:24]
    opex_mensuel = [0]*2 + [1200]*22
    rev_cumul, cout_cumul, be_mois = 0, invest, None
    for i, (r, o) in enumerate(zip(rev_mensuel, opex_mensuel)):
        rev_cumul += r; cout_cumul += o
        if be_mois is None and rev_cumul >= cout_cumul: be_mois = i + 1
    return {
        "mois": list(range(1, 25)), "rev_mensuel": rev_mensuel, "charges_mensuel": opex_mensuel,
        "investissement": invest, "breakeven_mois": be_mois,
    }
