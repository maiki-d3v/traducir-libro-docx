#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List


BASE_DIR = Path(__file__).resolve().parent.parent
INTERMEDIATE_DIR = BASE_DIR / "workspace" / "intermediate"
LOGS_DIR = BASE_DIR / "workspace" / "logs"


PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_]+_\d{3}\}\}")


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
    log_path = LOGS_DIR / "restore_content.log"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(message + "\n")


def build_placeholder_map(spans: List[Dict[str, Any]]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for span in spans or []:
        placeholder = span.get("placeholder")
        original = span.get("original", "")
        if placeholder:
            mapping[placeholder] = original
    return mapping


def restore_text(text: str, spans: List[Dict[str, Any]]) -> str:
    if not text:
        return text

    placeholder_map = build_placeholder_map(spans)

    # Reemplazo determinista por longitud descendente para evitar riesgos,
    # aunque los placeholders actuales no se solapan.
    for placeholder in sorted(placeholder_map.keys(), key=len, reverse=True):
        text = text.replace(placeholder, placeholder_map[placeholder])

    return text


def collect_unrestored_placeholders(text: str) -> List[str]:
    if not text:
        return []
    return sorted(set(PLACEHOLDER_RE.findall(text)))


def restore_standard_block(block: Dict[str, Any]) -> Dict[str, Any]:
    restored_block = dict(block)
    translated_text = block.get("translated_text", block.get("protected_text", block.get("text", "")))
    protected_spans = block.get("protected_spans", []) or []

    final_text = restore_text(translated_text or "", protected_spans)
    unrestored = collect_unrestored_placeholders(final_text)

    restored_block["final_text"] = final_text
    restored_block["restoration_status"] = "ok" if not unrestored else "warning"
    restored_block["unrestored_placeholders"] = unrestored

    return restored_block


def restore_table_block(block: Dict[str, Any]) -> Dict[str, Any]:
    restored_block = dict(block)
    restored_rows = []
    all_unrestored: List[str] = []

    for row in block.get("rows", []):
        restored_row = []
        for cell in row:
            cell_copy = dict(cell)
            restored_paragraphs = []

            for paragraph in cell.get("paragraphs", []):
                p_copy = dict(paragraph)
                translated_text = paragraph.get("translated_text", paragraph.get("protected_text", paragraph.get("text", "")))
                spans = paragraph.get("protected_spans", []) or []

                final_text = restore_text(translated_text or "", spans)
                unrestored = collect_unrestored_placeholders(final_text)

                p_copy["final_text"] = final_text
                p_copy["restoration_status"] = "ok" if not unrestored else "warning"
                p_copy["unrestored_placeholders"] = unrestored

                if unrestored:
                    all_unrestored.extend(unrestored)

                restored_paragraphs.append(p_copy)

            cell_copy["paragraphs"] = restored_paragraphs
            cell_copy["final_text"] = "\n".join(p.get("final_text", "") for p in restored_paragraphs)
            restored_row.append(cell_copy)

        restored_rows.append(restored_row)

    restored_block["rows"] = restored_rows
    restored_block["final_text"] = None
    restored_block["restoration_status"] = "ok" if not all_unrestored else "warning"
    restored_block["unrestored_placeholders"] = sorted(set(all_unrestored))

    return restored_block


def restore_block(block: Dict[str, Any]) -> Dict[str, Any]:
    if block.get("kind") == "table":
        return restore_table_block(block)
    return restore_standard_block(block)


def restore_document(data: Dict[str, Any]) -> Dict[str, Any]:
    source_blocks = data.get("blocks", []) or []
    restored_blocks: List[Dict[str, Any]] = []

    stats = {
        "total_blocks": len(source_blocks),
        "blocks_ok": 0,
        "blocks_with_warnings": 0,
        "total_unrestored_placeholders": 0,
    }

    for block in source_blocks:
        restored_block = restore_block(block)
        restored_blocks.append(restored_block)

        if restored_block.get("restoration_status") == "ok":
            stats["blocks_ok"] += 1
        else:
            stats["blocks_with_warnings"] += 1
            stats["total_unrestored_placeholders"] += len(restored_block.get("unrestored_placeholders", []))

    return {
        "document_metadata": data.get("document_metadata", {}),
        "upstream_statistics": data.get("upstream_statistics", {}),
        "segmentation_statistics": data.get("segmentation_statistics", {}),
        "protection_statistics": data.get("protection_statistics", {}),
        "translation_statistics": data.get("translation_statistics", {}),
        "restoration_statistics": stats,
        "blocks": restored_blocks,
    }


def main() -> int:
    ensure_dirs()

    if len(sys.argv) < 2:
        print("Usage: python restore_content.py <translated.json>")
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
        result = restore_document(data)

        suffix = ".restored.json"
        output_name = (
            input_path.name.replace(".translated.json", suffix)
            if input_path.name.endswith(".translated.json")
            else f"{input_path.stem}{suffix}"
        )
        output_path = INTERMEDIATE_DIR / output_name

        write_json(result, output_path)
        write_log(f"OK | restored={input_path} | output={output_path}")
        print(f"Restoration complete: {output_path}")
        return 0
    except Exception as exc:
        write_log(f"ERROR | file={input_path} | error={repr(exc)}")
        print(f"Restoration failed: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
