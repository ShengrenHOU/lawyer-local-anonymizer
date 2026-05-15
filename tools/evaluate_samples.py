from __future__ import annotations

import argparse
import json
from pathlib import Path

from legal_anonymizer.document_io import read_text_document
from legal_anonymizer.pipeline import anonymize_file
from legal_anonymizer.workspace import create_workspace


def evaluate(paths: list[Path], output_root: Path) -> list[dict[str, object]]:
    workspace = create_workspace(output_root)
    results: list[dict[str, object]] = []

    for source in paths:
        local_source = workspace.pending / source.name
        local_source.write_bytes(source.read_bytes())
        original_text = read_text_document(local_source)
        result = anonymize_file(local_source, workspace)
        anonymized_text = read_text_document(result.output_path)
        placeholders = anonymized_text.count("[[")
        original_length = len(original_text)
        anonymized_length = len(anonymized_text)
        result_payload = {
            "source": str(source),
            "output_path": str(result.output_path),
            "upload_allowed": result.upload_allowed,
            "risk_count": len(result.risk_findings),
            "risk_report_path": str(result.risk_report_path),
            "mapping_path": str(result.mapping_path),
            "mapping_xlsx_path": str(result.mapping_xlsx_path),
            "report_path": str(result.report_path),
            "original_length": original_length,
            "anonymized_length": anonymized_length,
            "placeholder_count": placeholders,
            "risk_categories": sorted({finding.category for finding in result.risk_findings}),
        }
        results.append(result_payload)

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate external legal documents locally.")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--output-root", type=Path, default=Path("tmp/sample-evaluation"))
    args = parser.parse_args()

    missing = [path for path in args.paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing sample files: {missing}")

    results = evaluate(args.paths, args.output_root)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
