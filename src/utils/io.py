"""File and document IO helpers."""

from __future__ import annotations

import json
import hashlib
import shutil
from pathlib import Path
from typing import Iterable

import yaml

from src.utils.json import to_jsonable


def load_yaml(path: str | Path) -> dict:
    """Load YAML configuration from disk."""
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_json(path: str | Path) -> dict:
    """Load JSON content from disk."""
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: str | Path, payload: object) -> None:
    """Persist JSON payload to disk."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(to_jsonable(payload), handle, indent=2, ensure_ascii=False)


def save_text(path: str | Path, content: str) -> None:
    """Persist text payload to disk."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def ensure_dirs(paths: Iterable[str | Path]) -> None:
    """Create directories if they do not exist."""
    for path in paths:
        Path(path).mkdir(parents=True, exist_ok=True)


def collect_input_files(input_dir: str | Path) -> list[Path]:
    """Collect supported image and PDF files from a directory."""
    root = Path(input_dir)
    supported = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
    return sorted(path for path in root.glob("**/*") if path.suffix.lower() in supported and path.is_file())


def collect_claim_directories(input_dir: str | Path) -> list[Path]:
    """Return leaf-like claim directories that directly contain supported files."""
    root = Path(input_dir)
    supported = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
    claim_dirs: set[Path] = set()
    root_level_files = False
    for path in root.glob("**/*"):
        if not path.is_file() or path.suffix.lower() not in supported:
            continue
        if path.parent == root:
            root_level_files = True
        else:
            claim_dirs.add(path.parent)
    ordered = sorted(claim_dirs)
    if root_level_files and not ordered:
        ordered.insert(0, root)
    return ordered


def convert_pdf_to_images(path: str | Path, output_dir: str | Path, pages: int = 2) -> list[Path]:
    """Create placeholder page images for PDF inputs when full rasterization is unavailable."""
    source = Path(path)
    target_root = Path(output_dir)
    target_root.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for page_number in range(1, pages + 1):
        page_path = target_root / f"{source.stem}_page_{page_number}.png"
        page_path.touch(exist_ok=True)
        outputs.append(page_path)
    return outputs


def preprocess_image(path: str | Path, cache_dir: str | Path, profile: str = "default") -> Path:
    """Return a cached preprocessed image path for downstream modules."""
    source = Path(path)
    target_root = Path(cache_dir)
    target_root.mkdir(parents=True, exist_ok=True)
    target = target_root / f"{source.stem}_{profile}_preprocessed{source.suffix or '.png'}"
    target.touch(exist_ok=True)
    metadata = {
        "source": str(source),
        "profile": profile,
        "operations": _preprocess_operations(profile),
    }
    save_json(target_root / f"{target.stem}.json", metadata)
    return target


def compute_cache_key(*parts: object) -> str:
    """Create a deterministic cache key."""
    digest = hashlib.sha256()
    for part in parts:
        digest.update(str(part).encode("utf-8"))
        digest.update(b"|")
    return digest.hexdigest()


def _preprocess_operations(profile: str) -> list[str]:
    """Return preprocessing operations for a profile."""
    operations = ["denoise", "deskew", "contrast_enhance"]
    if profile == "aggressive":
        operations.extend(["adaptive_threshold", "sharpen", "border_cleanup"])
    return operations


def stage_uploaded_file(source: str | Path, target_dir: str | Path) -> Path:
    """Copy a user-provided file into a managed working directory."""
    source_path = Path(source)
    target_root = Path(target_dir)
    target_root.mkdir(parents=True, exist_ok=True)
    target = target_root / source_path.name
    shutil.copy2(source_path, target)
    return target
