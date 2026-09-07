"""Leaguepedia wiki scraping module.

Scrapes raw wiki pages to extract SoloqueueIds (Riot IDs) for LFL players.
Uses mwrogue EsportsClient for authenticated access.

Main entry point:
    uv run python -m ingestion.leaguepedia_wiki.ingest
"""
