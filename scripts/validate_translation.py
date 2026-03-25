#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


BASE_DIR = Path(__file__).resolve().parent.parent
INTERMEDIATE_DIR = BASE_DIR / "workspace" / "intermediate"
LOGS_DIR = BASE_DIR / "workspace" / "logs"


PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_]+_\d{3}\}\}")
URL_RE = re.compile(r"https?://[^\s)>]+", re.IGNORECASE)


PROTECTED_SEMANTIC_TYPES = {
    "reference",
    "console_command",
    "code_block",
}


HEADING_TYPES = {
    "chapter_title",
    "section_title",
    "subsection_title",
}


def ensure_dirs() -> None:
    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(data: Dict[str, Any], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_log(message: str) -> None:
    log_path = LOGS_DIR / "validate_translation.log"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(message + "\n")


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def find_placeholders(text: str) -> List[str]:
    if not text:
        return []
    return sorted(set(PLACEHOLDER_RE.findall(text)))


def extract_urls(text: str) -> List[str]:
    if not text:
        return []
    return URL_RE.findall(text)


def make_issue(
    severity: str,
    category: str,
    block_id: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "severity": severity,   # error | warning | info
        "category": category,
        "block_id": block_id,
        "message": message,
        "details": details or {},
    }


def compare_protected_block(block: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []

    semantic_type = block.get("semantic_type", "")
    block_id = block.get("block_id", "unknown")
    source_text = block.get("text", "") or ""
    final_text = block.get("final_text", "") or ""

    if semantic_type == "reference":
        if source_text != final_text:
            issues.append(
                make_issue(
                    "error",
                    "protected_content_changed",
                    block_id,
                    "Reference block changed after restoration.",
                    {
                        "semantic_type": semantic_type,
                        "source_text": source_text,
                        "final_text": final_text,
                    },
                )
            )

    elif semantic_type == "console_command":
        if normalize_whitespace(source_text) != normalize_whitespace(final_text):
            issues.append(
                make_issue(
                    "error",
                    "protected_content_changed",
                    block_id,
                    "Console command block changed after restoration.",
                    {
                        "semantic_type": semantic_type,
                        "source_text": source_text,
                        "final_text": final_text,
                    },
                )
            )

    elif semantic_type == "code_block":
        if source_text != final_text:
            issues.append(
                make_issue(
                    "warning",
                    "code_block_changed",
                    block_id,
                    "Code block differs from source after restoration. Review whether only comments changed.",
                    {
                        "semantic_type": semantic_type,
                        "source_text": source_text,
                        "final_text": final_text,
                    },
                )
            )

    return issues


def validate_urls_in_block(block: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    block_id = block.get("block_id", "unknown")
    source_urls = extract_urls(block.get("text", "") or "")
    final_urls = extract_urls(block.get("final_text", "") or "")

    if source_urls != final_urls:
        issues.append(
            make_issue(
                "error",
                "url_mismatch",
                block_id,
                "URLs differ between source and final text.",
                {
                    "source_urls": source_urls,
                    "final_urls": final_urls,
                },
            )
        )

    return issues


def validate_placeholders_in_block(block: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    block_id = block.get("block_id", "unknown")

    final_placeholders = find_placeholders(block.get("final_text", "") or "")
    if final_placeholders:
        issues.append(
            make_issue(
                "error",
                "unrestored_placeholders",
                block_id,
                "Unrestored placeholders found in final text.",
                {
                    "placeholders": final_placeholders,
                },
            )
        )

    return issues


def validate_empty_or_suspicious_block(block: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    block_id = block.get("block_id", "unknown")
    semantic_type = block.get("semantic_type", "")
    source_text = block.get("text", "") or ""
    final_text = block.get("final_text", "") or ""

    if normalize_whitespace(source_text) and not normalize_whitespace(final_text):
        issues.append(
            make_issue(
                "warning",
                "empty_final_text",
                block_id,
                "Final text is empty although source text was not empty.",
                {
                    "semantic_type": semantic_type,
                },
            )
        )

    return issues


def validate_heading_block(block: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    block_id = block.get("block_id", "unknown")
    source_text = block.get("text", "") or ""
    final_text = block.get("final_text", "") or ""

    source_number_prefix = re.match(r"^\s*([0-9]+(?:\.[0-9]+)*)", source_text)
    final_number_prefix = re.match(r"^\s*([0-9]+(?:\.[0-9]+)*)", final_text)

    if bool(source_number_prefix) != bool(final_number_prefix):
        issues.append(
            make_issue(
                "warning",
                "heading_numbering_changed",
                block_id,
                "Heading numbering presence changed between source and final text.",
                {
                    "source_text": source_text,
                    "final_text": final_text,
                },
            )
        )
    elif source_number_prefix and final_number_prefix:
        if source_number_prefix.group(1) != final_number_prefix.group(1):
            issues.append(
                make_issue(
                    "warning",
                    "heading_numbering_changed",
                    block_id,
                    "Heading numbering changed between source and final text.",
                    {
                        "source_number": source_number_prefix.group(1),
                        "final_number": final_number_prefix.group(1),
                    },
                )
            )

    return issues


def validate_standard_block(block: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []

    issues.extend(validate_placeholders_in_block(block))
    issues.extend(validate_urls_in_block(block))
    issues.extend(validate_empty_or_suspicious_block(block))

    semantic_type = block.get("semantic_type", "")
    if semantic_type in PROTECTED_SEMANTIC_TYPES:
        issues.extend(compare_protected_block(block))

    if semantic_type in HEADING_TYPES:
        issues.extend(validate_heading_block(block))

    return issues


def validate_table_block(block: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    block_id = block.get("block_id", "unknown")

    for row_index, row in enumerate(block.get("rows", [])):
        for cell_index, cell in enumerate(row):
            for paragraph in cell.get("paragraphs", []):
                pseudo_block = {
                    "block_id": f"{block_id}::table[{row_index}:{cell_index}]::p{paragraph.get('paragraph_index', 0)}",
                    "semantic_type": "table",
                    "text": paragraph.get("text", ""),
                    "final_text": paragraph.get("final_text", ""),
                }
                issues.extend(validate_placeholders_in_block(pseudo_block))
                issues.extend(validate_urls_in_block(pseudo_block))
                issues.extend(validate_empty_or_suspicious_block(pseudo_block))

    if block.get("unrestored_placeholders"):
        issues.append(
            make_issue(
                "error",
                "unrestored_placeholders",
                block_id,
                "Unrestored placeholders found in table block.",
                {
                    "placeholders": block.get("unrestored_placeholders", []),
                },
            )
        )

    return issues


def validate_block(block: Dict[str, Any]) -> List[Dict[str, Any]]:
    if block.get("kind") == "table":
        return validate_table_block(block)
    return validate_standard_block(block)


def summarize_structure(data: Dict[str, Any]) -> Dict[str, Any]:
    blocks = data.get("blocks", []) or []

    summary = {
        "total_blocks": len(blocks),
        "tables": 0,
        "headings": 0,
        "by_semantic_type": {},
    }

    for block in blocks:
        semantic_type = block.get("semantic_type", "unknown")
        summary["by_semantic_type"][semantic_type] = summary["by_semantic_type"].get(semantic_type, 0) + 1

        if block.get("kind") == "table":
            summary["tables"] += 1

        if semantic_type in HEADING_TYPES:
            summary["headings"] += 1

    return summary


def validate_document(data: Dict[str, Any]) -> Dict[str, Any]:
    blocks = data.get("blocks", []) or []
    issues: List[Dict[str, Any]] = []

    for block in blocks:
        issues.extend(validate_block(block))

    counts = {
        "errors": sum(1 for issue in issues if issue["severity"] == "error"),
        "warnings": sum(1 for issue in issues if issue["severity"] == "warning"),
        "info": sum(1 for issue in issues if issue["severity"] == "info"),
        "total_issues": len(issues),
    }

    validation_status = "passed"
    if counts["errors"] > 0:
        validation_status = "failed"
    elif counts["warnings"] > 0:
        validation_status = "passed_with_warnings"

    return {
        "document_metadata": data.get("document_metadata", {}),
        "upstream_statistics": data.get("upstream_statistics", {}),
        "segmentation_statistics": data.get("segmentation_statistics", {}),
        "protection_statistics": data.get("protection_statistics", {}),
        "translation_statistics": data.get("translation_statistics", {}),
        "restoration_statistics": data.get("restoration_statistics", {}),
        "structure_summary": summarize_structure(data),
        "validation_summary": {
            "status": validation_status,
            **counts,
        },
        "issues": issues,
        "blocks": data.get("blocks", []),
    }


def main() -> int:
    ensure_dirs()

    if len(sys.argv) < 2:
        print("Usage: python validate_translation.py <restored.json>")
        return 1

    input_arg = Path(sys.argv[1])
    input_path = input_arg.resolve() if input_arg.is_absolute() else (Path.cwd() / input_arg).resolve()

    if not input_path.exists():
        print(f"Error: file not found: {input_path}")
        return 1

    if input_path.suffix.lower() != ".json":
        print("Error: input file must be a .json")
        return 1

    try:
        data = load_json(input_path)
        result = validate_document(data)

        suffix = ".validated.json"
        output_name = (
            input_path.name.replace(".restored.json", suffix)
            if input_path.name.endswith(".restored.json")
            else f"{input_path.stem}{suffix}"
        )
        output_path = INTERMEDIATE_DIR / output_name

        write_json(result, output_path)
        write_log(
            f"OK | validated={input_path} | output={output_path} "
            f"| status={result['validation_summary']['status']} "
            f"| errors={result['validation_summary']['errors']} "
            f"| warnings={result['validation_summary']['warnings']}"
        )

        print(f"Validation complete: {output_path}")
        print(
            "Status: "
            f"{result['validation_summary']['status']} | "
            f"errors={result['validation_summary']['errors']} | "
            f"warnings={result['validation_summary']['warnings']}"
        )
        return 0 if result["validation_summary"]["errors"] == 0 else 2

    except Exception as exc:
        write_log(f"ERROR | file={input_path} | error={repr(exc)}")
        print(f"Validation failed: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
