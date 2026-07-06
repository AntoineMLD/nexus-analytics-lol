"""Orchestration du pipeline Nexus Analytics.

Enchaîne les étapes dans l'ordre :
  1. Ingestion Bronze (Leaguepedia Cargo API)
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
"""

import argparse
import subprocess
import sys
from datetime import UTC, datetime

from ingestion.utils import logger, send_discord_notification

# Tables Silver à charger dans BigQuery dans cet ordre.
# L'ordre compte : stg_lfl_drafts dépend de lfl_matches en dbt,
# mais tous peuvent être chargés en parallèle dans BQ.
SILVER_TABLES: list[tuple[str, str]] = [
    ("leaguepedia", "lfl_matches"),
    ("leaguepedia", "lfl_player_stats"),
    ("leaguepedia", "lfl_players"),
    ("leaguepedia", "lfl_drafts"),
]


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


def run_ingestion() -> bool:
    """Step 1 — Ingest all Leaguepedia Cargo tables to GCS Bronze.

    Returns True on success, False on failure.
    """
    logger.info("=== Step 1/4 : Bronze ingestion ===")
    code = _run(
        ["uv", "run", "python", "-m", "ingestion.leaguepedia.ingest"],
        "ingestion",
    )
    return code == 0


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
            if not run_ingestion():
                failures.append("ingestion")

        if not run_silver_transforms(args.date):
            failures.append("silver_transforms")

        if not run_bq_loaders(args.date):
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
