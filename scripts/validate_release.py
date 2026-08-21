"""Validate release evidence metadata without contacting production services."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def current_commit(base_dir: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=base_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def validate_release_manifest(
    manifest_path: Path,
    *,
    base_dir: Path,
    require_current_commit: bool = False,
) -> list[str]:
    """Return actionable evidence errors for a tracked release manifest.

    This deliberately does not probe Vercel, Supabase, or credentials. Those
    remain separate live gates and must be recorded with their own evidence.
    """

    errors: list[str] = []
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"manifest does not exist: {manifest_path}"]
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"manifest cannot be read: {exc}"]

    if not isinstance(payload, dict):
        return ["manifest root must be an object"]
    if not str(payload.get("git_commit", "")).strip():
        errors.append("manifest.git_commit is required")
    if not str(payload.get("generated_at_utc", "")).strip():
        errors.append("manifest.generated_at_utc is required")
    if not isinstance(payload.get("evaluation"), list):
        errors.append("manifest.evaluation must be a list")
    if not isinstance(payload.get("artifacts"), dict):
        errors.append("manifest.artifacts must be an object")

    if require_current_commit:
        try:
            commit = current_commit(base_dir)
        except (OSError, subprocess.CalledProcessError) as exc:
            errors.append(f"cannot resolve current Git commit: {exc}")
        else:
            if payload.get("git_commit") != commit:
                errors.append(
                    f"manifest commit {payload.get('git_commit')} does not match current commit {commit}"
                )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("docs/release_manifest.json"))
    parser.add_argument("--require-current-commit", action="store_true")
    args = parser.parse_args()
    errors = validate_release_manifest(
        args.manifest,
        base_dir=Path.cwd(),
        require_current_commit=args.require_current_commit,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Release manifest is structurally valid: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
