"""
Page Equipe Projet — Dashboard operationnel Book One
Gantt ressources | Avancement par module aux jalons S4/S8 | Prediction retard
Vue liee en temps reel au Gantt et a l'equipe.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime
from calculs import (
    calcul_cout_tache, calcul_jh_tache, build_gantt_figure,
    propager_dependances,
)
from data import calcul_taux_jour
from simulation import get_simulation_data, BUDGET_VALIDE


# ─────────────────────────────────────────────────────────────
# GRAPHIQUES
# ─────────────────────────────────────────────────────────────

def build_gantt_ressources(taches, equipe_index, date_debut, jps=5):
    """
    Gantt par ressource : une ligne par membre de l'equipe, barres = taches affectees.
    Permet de visualiser la charge individuelle et les chevauchements.
    """
    from calculs import semaine_vers_date

    rows = []
    for t in taches:
        res  = equipe_index.get(t["res"], {})
        deb  = semaine_vers_date(t["semaine"], date_debut)
        fin  = semaine_vers_date(t["semaine"] + t["duree"], date_debut)
        jh   = calcul_jh_tache(t, jps)
        cout = calcul_cout_tache(t, equipe_index, jps)
        rows.append({
            "Ressource": res.get("label", t["res"]),
            "Tache":     f"#{t['id']} {t['nom']}",
            "Debut":     deb,
            "Fin":       fin,
            "Couleur":   "#" + res.get("couleur", "888780"),
            "Critique":  t.get("critique", False),
            "Tooltip": (
                f"<b>{t['nom']}</b><br>"
                f"Ressource : {res.get('label','?')}<br>"
                f"S{t['semaine']} a S{t['semaine']+t['duree']} - {jh} j/h - {int(cout):,} EUR"
                + ("<br><b>Chemin critique</b>" if t.get("critique") else "")
            ),
        })

    df = pd.DataFrame(rows)
    ordre = [res.get("label", "") for res in equipe_index.values()]
    df["_ord"] = df["Ressource"].apply(lambda r: ordre.index(r) if r in ordre else 99)
    df = df.sort_values("_ord")

    labels_y = list(df["Ressource"].unique())

    fig = px.timeline(
        df, x_start="Debut", x_end="Fin", y="Ressource",
        color="Ressource", custom_data=["Tooltip"],
        category_orders={"Ressource": list(reversed(labels_y))},
    )

    couleur_map  = {row["Ressource"]: row["Couleur"] for row in rows}
    critique_map = {}
    for row in rows:
        critique_map.setdefault(row["Ressource"], []).append(row["Critique"])

    for trace in fig.data:
        nom  = trace.name
        col  = couleur_map.get(nom, "#888")
        crit = any(critique_map.get(nom, []))
        trace.marker.color      = col
        trace.marker.opacity    = 1.0 if crit else 0.75
        trace.marker.line.color = "#E24B4A" if crit else col
        trace.marker.line.width = 1.5 if crit else 0.5
        trace.hovertemplate     = "%{customdata[0]}<extra></extra>"
        trace.showlegend        = False

    fig.update_layout(
        height=320,
        xaxis=dict(title="", tickformat="%d %b", gridcolor="#E8EAF0"),
        yaxis=dict(title="", categoryorder="array",
                   categoryarray=list(reversed(labels_y))),
        margin=dict(l=10, r=20, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=11),
    )
    return fig


def build_avancement_chart(sim: dict) -> go.Figure:
    """
    Avancement par module fonctionnel Book One aux 3 jalons (S4, S8, S14).
    Les taux sont contextualises au projet Book One.
    """
    cats = ["Cadrage", "UX/UI", "Architecture", "Développement MVP", "Bonus", "Tests/Recette", "Mise en production", "Clôture"]

    # Avancement simulé par module à chaque jalon
    avancement_s4 = {
        "Cadrage": 100, "UX/UI": 100, "Architecture": 80, "Développement MVP": 20,
        "Bonus": 0, "Tests/Recette": 0, "Mise en production": 0, "Clôture": 0,
    }
    avancement_s8 = {
        "Cadrage": 100, "UX/UI": 100, "Architecture": 100, "Développement MVP": 100,
        "Bonus": 100, "Tests/Recette": 100, "Mise en production": 100, "Clôture": 100,
    }

    fig = go.Figure()
    for data, name, col in [
        (avancement_s4,  "S4",  "#B5D4F4"),
        (avancement_s8,  "S8",  "#1E2761"),
    ]:
        fig.add_trace(go.Bar(
            name=name, x=cats, y=[data.get(c, 0) for c in cats],
            marker_color=col,
            text=[f"{data.get(c, 0)}%" for c in cats],
            textposition="outside", textfont=dict(size=9),
            hovertemplate="%{x} — " + name + " : %{y}%<extra></extra>",
        ))

    fig.update_layout(
        barmode="group", height=300,
        xaxis=dict(tickangle=-30, tickfont=dict(size=9)),
        yaxis=dict(title="Avancement (%)", range=[0, 115], gridcolor="#E8EAF0"),
        legend=dict(orientation="h", y=1.1, font_size=11),
        margin=dict(l=10, r=10, t=30, b=60),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=11),
    )
    return fig


def build_prediction_retard(sim: dict):
    """
    Prediction du retard final basee sur la velocite observee aux jalons.
    Velocite = taches terminees / semaines ecoulees.
    Projection : si la velocite reste constante, fin a quelle semaine ?
    """
    jalons      = sim["jalons"]
    jalons_keys = ["S4", "S8"]
    points      = [(jalons[jk]["semaine"], jalons[jk]["taches_terminees"]) for jk in jalons_keys]
    total_taches = len(sim["taches"])

    velocites = []
    for i in range(1, len(points)):
        s0, t0 = points[i - 1]
        s1, t1 = points[i]
        v = (t1 - t0) / max(1, s1 - s0)
        velocites.append(v)
    v_moy = sum(velocites) / len(velocites) if velocites else 1.0

    s_last, t_last   = points[-1]
    restantes        = total_taches - t_last
    sem_restantes    = restantes / max(0.01, v_moy)
    sem_fin_pred     = s_last + sem_restantes
    retard_pred      = max(0, sem_fin_pred - 8)

    sems        = [p[0] for p in points]
    termees     = [p[1] for p in points]
    sems_proj   = [s_last + i for i in range(int(sem_restantes) + 2)]
    termees_proj = [t_last + v_moy * i for i in range(int(sem_restantes) + 2)]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sems, y=termees, mode="lines+markers", name="Taches terminees (reel)",
        line=dict(color="#1D9E75", width=2.5), marker=dict(size=10),
    ))
    fig.add_trace(go.Scatter(
        x=sems_proj, y=termees_proj, mode="lines", name="Projection (velocite constante)",
        line=dict(color="#BA7517", width=2, dash="dot"),
    ))
    fig.add_hline(
        y=total_taches, line=dict(color="#378ADD", width=1.5, dash="dash"),
        annotation_text=f"Objectif : {total_taches} taches", annotation_font_size=10,
    )
    fig.add_vline(
        x=14, line=dict(color="#1E2761", width=1.5, dash="dot"),
        annotation_text="S14 prevu", annotation_font_size=10,
    )
    fig.update_layout(
        height=260,
        xaxis=dict(title="Semaine", gridcolor="#E8EAF0"),
        yaxis=dict(title="Taches terminees", gridcolor="#E8EAF0"),
        legend=dict(orientation="h", y=1.12, font_size=10),
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=11),
    )
    return fig, retard_pred, v_moy


def build_charge_ressource(taches, equipe_index, jps=5):
    """Heatmap semaine x ressource = j/h charges."""
    membres  = list(equipe_index.keys())
    labels   = [equipe_index[m]["label"] for m in membres]
    sem_max  = int(max(t["semaine"] + t["duree"] for t in taches) + 0.9)
    matrix   = [[0] * sem_max for _ in membres]

    for t in taches:
        if t["res"] in membres:
            ri = membres.index(t["res"])
            s_deb = int(t["semaine"]) - 1
            s_fin = int(t["semaine"] + t["duree"] + 0.9) - 1
            for s in range(s_deb, s_fin + 1):
                if s < sem_max:
                    matrix[ri][s] += jps

    sem_labels = [f"S{i+1}" for i in range(sem_max)]
    fig = go.Figure(go.Heatmap(
        z=matrix, x=sem_labels, y=labels,
        colorscale=[[0, "#F7F8FC"], [0.4, "#B5D4F4"], [0.8, "#378ADD"], [1, "#1E2761"]],
        hovertemplate="<b>%{y}</b><br>%{x} : %{z} j/h<extra></extra>",
        showscale=True, colorbar=dict(title="j/h", thickness=12, len=0.8),
    ))
    fig.update_layout(
        height=260,
        xaxis=dict(tickfont=dict(size=9)), yaxis=dict(tickfont=dict(size=10)),
        margin=dict(l=10, r=60, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", font=dict(size=11),
    )
    return fig


# ─────────────────────────────────────────────────────────────
# RENDER PRINCIPAL
# ─────────────────────────────────────────────────────────────

def render_equipe_projet():
    st.markdown("# Dashboard Equipe Projet — Book One")
    st.caption(
        "Vue operationnelle liee en temps reel au Gantt. "
        "Modifier une tache ou une ressource met a jour ce dashboard instantanement. "
        "Jalons : S4 (architecture + dev), S8 (livraison finale)."
    )

    if "taches" not in st.session_state or "equipe" not in st.session_state:
        st.warning("Donnees non chargees — revenez a l'onglet Gantt.")
        return

    taches       = st.session_state.taches
    equipe       = st.session_state.equipe
    equipe_index = {m["id"]: m for m in equipe}
    config       = st.session_state.get("config", {"date_debut": "2025-01-06", "jours_par_semaine": 5})
    date_debut   = config.get("date_debut", "2025-01-06")
    jps          = config.get("jours_par_semaine", 5)
    sim          = get_simulation_data()

    # ── KPIs operationnels ───────────────────────────────────
    total_taches = len(taches)
    total_jh     = sum(calcul_jh_tache(t, jps) for t in taches)
    total_cout   = sum(calcul_cout_tache(t, equipe_index, jps) for t in taches)
    nb_critiques = sum(1 for t in taches if t.get("critique"))
    sem_max      = max(t["semaine"] + t["duree"] for t in taches) - 1

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Taches totales",   total_taches, f"{nb_critiques} critiques")
    k2.metric("Jours / Homme",    f"{total_jh} j/h")
    k3.metric("Budget RH reel",   f"{int(total_cout):,} EUR".replace(",", " "))
    k4.metric("Duree planifiee",  f"{sem_max} semaines")
    k5.metric("Ecart budget",
              f"{int(total_cout - BUDGET_VALIDE):+,} EUR".replace(",", " "),
              delta_color="inverse" if total_cout > BUDGET_VALIDE else "normal")

    st.markdown("---")

    # ── Gantt par ressource ──────────────────────────────────
    st.markdown("#### Gantt par ressource")
    st.caption(
        "Chaque ligne = 1 ressource | Barres = taches affectees | "
        "Bordure rouge = tache sur le chemin critique | Mis a jour en temps reel"
    )
    st.plotly_chart(
        build_gantt_ressources(taches, equipe_index, date_debut, jps),
        use_container_width=True,
    )

    # ── Heatmap de charge ────────────────────────────────────
    with st.expander("Heatmap de charge par ressource et semaine"):
        st.plotly_chart(build_charge_ressource(taches, equipe_index, jps), use_container_width=True)
        st.caption("Intensite = j/h charges par semaine. Semaines vides = ressource disponible.")

    st.markdown("---")

    # ── Avancement par module ────────────────────────────────
    st.markdown("#### Avancement par module fonctionnel aux 3 jalons (S4 / S8 / S14)")
    st.caption(
        "Architecture → Authentification → Catalogue → Depot/Scan → Paiement "
        "→ Livraison → Notifications → QA → DevOps → Lancement"
    )
    st.plotly_chart(build_avancement_chart(sim), use_container_width=True)

    st.markdown("---")

    # ── Prediction de retard ──────────────────────────────────
    p1, p2 = st.columns([3, 2])
    with p1:
        st.markdown("#### Prediction du retard final")
        st.caption(
            "Velocite observee aux jalons S4/S8/S14. "
            "Projection lineaire si la velocite reste constante."
        )
        fig_pred, retard_pred, v_moy = build_prediction_retard(sim)
        st.plotly_chart(fig_pred, use_container_width=True)

    with p2:
        st.markdown("#### Diagnostic")
        st.markdown("")
        st.metric("Velocite observee", f"{v_moy:.1f} taches/sem", "Moyenne jalons S4/S8/S14")
        if retard_pred > 0:
            st.metric("Retard predit a S14", f"{retard_pred:.1f} sem.",
                      delta_color="inverse")
            st.warning(
                f"A la velocite actuelle, le projet se termine a S{14 + retard_pred:.0f} "
                f"(retard estime : {retard_pred:.1f} semaines). "
                f"Actions recommandees : renforcement equipe ou reduction scope "
                f"(Wishes en V2, notifications simplifiees).",
            )
        else:
            st.metric("Retard predit", "0 sem.", "Dans les delais")
            st.success("La velocite actuelle permet une livraison dans les delais.")

        # Simulation impact retard sur budget
        cout_sem_supp = int(total_cout / sem_max) if sem_max > 0 else 0
        st.markdown("---")
        st.markdown("**Simulation : cout d'une semaine de retard**")
        st.metric("Surcout / semaine supplementaire",
                  f"{cout_sem_supp:,} EUR".replace(",", " "),
                  "RH + infrastructure")
        if retard_pred > 0:
            st.metric("Surcout total estime",
                      f"{int(cout_sem_supp * retard_pred):,} EUR".replace(",", " "),
                      delta_color="inverse")

    st.markdown("---")

    # ── Risques survenus — tous jalons ───────────────────────
    st.markdown("#### Risques survenus — tous jalons (S4 / S8 / S14)")
    all_risks = []
    for jname, jdata in sim["jalons"].items():
        for r in jdata["risques"]:
            all_risks.append({
                "Jalon":      jname,
                "ID":         r["id"],
                "Categorie":  r["categorie"],
                "Titre":      r["titre"],
                "Impact":     r["impact"],
                "Statut":     r["statut"],
                "Cout (EUR)": r["cout"],
            })

    df_risks = pd.DataFrame(all_risks)

    def style_risks(row):
        if row["Statut"] == "Resolu":
            return [""] * len(row)
        return ["color:#E24B4A;font-weight:500"] * len(row)

    st.dataframe(
        df_risks.style.apply(style_risks, axis=1).format({"Cout (EUR)": "{:,}"}),
        use_container_width=True, hide_index=True,
    )
    total_cout_risques = df_risks["Cout (EUR)"].sum()
    en_cours           = df_risks[df_risks["Statut"] != "Resolu"].shape[0]
    rc1, rc2, rc3 = st.columns(3)
    rc1.metric("Risques total", len(all_risks))
    rc2.metric("Cout total risques survenus",
               f"{total_cout_risques:,} EUR".replace(",", " "))
    rc3.metric("Encore en cours", en_cours,
               delta_color="inverse" if en_cours > 0 else "normal")

    st.markdown("---")

    # ── Tableau complet des taches ────────────────────────────
    with st.expander("Tableau complet des taches avec couts reels"):
        rows = []
        for t in sorted(taches, key=lambda x: x["id"]):
            res  = equipe_index.get(t["res"], {})
            jh   = calcul_jh_tache(t, jps)
            cout = calcul_cout_tache(t, equipe_index, jps)
            rows.append({
                "#":         t["id"],
                "Tache":     t["nom"],
                "Categorie": t["cat"],
                "Ressource": res.get("label", t["res"]),
                "S.debut":   t["semaine"],
                "Duree":     t["duree"],
                "J/H":       jh,
                "Cout (EUR)": int(cout),
                "Critique":  "!" if t.get("critique") else "",
            })
        df_t = pd.DataFrame(rows)

        def style_critique(row):
            if row["Critique"] == "!":
                return [""] * (len(row) - 2) + ["color:#E24B4A;font-weight:500", ""]
            return [""] * len(row)

        st.dataframe(
            df_t.style.apply(style_critique, axis=1).format({"Cout (EUR)": "{:,}"}),
            use_container_width=True, hide_index=True,
        )
        st.caption(
            f"Total : {sum(r['J/H'] for r in rows)} j/h | "
            f"{sum(r['Cout (EUR)'] for r in rows):,} EUR cout employeur"
        )
