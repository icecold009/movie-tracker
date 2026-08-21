import json

from scripts.validate_release import validate_release_manifest


def test_release_manifest_validation_reports_missing_provenance(tmp_path):
    manifest = tmp_path / "release_manifest.json"
    manifest.write_text(json.dumps({"git_commit": "abc"}), encoding="utf-8")

    errors = validate_release_manifest(manifest, base_dir=tmp_path)

    assert "manifest.generated_at_utc is required" in errors
    assert "manifest.evaluation must be a list" in errors
    assert "manifest.artifacts must be an object" in errors


def test_release_manifest_validation_accepts_structural_evidence(tmp_path):
    manifest = tmp_path / "release_manifest.json"
    manifest.write_text(json.dumps({
        "git_commit": "abc",
        "generated_at_utc": "2026-08-19T00:00:00Z",
        "evaluation": [],
        "artifacts": {},
    }), encoding="utf-8")

    assert validate_release_manifest(manifest, base_dir=tmp_path) == []
