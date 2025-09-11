#!/usr/bin/env python3
"""
Migrate legacy output folders to unified output/ structure.

Mappings:
 - batch_output_meeting/ -> output/batch/
 - batch_output/         -> output/batch/
 - hybrid_output_meeting/-> output/hybrid_meeting/
 - hybrid_output/        -> output/hybrid/
 - .transient/           -> output/.transient/

The script moves files recursively, preserves sub-structure, and avoids
overwriting by adding numeric suffix when needed.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MAPPINGS = [
    (ROOT / 'batch_output_meeting', ROOT / 'output' / 'batch'),
    (ROOT / 'batch_output',         ROOT / 'output' / 'batch'),
    (ROOT / 'hybrid_output_meeting',ROOT / 'output' / 'hybrid_meeting'),
    (ROOT / 'hybrid_output',        ROOT / 'output' / 'hybrid'),
    (ROOT / '.transient',           ROOT / 'output' / '.transient'),
]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def unique_path(dest: Path) -> Path:
    if not dest.exists():
        return dest
    stem = dest.stem
    suffix = dest.suffix
    parent = dest.parent
    i = 1
    while True:
        cand = parent / f"{stem} ({i}){suffix}"
        if not cand.exists():
            return cand
        i += 1


def move_tree(src: Path, dst_base: Path) -> tuple[int, int]:
    """Move files recursively from src to dst_base, preserving subdirs.
    Returns (files_moved, dirs_created).
    """
    files_moved = 0
    dirs_created = 0
    for root, dirs, files in os.walk(src):
        rel = Path(root).relative_to(src)
        target_dir = dst_base / rel
        if not target_dir.exists():
            ensure_dir(target_dir)
            dirs_created += 1
        for name in files:
            src_file = Path(root) / name
            dst_file = target_dir / name
            dst_file = unique_path(dst_file)
            try:
                shutil.move(str(src_file), str(dst_file))
                files_moved += 1
            except Exception as e:
                print(f"[WARN] Failed to move {src_file} -> {dst_file}: {e}")
    return files_moved, dirs_created


def cleanup_empty_dirs(path: Path) -> int:
    """Remove empty directories under path. Returns count removed."""
    removed = 0
    for dirpath, dirnames, filenames in os.walk(path, topdown=False):
        d = Path(dirpath)
        try:
            if not any(d.iterdir()):
                d.rmdir()
                removed += 1
        except Exception:
            pass
    return removed


def main() -> int:
    total_moved = 0
    total_dirs = 0
    total_removed = 0
    any_found = False

    # Ensure base output directories exist
    for base in [ROOT / 'output' / 'batch', ROOT / 'output' / 'hybrid', ROOT / 'output' / 'hybrid_meeting', ROOT / 'output' / 'live', ROOT / 'output' / '.transient']:
        ensure_dir(base)

    for src, dst in MAPPINGS:
        if not src.exists():
            continue
        any_found = True
        print(f"[INFO] Migrating {src.relative_to(ROOT)} -> {dst.relative_to(ROOT)}")
        ensure_dir(dst)

        # If src is a file, move directly
        if src.is_file():
            dst_file = unique_path(dst / src.name) if dst.is_dir() else unique_path(dst)
            shutil.move(str(src), str(dst_file))
            print(f"[OK] Moved file: {src} -> {dst_file}")
            total_moved += 1
            continue

        moved, created = move_tree(src, dst)
        total_moved += moved
        total_dirs += created
        removed = cleanup_empty_dirs(src)
        total_removed += removed
        # Remove the root directory if empty after cleanup
        try:
            if src.exists() and not any(src.rglob('*')):
                src.rmdir()
                total_removed += 1
        except Exception:
            pass

    if not any_found:
        print("[INFO] No legacy output directories found. Nothing to migrate.")
    else:
        print("\n=== Migration Summary ===")
        print(f"Files moved    : {total_moved}")
        print(f"Dirs created   : {total_dirs}")
        print(f"Legacy dirs rm : {total_removed}")
        print(f"Output root    : {(ROOT / 'output').resolve()}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

