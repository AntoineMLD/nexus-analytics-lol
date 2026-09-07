# ─── Image de base ────────────────────────────────────────────────────────────
# python:3.11-slim : image légère, compatible avec toutes les dépendances GCP.
# On fixe la version mineure pour la reproductibilité.
FROM python:3.11-slim

# ─── Variables d'environnement ────────────────────────────────────────────────
# PORT : Cloud Run injecte cette variable — on la respecte pour que
#        uvicorn écoute sur le bon port. Valeur par défaut locale : 8080.
ENV PORT=8080 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# ─── Dépendances système ──────────────────────────────────────────────────────
# Pas de build-essential ni gcc nécessaires — toutes les dépendances Python
# ont des wheels précompilés disponibles sur PyPI.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ─── Répertoire de travail ────────────────────────────────────────────────────
WORKDIR /app

# ─── Installation des dépendances ────────────────────────────────────────────
# On copie pyproject.toml en premier pour profiter du cache Docker :
# si les dépendances ne changent pas, cette couche n'est pas reconstruite.
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
        fastapi \
        uvicorn \
        google-cloud-bigquery \
        google-cloud-storage \
        google-api-python-client \
        pydantic-settings \
        httpx

# ─── Code source ─────────────────────────────────────────────────────────────
# On copie uniquement les packages nécessaires à l'API (pas les tests, ni dbt).
COPY api/ ./api/
COPY ingestion/ ./ingestion/

# ─── Utilisateur non-root ─────────────────────────────────────────────────────
# Bonne pratique de sécurité : Cloud Run s'exécute déjà sans root,
# mais l'expliciter ici renforce la posture de sécurité locale.
RUN useradd --no-create-home --shell /bin/false appuser
USER appuser

# ─── Démarrage ────────────────────────────────────────────────────────────────
# --workers 1 : Cloud Run scale horizontalement (plusieurs instances),
# pas besoin de plusieurs workers par conteneur.
# --host 0.0.0.0 : écoute sur toutes les interfaces réseau (requis dans Docker).
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port $PORT --workers 1"]
