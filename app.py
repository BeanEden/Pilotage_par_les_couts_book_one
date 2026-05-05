"""
Application Streamlit — Pilotage RH par les couts : Book One MVP Mobile.
Projet : startup "Tous les livres a 1 EUR" — jan-avr 2025.
"""

import os
import sys
import copy
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Ajouter le repertoire courant au path pour eviter les ModuleNotFoundError sur Windows
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data import (
    get_taches_default, get_equipe_default,
    PROJECT_CONFIG, CATEGORIES, CAT_COULEURS,
    COMPLEXITE_OPTIONS, COMPLEXITE_COULEURS, TYPE_RESSOURCE_OPTIONS,
    JOURS_OUVRES_PAR_AN, STATUTS_CONVENTION, TAUX_CHARGES_PATRONALES,
    STATUT_DEFAULT_PAR_TYPE, calcul_taux_jour,
)
from calculs import (
    calcul_kpis, build_gantt_figure, build_budget_chart,
    build_cat_chart, build_charge_chart, build_budget_dataframe,
    calcul_cout_tache, calcul_jh_tache, propager_dependances,
    build_rh_pie_chart, build_rh_weekly_cost_chart,
)
from page_budget_global import render_budget_global
from page_direction_financiere import render_direction_financiere
from page_investisseurs import render_investisseurs
from page_equipe_projet import render_equipe_projet
from persistence import save_state, load_state, delete_state
from utils_pdf import export_page_to_pdf


def _autosave():
    save_state({
        "taches":       st.session_state.get("taches", []),
        "equipe":       st.session_state.get("equipe", []),
        "config":       st.session_state.get("config", {}),
        "postes_couts": st.session_state.get("postes_couts"),
        "risques":      st.session_state.get("risques"),
    })


st.set_page_config(
    page_title="Pilotage RH — Book One MVP",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
[data-testid="metric-container"] {
    background: #F4F6FA;
    border: 1px solid #E2E6F0;
    border-radius: 8px;
    padding: 12px 16px;
}
[data-testid="stMetricDelta"] { font-size: 12px; }
.stAlert { border-radius: 8px; }
div[data-testid="stExpander"] { border: 1px solid #E2E6F0; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ── Initialisation session state ─────────────────────────────
if "taches" not in st.session_state:
    saved = load_state()
    if saved:
        st.session_state.taches  = saved.get("taches",  get_taches_default())
        st.session_state.equipe  = saved.get("equipe",  get_equipe_default())
        st.session_state.config  = saved.get("config",  copy.deepcopy(PROJECT_CONFIG))
        if "postes_couts" in saved: st.session_state.postes_couts = saved["postes_couts"]
        if "risques"      in saved: st.session_state.risques      = saved["risques"]
    else:
        st.session_state.taches = get_taches_default()
        st.session_state.equipe = get_equipe_default()
        st.session_state.config = copy.deepcopy(PROJECT_CONFIG)

equipe_index      = {m["id"]: m for m in st.session_state.equipe}
ids_ressources    = [m["id"] for m in st.session_state.equipe]
labels_ressources = {m["id"]: m["label"] for m in st.session_state.equipe}

# ── SIDEBAR : NAVIGATION ─────────────────────────────────────
with st.sidebar:
    st.markdown("## Navigation")
    menu_options = {
        "Gantt":    "Gantt",
        "Taches":   "Taches",
        "BudgetRH": "Budget RH",
        "Equipe":   "Equipe",
        "Global":   "Budget Global & Risques",
        "Finances":  "Direction Financiere",
        "Invest":   "Investisseurs",
        "Projet":   "Equipe Projet",
    }
    page_sel = st.radio(
        "Selectionner une vue",
        options=list(menu_options.values()),
        key="navigation_sidebar",
    )

    st.divider()
    if st.button("Reinitialiser les donnees", use_container_width=True):
        st.session_state.taches       = get_taches_default()
        st.session_state.equipe       = get_equipe_default()
        st.session_state.config       = copy.deepcopy(PROJECT_CONFIG)
        st.session_state.postes_couts = None
        st.session_state.risques      = None
        delete_state()
        st.rerun()
    st.caption("Sauvegarde automatique active")

# ── KPIs globaux (calcules une fois, utilises dans plusieurs vues) ────────────
kt = calcul_kpis(
    st.session_state.taches,
    equipe_index,
    st.session_state.config["date_debut"],
    st.session_state.config["jours_par_semaine"],
)

# ── ROUTAGE ───────────────────────────────────────────────────

if page_sel == menu_options["Gantt"]:
    c_head1, c_head2 = st.columns([4, 1])
    c_head1.markdown(f"# {st.session_state.config['nom']}")

    # Export PDF Gantt
    kpis_gantt = {
        "Nb Taches":  kt["nb_taches"],
        "Budget RH":  f"{int(kt['total_cout']):,} EUR",
        "Jours/Homme":f"{kt['total_jh']} j/h",
        "Date Fin":   kt["date_fin"].strftime("%d/%m/%Y"),
    }
    pdf_bytes = export_page_to_pdf("Vue Gantt — Book One", kpis_gantt, config=st.session_state.config)
    c_head2.download_button("PDF", data=pdf_bytes, file_name="Rapport_Gantt_BookOne.pdf", mime="application/pdf")

    with st.expander("Parametres du projet & Filtres d'affichage", expanded=False):
        c_conf1, c_conf2, c_conf3 = st.columns(3)
        st.session_state.config["nom"] = c_conf1.text_input(
            "Nom du projet", value=st.session_state.config["nom"])
        st.session_state.config["date_debut"] = c_conf1.date_input(
            "Date de debut",
            value=pd.to_datetime(st.session_state.config["date_debut"]),
            format="DD/MM/YYYY",
        ).strftime("%Y-%m-%d")

        st.session_state.config["jours_par_semaine"] = c_conf2.slider(
            "Jours ouvres / semaine", 3, 5, st.session_state.config["jours_par_semaine"])

        tri_gantt = c_conf2.radio(
            "Tri", ["numero", "date"], horizontal=True,
            format_func=lambda x: "Numero" if x == "numero" else "Date",
        )

        afficher_deps  = c_conf3.checkbox("Dependances", value=True)
        filtre_critique = c_conf3.checkbox("Chemin critique", value=False)

        f1, f2, f3 = st.columns(3)
        filtre_cat = f1.multiselect("Categories", options=CATEGORIES, placeholder="Toutes")
        filtre_res = f2.multiselect(
            "Ressources", options=ids_ressources,
            format_func=lambda x: labels_ressources.get(x, x), placeholder="Toutes",
        )
        sem_max_p  = int(max(t["semaine"] + t["duree"] for t in st.session_state.taches) + 0.9)
        filtre_sem = f3.slider("Plage semaines", 1, sem_max_p, (1, sem_max_p), format="S%d")

    taches_f = st.session_state.taches
    if filtre_cat:     taches_f = [t for t in taches_f if t["cat"] in filtre_cat]
    if filtre_res:     taches_f = [t for t in taches_f if t["res"] in filtre_res]
    if filtre_critique:taches_f = [t for t in taches_f if t.get("critique")]
    taches_f = [t for t in taches_f
                if t["semaine"] <= filtre_sem[1] and t["semaine"] + t["duree"] - 1 >= filtre_sem[0]]

    kf = calcul_kpis(taches_f, equipe_index, st.session_state.config["date_debut"],
                     st.session_state.config["jours_par_semaine"])

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Taches",       kf["nb_taches"],   f"/{kt['nb_taches']} total")
    c2.metric("Jours / Homme", f"{kf['total_jh']:.1f} j/h", f"/{kt['total_jh']:.1f} total")
    c3.metric("Duree",        f"{kf['nb_semaines']:.1f} sem.")
    c4.metric("Livraison",    kf["date_fin"].strftime("%d/%m/%Y") if kf["nb_taches"] else "—")
    c5.metric("Budget RH",    f"{int(kf['total_cout']):,} EUR".replace(",", " "))

    st.divider()

    if not taches_f:
        st.info("Aucune tache ne correspond aux filtres.")
    else:
        fig_gantt = build_gantt_figure(
            taches_f, equipe_index,
            st.session_state.config["date_debut"],
            st.session_state.config["jours_par_semaine"],
            tri=tri_gantt, afficher_deps=afficher_deps,
        )
        st.plotly_chart(fig_gantt, use_container_width=True)

    col_inf1, col_inf2 = st.columns(2)
    with col_inf1:
        with st.expander("Chemin critique — detail", expanded=False):
            taches_crit = sorted(
                [t for t in st.session_state.taches if t.get("critique")],
                key=lambda t: t["semaine"],
            )
            if taches_crit:
                st.markdown("`" + " -> ".join(f"#{t['id']}" for t in taches_crit) + "`")
                st.caption(
                    f"{len(taches_crit)} taches critiques - "
                    f"{int(sum(calcul_cout_tache(t, equipe_index, st.session_state.config['jours_par_semaine']) for t in taches_crit)):,} EUR"
                )
    with col_inf2:
        with st.expander("Charge hebdomadaire", expanded=False):
            st.plotly_chart(
                build_charge_chart(
                    st.session_state.taches, equipe_index,
                    st.session_state.config["date_debut"],
                    st.session_state.config["jours_par_semaine"],
                ),
                use_container_width=True,
            )

elif page_sel == menu_options["Taches"]:
    c_t1, c_t2 = st.columns([4, 1])
    c_t1.markdown("### Gestion des taches")

    df_taches  = pd.DataFrame(st.session_state.taches)[["id", "nom", "res", "cat", "semaine", "duree"]]
    pdf_bytes_t = export_page_to_pdf(
        "Liste des Taches — Book One",
        {"Total": len(st.session_state.taches)},
        tables=[("Detail des taches", df_taches)],
    )
    c_t2.download_button("PDF", data=pdf_bytes_t, file_name="Liste_Taches_BookOne.pdf", mime="application/pdf")

    if st.session_state.get("propagation_info"):
        st.info(
            "Propagation automatique :\n\n"
            + "\n".join(f"- {m}" for m in st.session_state["propagation_info"]),
            icon="🔗",
        )
        if st.button("Masquer"):
            st.session_state.pop("propagation_info", None); st.rerun()

    with st.expander("Ajouter une tache"):
        nc1, nc2, nc3 = st.columns(3)
        new_nom  = nc1.text_input("Nom")
        new_cat  = nc1.selectbox("Categorie", CATEGORIES)
        new_res  = nc2.selectbox("Ressource", ids_ressources,
                                  format_func=lambda x: labels_ressources.get(x, x))
        new_sem  = nc2.number_input("Semaine debut", 1, 52, 1)
        new_dur  = nc3.number_input("Duree", 1, 20, 2)
        new_cplx = nc3.selectbox("Complexite", COMPLEXITE_OPTIONS)
        new_crit = nc3.checkbox("Critique")
        new_deps = nc1.text_input("Dependances (ex: 1,3)")
        if st.button("Ajouter", type="primary"):
            deps = [int(d.strip()) for d in new_deps.split(",") if d.strip().isdigit()]
            nid  = max((t["id"] for t in st.session_state.taches), default=0) + 1
            st.session_state.taches.append({
                "id": nid, "cat": new_cat, "nom": new_nom, "res": new_res,
                "semaine": float(new_sem), "duree": float(new_dur),
                "critique": new_crit, "deps": deps, "complexite": new_cplx,
            })
            _autosave(); st.rerun()

    for cat in sorted(set(t["cat"] for t in st.session_state.taches)):
        t_cat = [t for t in st.session_state.taches if t["cat"] == cat]
        st.markdown(f"**{cat}**")
        for t in t_cat:
            with st.expander(f"#{t['id']} - {t['nom']} ({t['res']})"):
                e1, e2, e3 = st.columns(3)
                t_nom     = e1.text_input("Nom", t["nom"], key=f"tn_{t['id']}")
                
                # Securite si la categorie ou la ressource a change entre temps (session state persistant)
                idx_cat = CATEGORIES.index(t["cat"]) if t["cat"] in CATEGORIES else 0
                t_cat_val = e1.selectbox("Cat", CATEGORIES, index=idx_cat, key=f"tc_{t['id']}")
                
                idx_res = ids_ressources.index(t["res"]) if t["res"] in ids_ressources else 0
                t_res     = e2.selectbox("Res", ids_ressources, index=idx_res,
                                         format_func=lambda x: labels_ressources.get(x, x), key=f"tr_{t['id']}")
                t_sem     = e2.number_input("Sem", 1.0, 52.0, float(t["semaine"]), step=1.0, key=f"ts_{t['id']}")
                t_dur     = e2.number_input("Dur", 0.2, 20.0, float(t["duree"]), step=0.2, key=f"td_{t['id']}")
                t_deps    = e3.text_input("Deps", ",".join(str(d) for d in t["deps"]), key=f"tp_{t['id']}")
                if st.button("Enregistrer", key=f"save_{t['id']}"):
                    idx = next(i for i, x in enumerate(st.session_state.taches) if x["id"] == t["id"])
                    st.session_state.taches[idx].update({
                        "nom": t_nom, "cat": t_cat_val, "res": t_res,
                        "semaine": t_sem, "duree": t_dur,
                        "deps": [int(d) for d in t_deps.split(",") if d.strip().isdigit()],
                    })
                    _autosave(); st.rerun()

elif page_sel == menu_options["BudgetRH"]:
    st.markdown("### Budget RH — Book One")
    
    # Filtre spécifique pour cette page
    filtre_res_rh = st.multiselect(
        "Filtrer par ressource", options=ids_ressources,
        format_func=lambda x: labels_ressources.get(x, x),
        placeholder="Toutes les ressources",
        key="filtre_res_rh_page"
    )
    taches_rh_f = st.session_state.taches
    if filtre_res_rh:
        taches_rh_f = [t for t in taches_rh_f if t["res"] in filtre_res_rh]

    b1, b2, b3 = st.columns(3)
    # On recalcule les KPIs pour les ressources filtrées
    kf_rh = calcul_kpis(taches_rh_f, equipe_index, st.session_state.config["date_debut"],
                        st.session_state.config["jours_par_semaine"])
    b1.metric("Budget RH sélectionné", f"{int(kf_rh['total_cout']):,} EUR".replace(",", " "))
    b2.metric("Charge totale", f"{kf_rh['total_jh']:.1f} j/h")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Répartition par ressource (Total)**")
        st.plotly_chart(
            build_rh_pie_chart(taches_rh_f, equipe_index,
                               st.session_state.config["jours_par_semaine"]),
            use_container_width=True,
        )
    with c2:
        st.markdown("**Coût hebdomadaire cumulé par profil**")
        st.plotly_chart(
            build_rh_weekly_cost_chart(taches_rh_f, equipe_index,
                                       st.session_state.config["date_debut"],
                                       st.session_state.config["jours_par_semaine"]),
            use_container_width=True,
        )
    st.dataframe(
        build_budget_dataframe(st.session_state.taches, equipe_index,
                               st.session_state.config["jours_par_semaine"]),
        use_container_width=True, hide_index=True,
    )

elif page_sel == menu_options["Equipe"]:
    from data import SENIORITE_OPTIONS
    st.markdown("### Equipe — Book One")
    st.caption("Gestion des profils, personas et coûts employeurs.")

    with st.expander("➕ **Ajouter un membre à l'équipe**", expanded=False):
        c1, c2 = st.columns([2, 2])
        new_id = c1.text_input("ID court (ex: DEV2)", key="new_res_id").upper().strip()
        new_lbl = c1.text_input("Poste / Rôle", key="new_res_lbl")
        
        c3, c4, c5 = st.columns(3)
        new_nom = c3.text_input("Nom", key="new_res_nom")
        new_pre = c4.text_input("Prénom", key="new_res_pre")
        new_sen = c5.selectbox("Séniorité", SENIORITE_OPTIONS, index=2, key="new_res_sen")
        
        c6, c7 = st.columns(2)
        new_typ = c6.selectbox("Type de contrat", TYPE_RESSOURCE_OPTIONS, key="new_res_typ")
        new_sta = c7.selectbox("Statut conventionnel", STATUTS_CONVENTION, key="new_res_sta")
        new_sal = st.number_input("Salaire brut annuel (€)", value=45000, step=1000, key="new_res_sal")
        
        if st.button("Créer le profil"):
            if not new_id or not new_lbl:
                st.error("L'ID et le Poste sont obligatoires.")
            elif any(m["id"] == new_id for m in st.session_state.equipe):
                st.error(f"L'ID '{new_id}' est déjà utilisé.")
            else:
                st.session_state.equipe.append({
                    "id": new_id, "label": new_lbl, 
                    "nom": new_nom, "prenom": new_pre, "seniorite": new_sen,
                    "type": new_typ, "statut": new_sta, "salaire_brut_annuel": new_sal,
                    "couleur": "888780"
                })
                _autosave(); st.rerun()


    # Nettoyage automatique des membres non utilisés
    ids_utilises = set(t["res"] for t in st.session_state.taches)
    equipe_nettoyee = [m for m in st.session_state.equipe if m["id"] in ids_utilises]
    if len(equipe_nettoyee) != len(st.session_state.equipe):
        st.session_state.equipe = equipe_nettoyee
        _autosave()
        st.info(f"🧹 Nettoyage : {len(ids_utilises)} profils actifs conservés.")

    for m in st.session_state.equipe:
        tj = calcul_taux_jour(m)
        jours = JOURS_OUVRES_PAR_AN.get(m["type"], 218)
        taux_ch = TAUX_CHARGES_PATRONALES.get(m.get("statut", "ETAM"), 0.42)
        cout_annuel = int(m["salaire_brut_annuel"] * (1 + taux_ch))
        
        full_name = f"{m.get('prenom', '')} {m.get('nom', '')}".strip()
        seniority = m.get('seniorite', 'N/A')
        
        with st.expander(f"👤 {full_name or m['label']} — {m['label']} ({seniority}) — {tj} EUR/j"):
            kp = f"eq_{m['id']}"
            c1, c2 = st.columns([2, 1])
            new_label = c1.text_input("Poste", m["label"], key=f"{kp}_lbl")
            new_sen = c2.selectbox("Séniorité", SENIORITE_OPTIONS, 
                                   index=SENIORITE_OPTIONS.index(m.get("seniorite", "Senior")), 
                                   key=f"{kp}_sen")
            
            c3, c4 = st.columns(2)
            new_prenom = c3.text_input("Prénom", m.get("prenom", ""), key=f"{kp}_pre")
            new_nom = c4.text_input("Nom", m.get("nom", ""), key=f"{kp}_nom")
            
            c5, c6 = st.columns(2)
            new_type  = c5.selectbox("Type", TYPE_RESSOURCE_OPTIONS,
                                     index=TYPE_RESSOURCE_OPTIONS.index(m["type"]),
                                     key=f"{kp}_type")
            new_statut = c6.selectbox("Statut", STATUTS_CONVENTION,
                                      index=STATUTS_CONVENTION.index(m.get("statut", "ETAM")),
                                      key=f"{kp}_statut")
            
            c1b, c2b, c3b = st.columns(3)
            new_sal = c1b.number_input("Salaire brut annuel (€)", value=m["salaire_brut_annuel"], step=1000, key=f"{kp}_sal")
            
            c2b.metric("Taux de charges", f"{int(taux_ch * 100)} %")
            c3b.metric("Coût annuel Total", f"{cout_annuel:,} €".replace(",", " "))
            
            st.info(f"💡 **Calcul du taux jour** : {cout_annuel:,} € / {jours} j ouvrés = **{tj} €/j** (arrondi)")

            if st.button("Enregistrer", key=f"{kp}_btn"):
                idx = next(i for i, x in enumerate(st.session_state.equipe) if x["id"] == m["id"])
                st.session_state.equipe[idx].update({
                    "label": new_label, "nom": new_nom, "prenom": new_prenom, "seniorite": new_sen,
                    "type": new_type, "statut": new_statut, "salaire_brut_annuel": new_sal,
                })
                _autosave(); st.rerun()

    st.markdown("#### Charge & cout par ressource")
    rows_charge = []
    for m in st.session_state.equipe:
        tr   = [t for t in st.session_state.taches if t["res"] == m["id"]]
        jh   = sum(calcul_jh_tache(t, st.session_state.config["jours_par_semaine"]) for t in tr)
        cout = sum(calcul_cout_tache(t, equipe_index, st.session_state.config["jours_par_semaine"]) for t in tr)
        rows_charge.append({
            "Profil":       m["label"],
            "Nb taches":    len(tr),
            "J/H total":    jh,
            "Cout total (EUR)": int(cout),
        })
    st.dataframe(
        pd.DataFrame(rows_charge).sort_values("J/H total", ascending=False),
        use_container_width=True, hide_index=True,
    )

elif page_sel == menu_options["Global"]:
    render_budget_global()

elif page_sel == menu_options["Finances"]:
    render_direction_financiere()

elif page_sel == menu_options["Invest"]:
    render_investisseurs()

elif page_sel == menu_options["Projet"]:
    render_equipe_projet()
