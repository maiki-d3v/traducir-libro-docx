#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from docx import Document
from docx.document import Document as _Document
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph


BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "workspace" / "input"
INTERMEDIATE_DIR = BASE_DIR / "workspace" / "intermediate"
LOGS_DIR = BASE_DIR / "workspace" / "logs"


def ensure_dirs() -> None:
    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def iter_block_items(parent):
    """
    Itera párrafos y tablas en el orden original del documento.
    """
    from docx.oxml.text.paragraph import CT_P
    from docx.oxml.table import CT_Tbl

    if isinstance(parent, _Document):
        parent_elm = parent.element.body
    elif isinstance(parent, _Cell):
        parent_elm = parent._tc
    else:
        raise TypeError(f"Unsupported parent type: {type(parent)}")

    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def safe_bool(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)


def get_heading_level(style_name: str | None) -> int | None:
    if not style_name:
        return None

    normalized = style_name.strip().lower()
    if normalized.startswith("heading "):
        try:
            return int(normalized.replace("heading ", "").strip())
        except ValueError:
            return None

    if normalized.startswith("title"):
        return 0

    return None


def extract_run(run, run_index: int) -> Dict[str, Any]:
    return {
        "index": run_index,
        "text": run.text,
        "formatting": {
            "bold": safe_bool(run.bold),
            "italic": safe_bool(run.italic),
            "underline": safe_bool(run.underline),
            "all_caps": safe_bool(run.font.all_caps),
            "small_caps": safe_bool(run.font.small_caps),
            "subscript": safe_bool(run.font.subscript),
            "superscript": safe_bool(run.font.superscript),
            "strike": safe_bool(run.font.strike),
            "double_strike": safe_bool(run.font.double_strike),
            "hidden": safe_bool(run.font.hidden),
            "name": run.font.name,
            "size_pt": float(run.font.size.pt) if run.font.size else None,
        },
    }


def extract_paragraph(paragraph: Paragraph, block_index: int) -> Dict[str, Any]:
    style_name = paragraph.style.name if paragraph.style else None
    heading_level = get_heading_level(style_name)

    runs = [extract_run(run, i) for i, run in enumerate(paragraph.runs)]
    full_text = "".join(run["text"] for run in runs)

    if heading_level == 0:
        block_type = "chapter_title"
    elif heading_level == 1:
        block_type = "section_title"
    elif heading_level and heading_level >= 2:
        block_type = "subsection_title"
    else:
        block_type = "paragraph"

    return {
        "block_id": f"block_{block_index:05d}",
        "kind": "paragraph",
        "type": block_type,
        "style_name": style_name,
        "heading_level": heading_level,
        "text": full_text,
        "runs": runs,
        "paragraph_format": {
            "alignment": str(paragraph.alignment) if paragraph.alignment is not None else None,
        },
    }


def extract_table(table: Table, block_index: int) -> Dict[str, Any]:
    rows_data: List[List[Dict[str, Any]]] = []

    for row_idx, row in enumerate(table.rows):
        row_data = []
        for col_idx, cell in enumerate(row.cells):
            cell_paragraphs = []
            for p_idx, paragraph in enumerate(cell.paragraphs):
                cell_paragraphs.append({
                    "paragraph_index": p_idx,
                    "text": paragraph.text,
                    "style_name": paragraph.style.name if paragraph.style else None,
                    "runs": [extract_run(run, i) for i, run in enumerate(paragraph.runs)],
                })

            row_data.append({
                "row_index": row_idx,
                "col_index": col_idx,
                "text": "\n".join(p["text"] for p in cell_paragraphs),
                "paragraphs": cell_paragraphs,
            })
        rows_data.append(row_data)

    return {
        "block_id": f"block_{block_index:05d}",
        "kind": "table",
        "type": "table",
        "rows": rows_data,
    }


def infer_doc_metadata(document: Document, source_path: Path) -> Dict[str, Any]:
    core = document.core_properties
    return {
        "source_file": source_path.name,
        "source_path": str(source_path),
        "title": core.title,
        "author": core.author,
        "subject": core.subject,
        "category": core.category,
        "comments": core.comments,
        "language": core.language,
        "created": core.created.isoformat() if core.created else None,
        "modified": core.modified.isoformat() if core.modified else None,
    }


def extract_document(docx_path: Path) -> Dict[str, Any]:
    document = Document(str(docx_path))
    blocks: List[Dict[str, Any]] = []

    for block_index, item in enumerate(iter_block_items(document), start=1):
        if isinstance(item, Paragraph):
            blocks.append(extract_paragraph(item, block_index))
        elif isinstance(item, Table):
            blocks.append(extract_table(item, block_index))

    return {
        "document_metadata": infer_doc_metadata(document, docx_path),
        "statistics": {
            "total_blocks": len(blocks),
            "paragraph_blocks": sum(1 for b in blocks if b["kind"] == "paragraph"),
            "table_blocks": sum(1 for b in blocks if b["kind"] == "table"),
        },
        "blocks": blocks,
    }


def write_json(data: Dict[str, Any], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_log(message: str) -> None:
    log_path = LOGS_DIR / "extract_docx.log"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(message + "\n")


def main() -> int:
    ensure_dirs()

    if len(sys.argv) < 2:
        print("Usage: python extract_docx.py <input.docx>")
        return 1

    input_arg = Path(sys.argv[1])

    if not input_arg.is_absolute():
        input_path = (Path.cwd() / input_arg).resolve()
    else:
        input_path = input_arg

    if not input_path.exists():
        print(f"Error: file not found: {input_path}")
        return 1

    if input_path.suffix.lower() != ".docx":
        print("Error: input file must be a .docx")
        return 1

    try:
        result = extract_document(input_path)
        output_name = f"{input_path.stem}.extracted.json"
        output_path = INTERMEDIATE_DIR / output_name
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
