#!/usr/bin/env python3
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List


BASE_DIR = Path(__file__).resolve().parent.parent
INTERMEDIATE_DIR = BASE_DIR / "workspace" / "intermediate"
LOGS_DIR = BASE_DIR / "workspace" / "logs"


def ensure_dirs() -> None:
    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def write_json(data: Dict[str, Any], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_log(message: str) -> None:
    log_path = LOGS_DIR / "extract_xml.log"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(message + "\n")


def strip_namespace(tag: str) -> str:
    if tag.startswith("{") and "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def infer_block_type(tag_name: str) -> str:
    normalized = (tag_name or "").lower()

    if normalized in {"title", "h1", "chapter", "chaptertitle"}:
        return "chapter_title"
    if normalized in {"h2", "section", "sectiontitle"}:
        return "section_title"
    if normalized in {"h3", "h4", "subsection", "subsectiontitle"}:
        return "subsection_title"

    return "paragraph"


def make_run(text: str) -> Dict[str, Any]:
    return {
        "index": 0,
        "text": text,
        "formatting": {
            "bold": None,
            "italic": None,
            "underline": None,
            "all_caps": None,
            "small_caps": None,
            "subscript": None,
            "superscript": None,
            "strike": None,
            "double_strike": None,
            "hidden": None,
            "name": None,
            "size_pt": None,
        },
    }


def append_text_block(
    blocks: List[Dict[str, Any]],
    text: str,
    owner_tag: str,
    path: List[int],
    slot: str,
) -> None:
    if not text or not text.strip():
        return

    block_index = len(blocks) + 1
    block_type = infer_block_type(owner_tag)
    heading_level = None
    if block_type == "chapter_title":
        heading_level = 1
    elif block_type == "section_title":
        heading_level = 2
    elif block_type == "subsection_title":
        heading_level = 3

    blocks.append(
        {
            "block_id": f"block_{block_index:05d}",
            "kind": "paragraph",
            "type": block_type,
            "style_name": None,
            "heading_level": heading_level,
            "text": text,
            "runs": [make_run(text)],
            "paragraph_format": {
                "alignment": None,
            },
            "xml_binding": {
                "path": path,
                "slot": slot,
                "owner_tag": owner_tag,
            },
        }
    )


def walk_xml(element: ET.Element, path: List[int], blocks: List[Dict[str, Any]]) -> None:
    owner_tag = strip_namespace(element.tag)

    append_text_block(blocks, element.text or "", owner_tag, path, "text")

    for child_index, child in enumerate(list(element)):
        child_path = path + [child_index]
        walk_xml(child, child_path, blocks)

        append_text_block(
            blocks,
            child.tail or "",
            owner_tag,
            child_path,
            "tail",
        )


def infer_doc_metadata(source_path: Path, root: ET.Element) -> Dict[str, Any]:
    return {
        "source_file": source_path.name,
        "source_path": str(source_path),
        "source_format": "xml",
        "root_tag": strip_namespace(root.tag),
    }


def extract_document(xml_path: Path) -> Dict[str, Any]:
    tree = ET.parse(str(xml_path))
    root = tree.getroot()

    blocks: List[Dict[str, Any]] = []
    walk_xml(root, [], blocks)

    return {
        "document_metadata": infer_doc_metadata(xml_path, root),
        "statistics": {
            "total_blocks": len(blocks),
            "paragraph_blocks": len(blocks),
            "table_blocks": 0,
        },
        "blocks": blocks,
    }


def main() -> int:
    ensure_dirs()

    if len(sys.argv) < 2:
        print("Usage: python extract_xml.py <input.xml>")
        return 1

    input_arg = Path(sys.argv[1])
    input_path = input_arg.resolve() if input_arg.is_absolute() else (Path.cwd() / input_arg).resolve()

    if not input_path.exists():
        print(f"Error: file not found: {input_path}")
        return 1

    if input_path.suffix.lower() != ".xml":
        print("Error: input file must be a .xml")
        return 1

    try:
        result = extract_document(input_path)
        output_path = INTERMEDIATE_DIR / f"{input_path.stem}.extracted.json"
        write_json(result, output_path)
        write_log(f"OK | extracted={input_path} | output={output_path}")
        print(f"Extraction complete: {output_path}")
        return 0
    except Exception as exc:
        write_log(f"ERROR | file={input_path} | error={repr(exc)}")
        print(f"Extraction failed: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
