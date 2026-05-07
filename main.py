"""Application entrypoint."""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.core.pipeline import ClaimPipeline
from src.utils.io import collect_claim_directories, collect_input_files, ensure_dirs, load_json, load_yaml, save_json, save_text


def build_pipeline() -> ClaimPipeline:
    """Build the configured pipeline instance."""
    config = load_yaml("configs/base.yaml")
    thresholds = load_yaml("configs/thresholds.yaml")
    rules = load_json("configs/rules.json")
    stg_dir = Path(config["paths"].get("stg_dir", "data/stg"))
    discovered_stg = sorted(
        str(path)
        for path in stg_dir.glob("**/*")
        if path.is_file() and path.suffix.lower() in {".txt", ".pdf", ".md"}
    )
    existing_stg = {
        item.get("path") if isinstance(item, dict) else str(item)
        for item in rules.get("stg_documents", [])
    }
    for path_value in discovered_stg:
        if path_value not in existing_stg:
            rules.setdefault("stg_documents", []).append({"path": path_value})
    ensure_dirs(
        [
            config["paths"]["input_dir"],
            config["paths"]["cache_dir"],
            config["paths"]["synthetic_dir"],
            config["paths"].get("stg_dir", "data/stg"),
            config["pipeline"]["cache"]["ocr_dir"],
            config["pipeline"]["cache"]["preprocess_dir"],
            config["pipeline"]["cache"]["analytics_dir"],
            config["pipeline"]["outputs"]["final_dir"],
            config["pipeline"]["outputs"]["debug_dir"],
            config["pipeline"]["outputs"]["logs_dir"],
            config["pipeline"]["outputs"]["visualizations_dir"],
        ]
    )
    return ClaimPipeline(config=config, thresholds=thresholds, rules=rules)


def _safe_claim_id(directory: Path) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", directory.name).strip("-_.")
    return cleaned or "root_claim"


def _claim_type_for(directory: Path) -> str:
    metadata_path = directory / "claim.json"
    if metadata_path.exists():
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            claim_type = str(payload.get("claim_type", "")).strip()
            if claim_type:
                return claim_type
        except json.JSONDecodeError:
            pass
    lowered = directory.name.lower()
    if any(token in lowered for token in ("medical", "fever")):
        return "medical_claim"
    sidecar_text = " ".join(path.read_text(encoding="utf-8", errors="ignore").lower() for path in directory.glob("*.txt"))
    if "procedure note" in sidecar_text or "operation note" in sidecar_text:
        return "surgery_claim"
    if "fever duration" in sidecar_text or "hemoglobin" in sidecar_text or "diagnosis fever" in sidecar_text:
        return "medical_claim"
    return "surgery_claim"


def _mirror_claim_outputs(config: dict, claim_id: str) -> None:
    outputs_root = Path(config["paths"].get("output_dir", "outputs"))
    claim_root = outputs_root / claim_id
    claim_root.mkdir(parents=True, exist_ok=True)
    final_dir = Path(config["pipeline"]["outputs"]["final_dir"])
    debug_dir = Path(config["pipeline"]["outputs"]["debug_dir"])
    visualization_dir = Path(config["pipeline"]["outputs"].get("visualizations_dir", "outputs/visualizations"))
    final_path = final_dir / f"{claim_id}.json"
    debug_path = debug_dir / f"{claim_id}_debug.json"
    visualization_path = visualization_dir / f"{claim_id}_evidence.txt"
    if final_path.exists():
        save_json(claim_root / "final.json", load_json(final_path))
    if debug_path.exists():
        save_json(claim_root / "debug.json", load_json(debug_path))
    if visualization_path.exists():
        save_text(claim_root / "evidence.txt", visualization_path.read_text(encoding="utf-8"))


def main() -> None:
    """Run the pipeline against documents in the configured input directory."""
    pipeline = build_pipeline()
    input_root = Path("data/input")
    claim_dirs = collect_claim_directories(input_root)
    if not claim_dirs:
        sample_dir = input_root / "claim_1"
        sample_dir.mkdir(parents=True, exist_ok=True)
        sample = sample_dir / "claim_form.png"
        sample.touch(exist_ok=True)
        claim_dirs = [sample_dir]

    summaries: list[str] = []
    for directory in claim_dirs:
        files = [str(path) for path in collect_input_files(directory)]
        if not files:
            continue
        claim_id = _safe_claim_id(directory)
        claim_type = _claim_type_for(directory)
        payload = pipeline.run(files, claim_id=claim_id, claim_type=claim_type)
        _mirror_claim_outputs(pipeline.config, claim_id)
        summaries.append(f"{claim_id} -> {payload['decision']['status']} ({payload['decision']['confidence']})")
    for line in summaries:
        print(f"Claim {line}")


if __name__ == "__main__":
    main()
