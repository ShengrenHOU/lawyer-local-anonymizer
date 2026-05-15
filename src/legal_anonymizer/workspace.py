from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from legal_anonymizer.config import FOLDERS


@dataclass(frozen=True)
class WorkspacePaths:
    root: Path
    pending: Path
    anonymized: Path
    review_required: Path
    restore_pending: Path
    restored: Path
    mappings: Path


def workspace_paths(root: Path) -> WorkspacePaths:
    root = Path(root)
    return WorkspacePaths(
        root=root,
        pending=root / FOLDERS.pending,
        anonymized=root / FOLDERS.anonymized,
        review_required=root / FOLDERS.review_required,
        restore_pending=root / FOLDERS.restore_pending,
        restored=root / FOLDERS.restored,
        mappings=root / FOLDERS.mappings,
    )


def create_workspace(root: Path) -> WorkspacePaths:
    paths = workspace_paths(root)
    for path in (
        paths.root,
        paths.pending,
        paths.anonymized,
        paths.review_required,
        paths.restore_pending,
        paths.restored,
        paths.mappings,
    ):
        path.mkdir(parents=True, exist_ok=True)
    return paths
