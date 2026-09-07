"""Orchestration du pipeline Nexus Analytics.

Enchaîne les étapes dans l'ordre :
  1. Ingestion Bronze — toutes les sources :
     a. Leaguepedia Cargo API (9 tables)
     b. Oracle's Elixir CSV (Google Drive)
     c. Leaguepedia Wiki scraping (SoloqueueIds)
     d. Riot API (PUUIDs + match IDs)
  2. Transforms Silver (normalisation + unpivot)
  3. Chargement BigQuery (GCS Silver → BQ raw)
  4. dbt run (Silver raw → Gold)

Aucun scheduler n'est configuré : ce script se lance manuellement ou via
un Cloud Scheduler / Cloud Run Job.

Usage :
    # Pipeline complet pour la date du jour
    uv run python -m pipeline.orchestration.run_pipeline

    # Seulement les transforms Silver et le chargement BQ (ingestion déjà faite)
    uv run python -m pipeline.orchestration.run_pipeline --skip-ingest

    # Seulement dbt (tout le reste déjà fait)
    uv run python -m pipeline.orchestration.run_pipeline --dbt-only

    # Cibler une date spécifique (utile pour un replay)
    uv run python -m pipeline.orchestration.run_pipeline --date 2026-07-01

    # Ingestion Leaguepedia uniquement (pas Oracle/Riot/wiki)
    uv run python -m pipeline.orchestration.run_pipeline --leaguepedia-only
"""

import argparse
import subprocess
import sys
from datetime import UTC, datetime

from ingestion.utils import gcs_client, logger, send_discord_notification, settings

# Tables Silver à charger dans BigQuery dans cet ordre.
# L'ordre compte : stg_lfl_drafts dépend de lfl_matches en dbt,
# mais tous peuvent être chargés en parallèle dans BQ.
SILVER_TABLES: list[tuple[str, str]] = [
    ("leaguepedia", "lfl_matches"),
    ("leaguepedia", "lfl_player_stats"),
    ("leaguepedia", "lfl_players"),
    ("leaguepedia", "lfl_drafts"),
]


def find_latest_bronze_date() -> str:
    """Detect the most recent ingestion date from GCS Bronze by listing Tournaments files.

    The Tournaments table is always ingested first and is a reliable proxy for
    the latest available Bronze date across all Leaguepedia tables.

    Returns:
        Date string in 'YYYY-MM-DD' format (e.g. '2026-06-04').

    Raises:
        FileNotFoundError: If no Bronze file is found (ingestion never ran).
    """
    prefix = "bronze/leaguepedia/Tournaments/"
    with gcs_client() as client:
        blobs = list(client.bucket(settings.gcs_bucket_name).list_blobs(prefix=prefix))
    if not blobs:
        raise FileNotFoundError(
            f"No Bronze Tournaments file found in gs://{settings.gcs_bucket_name}/{prefix}. "
            "Run ingestion first (without --skip-ingest)."
        )
    latest = max(blobs, key=lambda b: b.name)
    date = latest.name.split("/")[-1].replace(".json", "")
    logger.info("Auto-detected latest Bronze date: %s", date)
    return date


def _run(cmd: list[str], step_name: str) -> int:
    """Run a subprocess command and log the result.

    Returns the exit code. Does NOT raise on failure — the caller decides
    whether to abort or continue.
    """
    logger.info("[%s] Running: %s", step_name, " ".join(cmd))
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        logger.error("[%s] Failed with exit code %d.", step_name, result.returncode)
    else:
        logger.info("[%s] Done.", step_name)
    return result.returncode


def run_ingestion(leaguepedia_only: bool = False) -> bool:
    """Step 1 — Ingest all Bronze sources to GCS.

    Sources ingested (in order):
      - Leaguepedia Cargo API (always)
      - Oracle's Elixir CSV (unless leaguepedia_only)
      - Leaguepedia Wiki scraping for SoloqueueIds (unless leaguepedia_only)
      - Riot API for PUUIDs (unless leaguepedia_only, depends on wiki scraping)

    Args:
        leaguepedia_only: If True, skip Oracle, wiki, and Riot ingestion.

    Returns:
        True if all requested sources succeed, False if any fails.
    """
    logger.info("=== Step 1/4 : Bronze ingestion ===")
    success = True

    # 1a — Leaguepedia Cargo API
    code = _run(
        ["uv", "run", "python", "-m", "ingestion.leaguepedia.ingest"],
        "ingestion:leaguepedia",
    )
    if code != 0:
        success = False

    if leaguepedia_only:
        logger.info("--leaguepedia-only flag set, skipping other sources.")
        return success

    # 1b — Oracle's Elixir CSV
    code = _run(
        ["uv", "run", "python", "-m", "ingestion.oracle_elixir.ingest"],
        "ingestion:oracle_elixir",
    )
    if code != 0:
        success = False

    # 1c — Leaguepedia Wiki scraping (SoloqueueIds)
    # Depends on Silver lfl_players being present (from a previous run).
    code = _run(
        ["uv", "run", "python", "-m", "ingestion.leaguepedia_wiki.ingest"],
        "ingestion:wiki",
    )
    if code != 0:
        success = False

    # 1d — Riot API (PUUIDs + match IDs)
    # Depends on Silver lfl_players (EUW accounts) being present.
    code = _run(
        ["uv", "run", "python", "-m", "ingestion.riot_api.ingest"],
        "ingestion:riot_api",
    )
    if code != 0:
        success = False

    return success


def run_silver_transforms(date: str | None) -> bool:
    """Step 2 — Run all Silver transforms to normalize Bronze data.

    Returns True if all transforms succeed, False if any fails.
    """
    logger.info("=== Step 2/4 : Silver transforms ===")
    transforms = [
        "pipeline.silver_transforms.lfl_matches",
        "pipeline.silver_transforms.lfl_player_stats",
        "pipeline.silver_transforms.lfl_players",
        "pipeline.silver_transforms.lfl_drafts",
    ]
    success = True
    for module in transforms:
        cmd = ["uv", "run", "python", "-m", module]
        if date:
            cmd += ["--date", date]
        code = _run(cmd, module.split(".")[-1])
        if code != 0:
            success = False
            # Continue the other transforms even if one fails
    return success


def run_bq_loaders(date: str | None) -> bool:
    """Step 3 — Load Silver NDJSON files into BigQuery raw dataset.

    Returns True if all loads succeed.
    """
    logger.info("=== Step 3/4 : BigQuery loaders ===")
    success = True
    for source, table in SILVER_TABLES:
        cmd = [
            "uv",
            "run",
            "python",
            "-m",
            "pipeline.loaders.bq_loader",
            "--source",
            source,
            "--table",
            table,
        ]
        if date:
            cmd += ["--date", date]
        code = _run(cmd, f"bq_loader:{table}")
        if code != 0:
            success = False
    return success


def run_dbt() -> bool:
    """Step 4 — Run dbt to materialize Gold tables in BigQuery.

    Returns True on success.
    """
    logger.info("=== Step 4/4 : dbt run ===")
    code = _run(["dbt", "run", "--project-dir", "dbt"], "dbt")
    return code == 0


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Orchestration du pipeline Nexus Analytics (Bronze → Silver → BQ → Gold)."
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Date (YYYY-MM-DD) des fichiers Bronze à traiter. Défaut : la plus récente.",
    )
    parser.add_argument(
        "--skip-ingest",
        action="store_true",
        help="Sauter l'ingestion Bronze (étape 1). Utile si déjà fait.",
    )
    parser.add_argument(
        "--dbt-only",
        action="store_true",
        help="Exécuter uniquement dbt run (étape 4). Utile si BQ est déjà à jour.",
    )
    parser.add_argument(
        "--leaguepedia-only",
        action="store_true",
        help="Ingérer uniquement Leaguepedia Cargo (pas Oracle, wiki, Riot).",
    )
    return parser.parse_args()


def main() -> None:
    """Enchaîne toutes les étapes du pipeline avec notification Discord."""
    args = parse_args()
    started_at = datetime.now(UTC)
    failures: list[str] = []

    logger.info("Pipeline Nexus Analytics démarré — %s", started_at.isoformat())
    send_discord_notification(
        f":rocket: Pipeline démarré — {started_at.strftime('%Y-%m-%d %H:%M UTC')}"
    )

    if args.dbt_only:
        if not run_dbt():
            failures.append("dbt")
    else:
        if not args.skip_ingest:
            if not run_ingestion(leaguepedia_only=args.leaguepedia_only):
                failures.append("ingestion")

        # Résoudre la date Bronze une seule fois pour toutes les étapes suivantes.
        # Si --date n'est pas fourni, on détecte la dernière date disponible en GCS.
        # Sans cette résolution, chaque transform chercherait le fichier du jour
        # (date par défaut = aujourd'hui) et échouerait si l'ingestion n'a pas tourné le même jour.
        resolved_date = args.date
        if resolved_date is None:
            try:
                resolved_date = find_latest_bronze_date()
            except FileNotFoundError as exc:
                logger.error(str(exc))
                failures.append("silver_transforms")
                failures.append("bq_loaders")
                resolved_date = None

        if resolved_date and not run_silver_transforms(resolved_date):
            failures.append("silver_transforms")

        if resolved_date and not run_bq_loaders(resolved_date):
            failures.append("bq_loaders")

        if not run_dbt():
            failures.append("dbt")

    elapsed = (datetime.now(UTC) - started_at).seconds
    minutes, seconds = divmod(elapsed, 60)

    if failures:
        msg = (
            f":x: Pipeline terminé avec erreurs — "
            f"{minutes}m{seconds:02d}s\n"
            f"Étapes en échec : {', '.join(failures)}"
        )
        logger.error(msg)
        send_discord_notification(msg)
        sys.exit(1)
    else:
        msg = f":white_check_mark: Pipeline terminé avec succès — {minutes}m{seconds:02d}s"
        logger.info(msg)
        send_discord_notification(msg)


if __name__ == "__main__":
    main()
