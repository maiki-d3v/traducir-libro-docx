#!/usr/bin/env python3
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "workspace" / "output"
LOGS_DIR = BASE_DIR / "workspace" / "logs"


def ensure_dirs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_log(message: str) -> None:
    log_path = LOGS_DIR / "reconstruct_xml.log"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(message + "\n")


def get_element_by_path(root: ET.Element, path: List[int]) -> ET.Element:
    current = root
    for index in path:
        children = list(current)
        if index < 0 or index >= len(children):
            raise IndexError(f"Invalid XML path segment {index} for element {current.tag}")
        current = children[index]
    return current


def apply_translations(tree: ET.ElementTree, blocks: List[Dict[str, Any]]) -> int:
    root = tree.getroot()
    applied = 0

    for block in blocks:
        binding = block.get("xml_binding") or {}
        if not binding:
            continue

        path = binding.get("path")
        slot = binding.get("slot")
        if not isinstance(path, list) or slot not in {"text", "tail"}:
            continue

        element = get_element_by_path(root, [int(p) for p in path])
        final_text = block.get("final_text", "")

        if slot == "text":
            element.text = final_text
        else:
            element.tail = final_text

        applied += 1

    return applied


def build_output_path(input_json_path: Path, data: Dict[str, Any]) -> Path:
    source_file = (data.get("document_metadata", {}) or {}).get("source_file")
    if source_file:
        stem = Path(source_file).stem
    else:
        stem = input_json_path.stem.replace(".validated", "")

    return OUTPUT_DIR / f"{stem}.translated.en.xml"


def main() -> int:
    ensure_dirs()

    if len(sys.argv) < 2:
        print("Usage: python reconstruct_xml.py <validated.json>")
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
        source_path_raw = (data.get("document_metadata", {}) or {}).get("source_path")
        if not source_path_raw:
            raise ValueError("document_metadata.source_path is required for XML reconstruction")

        source_path = Path(source_path_raw)
        if not source_path.exists():
            raise FileNotFoundError(f"Original XML source not found: {source_path}")

        tree = ET.parse(str(source_path))
        applied_count = apply_translations(tree, data.get("blocks", []) or [])

        output_path = build_output_path(input_path, data)
        tree.write(str(output_path), encoding="utf-8", xml_declaration=True)

        validation_summary = data.get("validation_summary", {}) or {}
        write_log(
            f"OK | reconstructed={input_path} | output={output_path} "
            f"| applied_blocks={applied_count} "
            f"| validation_status={validation_summary.get('status')}"
        )

        print(f"XML reconstruction complete: {output_path}")
        return 0
    except Exception as exc:
        write_log(f"ERROR | file={input_path} | error={repr(exc)}")
        print(f"XML reconstruction failed: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
