"""Ingest package — parsers, chunking, pipeline."""

from app.ingest.pipeline import ingest_fixtures, ingest_file, ingest_paths

__all__ = ["ingest_fixtures", "ingest_file", "ingest_paths"]
