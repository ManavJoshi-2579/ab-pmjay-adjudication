"""Pipeline smoke tests."""

from __future__ import annotations

from pathlib import Path

from main import build_pipeline


def test_pipeline_runs_end_to_end(tmp_path: Path) -> None:
    """Pipeline should produce a final adjudication payload."""
    for name in ["claim_form.png", "discharge_summary.png", "procedure_note.png", "bill.png"]:
        (tmp_path / name).touch()

    payload = build_pipeline().run([str(path) for path in tmp_path.iterdir()], claim_id="test-claim")
    assert payload["claim_id"] == "test-claim"
    assert payload["decision"]["status"] in {"Pass", "Conditional", "Fail"}
    assert "timeline" in payload
    assert "decision" in payload
    assert "optimization" in payload
    assert Path("outputs/debug/test-claim_debug.json").exists()
    assert Path("outputs/visualizations/test-claim_evidence.txt").exists()
    assert Path("data/cache/analytics/test-claim_optimization.json").exists()
