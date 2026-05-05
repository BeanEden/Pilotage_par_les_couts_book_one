"""
Données de référence du projet Book One — « Tous les livres à 1 € ».

Choix technique : module Python pur sans I/O fichier.
Les structures sont des listes de dicts compatibles pandas et json.dumps
pour la sérialisation en session_state Streamlit.
"""

from copy import deepcopy

# ─────────────────────────────────────────────────────────────
# CONFIGURATION PROJET
# ─────────────────────────────────────────────────────────────

PROJECT_CONFIG = {
    "nom": "Book One — MVP Mobile",
    "date_debut": "2025-01-06",   # Lundi 6 janvier 2025 (semaine 2 calendaire)
    "jours_par_semaine": 5,
    "description": (
        "MVP de l'application mobile Book One : scan de 3 livres à déposer, "
        "catalogue géolocalisé, achat à 1 €, messagerie RDV, notifications."
    ),
}

# ─────────────────────────────────────────────────────────────
# RÉFÉRENTIELS RH
# ─────────────────────────────────────────────────────────────

# Jours ouvrés annuels par type de contrat (base légale FR)
JOURS_OUVRES_PAR_AN = {
    "CDI":       218,
    "STAGIAIRE": 151,
    "ALTERNANT": 218,
    "FREELANCE": 200,
}

# Taux de charges patronales 2024 par statut conventionnel
STATUTS_CONVENTION = ["Cadre", "ETAM", "Ouvrier", "Stagiaire", "Alternant", "Freelance"]

TAUX_CHARGES_PATRONALES = {
    "Cadre":      0.45,
    "ETAM":       0.42,
    "Ouvrier":    0.40,
    "Stagiaire":  0.00,
    "Alternant":  0.10,
    "Freelance":  0.00,
}

STATUT_DEFAULT_PAR_TYPE = {
    "CDI":       "Cadre",
    "STAGIAIRE": "Stagiaire",
    "ALTERNANT": "Alternant",
    "FREELANCE": "Freelance",
}

# ─────────────────────────────────────────────────────────────
# ÉQUIPE TECHNIQUE — 9 profils
# Respect de l'énoncé : au moins 1 stagiaire, 1 alternant, 1 freelance.
# Salaires calibrés pour une startup early-stage parisienne 2025.
# ─────────────────────────────────────────────────────────────

EQUIPE = [
    {"id": "PM",  "label": "Chef de projet",         "type": "CDI",       "statut": "Cadre",     "salaire_brut_annuel": 58000,  "couleur": "7F77DD"},
    {"id": "TL",  "label": "Tech Lead",               "type": "CDI",       "statut": "Cadre",     "salaire_brut_annuel": 72000,  "couleur": "534AB7"},
    {"id": "BE",  "label": "Dev Back-End",             "type": "CDI",       "statut": "ETAM",      "salaire_brut_annuel": 52000,  "couleur": "1D9E75"},
    {"id": "MOB", "label": "Dev Mobile (Flutter)",     "type": "CDI",       "statut": "ETAM",      "salaire_brut_annuel": 55000,  "couleur": "378ADD"},
    {"id": "UX",  "label": "UX Designer",              "type": "CDI",       "statut": "ETAM",      "salaire_brut_annuel": 48000,  "couleur": "BA7517"},
    {"id": "QA",  "label": "QA Engineer",              "type": "CDI",       "statut": "ETAM",      "salaire_brut_annuel": 45000,  "couleur": "D4537E"},
    {"id": "STG", "label": "Stagiaire Dev",            "type": "STAGIAIRE", "statut": "Stagiaire", "salaire_brut_annuel": 7800,   "couleur": "888780"},
    {"id": "ALT", "label": "Alternant Dev",            "type": "ALTERNANT", "statut": "Alternant", "salaire_brut_annuel": 16000,  "couleur": "B4B2A9"},
    {"id": "FRL", "label": "Freelance Paiement/Sécu", "type": "FREELANCE", "statut": "Freelance", "salaire_brut_annuel": 130000, "couleur": "E24B4A"},
]

EQUIPE_INDEX = {m["id"]: m for m in EQUIPE}


def calcul_taux_jour(membre: dict) -> int:
    """
    Taux journalier coût-employeur = (salaire_brut_annuel / jours_ouvrés) × (1 + taux_charges).
    Arrondi à 10 € par excès — approche conservatrice pour le budget projet.
    Source de vérité unique : tout changement de salaire ou statut se propage
    automatiquement sans re-sync manuelle du champ taux_jour.
    """
    jours     = JOURS_OUVRES_PAR_AN.get(membre["type"], 218)
    taux_ch   = TAUX_CHARGES_PATRONALES.get(membre.get("statut", "ETAM"), 0.42)
    cout_jour = (membre["salaire_brut_annuel"] / jours) * (1 + taux_ch)
    return max(1, round(cout_jour / 10) * 10)


# ─────────────────────────────────────────────────────────────
# TÂCHES ÉLÉMENTAIRES — 28 tâches Book One
#
# Périmètre MVP (énoncé) :
#   - Authentification + mode invité
#   - Catalogue géolocalisé (livres autour de moi)
#   - Dépôt de livres + scan ISBN (3 livres → droit d'achat)
#   - Achat à 1 €, confirmation de remise en main propre, débit
#   - Messagerie in-app (convenir du RDV de remise)
#   - Favoris et wishes (livres souhaités absents du catalogue)
#   - Notifications (vendu, livre souhaité disponible)
#   - QA, DevOps, lancement store
#
# Durée projet : 14 semaines (6 jan → 11 avr 2025)
# ─────────────────────────────────────────────────────────────

TACHES_DEFAULT = [
    # ── Architecture ──────────────────────────────────────────
    {"id":  1, "cat": "Architecture",    "nom": "Définition architecture technique",        "res": "TL",  "semaine": 1,  "duree": 2, "critique": True,  "deps": [],        "complexite": "Haute"},
    {"id":  2, "cat": "Architecture",    "nom": "Setup repo, CI/CD & environnements",       "res": "TL",  "semaine": 1,  "duree": 2, "critique": False, "deps": [],        "complexite": "Moyenne"},
    {"id":  3, "cat": "Architecture",    "nom": "Spécifications fonctionnelles MVP",        "res": "STG", "semaine": 1,  "duree": 3, "critique": False, "deps": [],        "complexite": "Faible"},

    # ── Authentification ──────────────────────────────────────
    {"id":  4, "cat": "Authentification","nom": "Maquettes UX auth + mode invité",          "res": "UX",  "semaine": 3,  "duree": 2, "critique": True,  "deps": [3],       "complexite": "Moyenne"},
    {"id":  5, "cat": "Authentification","nom": "API Auth (register, login, JWT)",           "res": "BE",  "semaine": 3,  "duree": 3, "critique": True,  "deps": [1],       "complexite": "Haute"},
    {"id":  6, "cat": "Authentification","nom": "Mode invité — accès lecture catalogue",    "res": "MOB", "semaine": 5,  "duree": 2, "critique": False, "deps": [5],       "complexite": "Faible"},

    # ── Catalogue géolocalisé ─────────────────────────────────
    {"id":  7, "cat": "Catalogue",       "nom": "Modèle de données livres + géoloc",        "res": "BE",  "semaine": 3,  "duree": 2, "critique": True,  "deps": [1],       "complexite": "Haute"},
    {"id":  8, "cat": "Catalogue",       "nom": "API catalogue — recherche & filtres géo",  "res": "BE",  "semaine": 5,  "duree": 3, "critique": True,  "deps": [7],       "complexite": "Haute"},
    {"id":  9, "cat": "Catalogue",       "nom": "Écran carte — livres autour de moi",       "res": "MOB", "semaine": 6,  "duree": 3, "critique": True,  "deps": [4, 8],    "complexite": "Haute"},
    {"id": 10, "cat": "Catalogue",       "nom": "Écran fiche livre détail",                 "res": "MOB", "semaine": 8,  "duree": 2, "critique": True,  "deps": [9],       "complexite": "Moyenne"},
    {"id": 11, "cat": "Catalogue",       "nom": "Favoris & Wishes (livres souhaités)",      "res": "ALT", "semaine": 8,  "duree": 3, "critique": False, "deps": [8],       "complexite": "Moyenne"},

    # ── Dépôt & Scan livres ───────────────────────────────────
    {"id": 12, "cat": "Depot",           "nom": "Intégration API ISBN (Open Library)",      "res": "BE",  "semaine": 5,  "duree": 2, "critique": True,  "deps": [1],       "complexite": "Moyenne"},
    {"id": 13, "cat": "Depot",           "nom": "Écran scan ISBN (caméra mobile)",          "res": "MOB", "semaine": 6,  "duree": 3, "critique": True,  "deps": [4, 12],   "complexite": "Haute"},
    {"id": 14, "cat": "Depot",           "nom": "Logique crédit : 3 scans → 1 achat dispo","res": "BE",  "semaine": 7,  "duree": 2, "critique": True,  "deps": [12],      "complexite": "Moyenne"},

    # ── Achat & Paiement ──────────────────────────────────────
    {"id": 15, "cat": "Paiement",        "nom": "Intégration Stripe — paiement 1 €",        "res": "FRL", "semaine": 9,  "duree": 3, "critique": True,  "deps": [14],      "complexite": "Haute"},
    {"id": 16, "cat": "Paiement",        "nom": "Écran achat + récap commande",             "res": "MOB", "semaine": 10, "duree": 2, "critique": True,  "deps": [10, 15],  "complexite": "Moyenne"},
    {"id": 17, "cat": "Paiement",        "nom": "Débit conditionnel (après confirmation remise)","res": "BE","semaine": 11,"duree": 2,"critique": True, "deps": [15],      "complexite": "Haute"},
    {"id": 18, "cat": "Paiement",        "nom": "Audit sécurité flux paiement",             "res": "FRL", "semaine": 12, "duree": 2, "critique": True,  "deps": [17],      "complexite": "Haute"},

    # ── Livraison / Remise en main propre ─────────────────────
    {"id": 19, "cat": "Livraison",       "nom": "Messagerie in-app — convenir du RDV",      "res": "BE",  "semaine": 9,  "duree": 3, "critique": False, "deps": [5],       "complexite": "Moyenne"},
    {"id": 20, "cat": "Livraison",       "nom": "Écran messagerie & confirmation RDV",      "res": "MOB", "semaine": 11, "duree": 2, "critique": False, "deps": [9, 19],   "complexite": "Moyenne"},
    {"id": 21, "cat": "Livraison",       "nom": "Confirmation remise en main propre (app)", "res": "MOB", "semaine": 12, "duree": 2, "critique": True,  "deps": [16, 20],  "complexite": "Moyenne"},

    # ── Notifications ─────────────────────────────────────────
    {"id": 22, "cat": "Notifications",   "nom": "Service push notifications (FCM/APNs)",   "res": "BE",  "semaine": 7,  "duree": 3, "critique": False, "deps": [5],       "complexite": "Moyenne"},
    {"id": 23, "cat": "Notifications",   "nom": "Notifs : livre vendu + wish disponible",  "res": "ALT", "semaine": 9,  "duree": 3, "critique": False, "deps": [11, 22],  "complexite": "Faible"},

    # ── QA / Tests ────────────────────────────────────────────
    {"id": 24, "cat": "QA",              "nom": "Tests unitaires back-end",                 "res": "ALT", "semaine": 8,  "duree": 4, "critique": False, "deps": [5, 8, 14],"complexite": "Moyenne"},
    {"id": 25, "cat": "QA",              "nom": "Tests intégration & E2E",                 "res": "QA",  "semaine": 11, "duree": 3, "critique": True,  "deps": [16, 21],  "complexite": "Haute"},

    # ── DevOps / Infra ────────────────────────────────────────
    {"id": 26, "cat": "DevOps",          "nom": "Config staging / prod + monitoring",       "res": "TL",  "semaine": 5,  "duree": 2, "critique": False, "deps": [2],       "complexite": "Moyenne"},
    {"id": 27, "cat": "DevOps",          "nom": "Documentation technique",                 "res": "STG", "semaine": 9,  "duree": 4, "critique": False, "deps": [8, 14],   "complexite": "Faible"},

    # ── Lancement ─────────────────────────────────────────────
    {"id": 28, "cat": "Lancement",       "nom": "Beta test interne + correction bugs",      "res": "QA",  "semaine": 13, "duree": 2, "critique": True,  "deps": [25, 18],  "complexite": "Haute"},
]


def get_taches_default() -> list[dict]:
    """Copie profonde des tâches — évite la mutation de la source lors de l'init session_state."""
    return deepcopy(TACHES_DEFAULT)


def get_equipe_default() -> list[dict]:
    """Copie profonde de l'équipe par défaut."""
    return deepcopy(EQUIPE)


# ─────────────────────────────────────────────────────────────
# CONSTANTES DE PRÉSENTATION
# ─────────────────────────────────────────────────────────────

CATEGORIES = [
    "Architecture", "Authentification", "Catalogue", "Depot",
    "Paiement", "Livraison", "Notifications", "QA", "DevOps", "Lancement"
]

CAT_COULEURS = {
    "Architecture":     "#185FA5",
    "Authentification": "#534AB7",
    "Catalogue":        "#1D9E75",
    "Depot":            "#0F6E56",
    "Paiement":         "#E24B4A",
    "Livraison":        "#BA7517",
    "Notifications":    "#378ADD",
    "QA":               "#D4537E",
    "DevOps":           "#5F5E5A",
    "Lancement":        "#7F77DD",
}

COMPLEXITE_OPTIONS  = ["Faible", "Moyenne", "Haute"]
SENIORITE_OPTIONS   = ["Junior", "Intermédiaire", "Senior", "Expert"]
COMPLEXITE_COULEURS = {"Faible": "#1D9E75", "Moyenne": "#BA7517", "Haute": "#E24B4A"}
TYPE_RESSOURCE_OPTIONS = ["CDI", "STAGIAIRE", "ALTERNANT", "FREELANCE"]

__all__ = [
    "PROJECT_CONFIG", "JOURS_OUVRES_PAR_AN", "STATUTS_CONVENTION",
    "TAUX_CHARGES_PATRONALES", "STATUT_DEFAULT_PAR_TYPE",
    "EQUIPE", "EQUIPE_INDEX", "TACHES_DEFAULT",
    "get_taches_default", "get_equipe_default", "calcul_taux_jour",
    "CATEGORIES", "CAT_COULEURS", "COMPLEXITE_OPTIONS",
    "SENIORITE_OPTIONS", "COMPLEXITE_COULEURS", "TYPE_RESSOURCE_OPTIONS",
]
