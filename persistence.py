"""
Persistance locale via fichier JSON.

Choix technique : fichier JSON dans le même répertoire que l'app.
- Simple, sans dépendance externe (pas de SQLite, pas de Redis)
- Compatible Streamlit Cloud (le fichier persiste tant que le pod tourne)
- Rechargement automatique au démarrage : si le fichier existe, les données
  sont restaurées ; sinon les valeurs par défaut sont utilisées.

Limitation : la persistance est liée à la durée de vie du pod Streamlit.
Sur Streamlit Community Cloud, un pod peut redémarrer (après ~1h d'inactivité).
Pour une persistance absolue, prévoir une migration vers st.session_state +
Streamlit Cloud secrets + Google Sheets ou une BDD externe.

Usage :
    from persistence import save_state, load_state
    save_state()          # appelé après chaque modification
    data = load_state()   # appelé au démarrage
"""

import json
import os
from pathlib import Path
from copy import deepcopy

# Chemin du fichier de sauvegarde — même dossier que l'app
SAVE_FILE = Path(__file__).parent / "projet_state.json"


def save_state(state: dict) -> None:
    """
    Sérialise et écrit l'état complet en JSON.
    Écrasement atomique via un fichier temporaire pour éviter
    la corruption en cas d'interruption pendant l'écriture.
    """
    tmp = SAVE_FILE.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        tmp.replace(SAVE_FILE)   # remplacement atomique sur POSIX
    except Exception as e:
        # Ne jamais faire planter l'app pour un échec de sauvegarde
        print(f"[persistence] Erreur sauvegarde : {e}")
        if tmp.exists():
            tmp.unlink()


def load_state() -> dict | None:
    """
    Charge l'état depuis le fichier JSON.
    Retourne None si le fichier n'existe pas ou est corrompu.
    """
    if not SAVE_FILE.exists():
        return None
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[persistence] Erreur chargement : {e}")
        return None


def delete_state() -> None:
    """Supprime le fichier de sauvegarde (utilisé par le bouton Reset)."""
    if SAVE_FILE.exists():
        SAVE_FILE.unlink()
