# config/blog_config.py

# === MODÈLES OPENAI CORRIGÉS (modèles fonctionnels uniquement) ===
OPENAI_MODELS = [
    "gpt-4o-mini",           # Modèle standard fonctionnel
    "gpt-4.1-nano",          # À tester si disponible
    "gpt-4.1-mini",          # À tester si disponible
    # "gpt-5-nano-2025-08-07",  # DÉSACTIVÉ: retour vide
    # "gpt-5-mini-2025-08-07",  # DÉSACTIVÉ: potentiellement problématique
    # "o3-mini",                # DÉSACTIVÉ: erreur paramètre max_tokens
    # "04-mini"                 # DÉSACTIVÉ: modèle inexistant (404)
]

# === PARAMÈTRES PAR MODÈLE ACTIF ===
OPENAI_MODEL_PARAM_MAP = {
    "gpt-4o-mini": {
        "token_param": "max_completion_tokens",
        "temperature_allowed": True
    },
    "gpt-4.1-nano": {
        "token_param": "max_completion_tokens",
        "temperature_allowed": True
    },
    "gpt-4.1-mini": {
        "token_param": "max_completion_tokens",
        "temperature_allowed": True
    }
    # Modèles désactivés conservés pour référence:
    # "gpt-5-nano-2025-08-07": {"token_param": "max_completion_tokens", "temperature_allowed": False}
    # "o3-mini": {"token_param": "max_completion_tokens", "temperature_allowed": True}  # CORRIGÉ: max_completion_tokens
    # "04-mini": modèle inexistant
}

# === TES MODÈLES GEMINI (exactement comme tu les as écrits) ===
GEMINI_MODELS = [
    "gemini-2.5-flash-lite-preview-06-17",
    "gemini-2.0-flash-001",
    "gemini-2.5-flash",
    "gemini-2.5-pro"
]