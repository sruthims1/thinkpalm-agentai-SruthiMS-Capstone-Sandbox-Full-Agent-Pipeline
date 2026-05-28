"""
File tools — read feature specs and write generated test files.

Output folder layout:
  outputs/
    gherkin/      *.feature          (Gherkin BDD scenarios)
    typescript/   *.spec.ts, *.ts    (Playwright TypeScript tests + config)
    coverage/     *_coverage_report.json
    audit/        *_audit_report.json
"""

import os
from pathlib import Path
from datetime import datetime

BASE_DIR     = Path(__file__).resolve().parents[2]
FEATURES_DIR = BASE_DIR / "sample_features"
OUTPUTS_DIR  = BASE_DIR / "outputs"

GHERKIN_DIR    = OUTPUTS_DIR / "gherkin"
TYPESCRIPT_DIR = OUTPUTS_DIR / "typescript"
COVERAGE_DIR   = OUTPUTS_DIR / "coverage"
AUDIT_DIR      = OUTPUTS_DIR / "audit"

FEATURES_DIR.mkdir(exist_ok=True)
for d in (GHERKIN_DIR, TYPESCRIPT_DIR, COVERAGE_DIR, AUDIT_DIR):
    d.mkdir(parents=True, exist_ok=True)


def _subdir_for(filename: str, file_type: str) -> Path:
    """Return the correct output subdirectory for a file."""
    if file_type == "feature":
        return GHERKIN_DIR
    if file_type == "playwright":
        return TYPESCRIPT_DIR
    if file_type == "report":
        if "audit" in filename.lower():
            return AUDIT_DIR
        return COVERAGE_DIR
    return OUTPUTS_DIR


def read_feature_file(filename: str) -> dict:
    path = FEATURES_DIR / filename
    if not path.exists():
        return {
            "success": False,
            "error":   f"File '{filename}' not found in sample_features/",
            "available_files": list_feature_files()["files"],
        }
    content = path.read_text(encoding="utf-8")
    return {
        "success":    True,
        "filename":   filename,
        "content":    content,
        "char_count": len(content),
        "line_count": content.count("\n") + 1,
    }


def write_test_file(filename: str, content: str, file_type: str = "feature") -> dict:
    if file_type == "playwright":
        norm = filename.replace("\\", "/").lower()
        ext  = ".ts" if ("config" in norm) else ".spec.ts"
    else:
        ext = {"feature": ".feature", "report": ".json"}.get(file_type, ".txt")

    if not filename.endswith(ext):
        filename = filename.replace(" ", "_").lower() + ext

    dest = _subdir_for(filename, file_type) / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    return {
        "success":    True,
        "filepath":   str(dest),
        "filename":   filename,
        "file_type":  file_type,
        "char_count": len(content),
        "written_at": datetime.utcnow().isoformat(),
    }


def list_feature_files() -> dict:
    files = [f.name for f in FEATURES_DIR.glob("*.txt")]
    return {
        "success":      True,
        "files":        sorted(files),
        "count":        len(files),
        "features_dir": str(FEATURES_DIR),
    }


def list_generated_tests() -> dict:
    feature_files  = sorted(f.name for f in GHERKIN_DIR.glob("*.feature"))
    spec_files     = sorted(f.name for f in TYPESCRIPT_DIR.glob("*.spec.ts"))
    config_files   = sorted(f.name for f in TYPESCRIPT_DIR.glob("*.ts") if not f.name.endswith(".spec.ts"))
    coverage_files = sorted(f.name for f in COVERAGE_DIR.glob("*.json"))
    audit_files    = sorted(f.name for f in AUDIT_DIR.glob("*.json"))
    return {
        "success":          True,
        "feature_files":    feature_files,
        "playwright_files": spec_files + config_files,
        "coverage_files":   coverage_files,
        "audit_files":      audit_files,
        "report_files":     coverage_files + audit_files,
        "total": len(feature_files) + len(spec_files) + len(config_files) + len(coverage_files) + len(audit_files),
    }


def read_generated_file(filename: str) -> dict:
    for search_dir in (GHERKIN_DIR, TYPESCRIPT_DIR, COVERAGE_DIR, AUDIT_DIR, OUTPUTS_DIR):
        path = search_dir / filename
        if path.exists():
            return {"success": True, "filename": filename, "content": path.read_text(encoding="utf-8")}
    return {"success": False, "error": f"File '{filename}' not found in outputs/"}
