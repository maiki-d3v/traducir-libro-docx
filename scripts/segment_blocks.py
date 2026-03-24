#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


BASE_DIR = Path(__file__).resolve().parent.parent
INTERMEDIATE_DIR = BASE_DIR / "workspace" / "intermediate"
LOGS_DIR = BASE_DIR / "workspace" / "logs"


REFERENCE_PATTERNS = [
    re.compile(r"^\s*\[[0-9]+\]\s+"),
    re.compile(r"^\s*[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ'`\-]+,\s+[A-Z]"),
    re.compile(r".*\bdoi:\s*\S+", re.IGNORECASE),
    re.compile(r".*\bhttps?://\S+", re.IGNORECASE),
]

CONSOLE_COMMAND_PATTERNS = [
    re.compile(r"^\s*(python|python3|pip|pip3|npm|node|git|docker|docker-compose|kubectl|ls|cd|cp|mv|rm|mkdir|chmod|chown|cat|grep|find|sed|awk|mysql|psql|bash|sh|zsh)\b"),
    re.compile(r"^\s*[$#]\s+"),
]

CODE_HINT_PATTERNS = [
    re.compile(r"^\s*(if|for|while|def|class|return|try|except|import|from|public|private|protected|function|const|let|var)\b"),
    re.compile(r"[{};=]{1,}"),
    re.compile(r"^\s*//"),
    re.compile(r"^\s*#include\b"),
]

BLOCK_PREFIX_RULES: List[Tuple[str, re.Pattern[str]]] = [
    ("definition", re.compile(r"^\s*(definición|definition)\b[:.]?", re.IGNORECASE)),
    ("theorem", re.compile(r"^\s*(teorema|theorem)\b[:.]?", re.IGNORECASE)),
    ("lemma", re.compile(r"^\s*(lema|lemma)\b[:.]?", re.IGNORECASE)),
    ("proposition", re.compile(r"^\s*(proposición|proposition)\b[:.]?", re.IGNORECASE)),
    ("corollary", re.compile(r"^\s*(corolario|corollary)\b[:.]?", re.IGNORECASE)),
    ("proof", re.compile(r"^\s*(demostración|proof)\b[:.]?", re.IGNORECASE)),
    ("example", re.compile(r"^\s*(ejemplo|example)\b[:.]?", re.IGNORECASE)),
    ("exercise", re.compile(r"^\s*(ejercicio|exercise)\b[:.]?", re.IGNORECASE)),
    ("question", re.compile(r"^\s*(pregunta|question)\b[:.]?", re.IGNORECASE)),
    ("algorithm", re.compile(r"^\s*(algoritmo|algorithm)\b[:.]?", re.IGNORECASE)),
    ("quote", re.compile(r"^\s*>\s+")),
]


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
    log_path = LOGS_DIR / "segment_blocks.log"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(message + "\n")


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def looks_like_reference(text: str) -> bool:
    return any(pattern.match(text) for pattern in REFERENCE_PATTERNS)


def looks_like_console_command(text: str) -> bool:
    return any(pattern.search(text) for pattern in CONSOLE_COMMAND_PATTERNS)


def looks_like_code(text: str) -> bool:
    if "\n" in text:
        lines = [line for line in text.splitlines() if line.strip()]
        if len(lines) >= 2:
            score = sum(1 for line in lines if any(p.search(line) for p in CODE_HINT_PATTERNS))
            if score >= 2:
                return True
    return any(pattern.search(text) for pattern in CODE_HINT_PATTERNS)


def looks_like_list_item(text: str) -> bool:
    return bool(re.match(r"^\s*(?:[-*+]|[0-9]+[.)]|[a-zA-Z][.)])\s+", text))


def infer_semantic_type(block: Dict[str, Any]) -> str:
    block_type = block.get("type")
    text = block.get("text", "") or ""
    normalized = normalize_text(text)

    if block.get("kind") == "table":
        return "table"

    if block_type in {"chapter_title", "section_title", "subsection_title"}:
        return block_type

    if not normalized:
        return "empty"

    for semantic_type, pattern in BLOCK_PREFIX_RULES:
        if pattern.match(normalized):
            return semantic_type

    if looks_like_reference(normalized):
        return "reference"

    if looks_like_console_command(normalized):
        return "console_command"

    if looks_like_code(text):
        return "code_block"

    if looks_like_list_item(normalized):
        return "list_item"

    return "prose"


def infer_translation_mode(semantic_type: str) -> str:
    if semantic_type in {"reference", "url", "filename", "path", "math_inline", "math_block"}:
        return "preserve_exact"
    if semantic_type == "code_block":
        return "translate_comments_only"
    if semantic_type == "console_command":
        return "preserve_command_translate_context"
    if semantic_type == "table":
        return "translate_text_only"
    return "translate_full"


def collect_style_flags(block: Dict[str, Any]) -> Dict[str, bool]:
    runs = block.get("runs", []) or []
    flags = {
        "has_bold": False,
        "has_italic": False,
        "has_underline": False,
        "has_superscript": False,
        "has_subscript": False,
        "has_small_caps": False,
        "has_all_caps": False,
    }

    for run in runs:
        fmt = run.get("formatting", {}) or {}
        flags["has_bold"] = flags["has_bold"] or bool(fmt.get("bold"))
        flags["has_italic"] = flags["has_italic"] or bool(fmt.get("italic"))
        flags["has_underline"] = flags["has_underline"] or bool(fmt.get("underline"))
        flags["has_superscript"] = flags["has_superscript"] or bool(fmt.get("superscript"))
        flags["has_subscript"] = flags["has_subscript"] or bool(fmt.get("subscript"))
        flags["has_small_caps"] = flags["has_small_caps"] or bool(fmt.get("small_caps"))
        flags["has_all_caps"] = flags["has_all_caps"] or bool(fmt.get("all_caps"))

    return flags


def enrich_block(block: Dict[str, Any]) -> Dict[str, Any]:
    semantic_type = infer_semantic_type(block)
    enriched = dict(block)

    enriched["semantic_type"] = semantic_type
    enriched["translation_mode"] = infer_translation_mode(semantic_type)
    enriched["normalized_text"] = normalize_text(block.get("text", ""))
    enriched["style_flags"] = collect_style_flags(block)
    enriched["protected_spans"] = []

    if semantic_type in {"chapter_title", "section_title", "subsection_title"}:
        enriched["block_role"] = "heading"
    elif semantic_type == "table":
        enriched["block_role"] = "table"
    elif semantic_type in {"code_block", "console_command", "reference"}:
        enriched["block_role"] = "technical"
    else:
        enriched["block_role"] = "content"

    return enriched


def segment_document(data: Dict[str, Any]) -> Dict[str, Any]:
    source_blocks = data.get("blocks", [])
    enriched_blocks = [enrich_block(block) for block in source_blocks]

    stats = {
        "total_blocks": len(enriched_blocks),
        "by_semantic_type": {},
    }

    for block in enriched_blocks:
        semantic_type = block["semantic_type"]
        stats["by_semantic_type"][semantic_type] = stats["by_semantic_type"].get(semantic_type, 0) + 1

    return {
        "document_metadata": data.get("document_metadata", {}),
        "upstream_statistics": data.get("statistics", {}),
        "segmentation_statistics": stats,
        "blocks": enriched_blocks,
    }


def main() -> int:
    ensure_dirs()

    if len(sys.argv) < 2:
        print("Usage: python segment_blocks.py <extracted.json>")
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
        result = segment_document(data)

        suffix = ".segmented.json"
        output_name = input_path.name.replace(".extracted.json", suffix) if input_path.name.endswith(".extracted.json") else f"{input_path.stem}{suffix}"
        output_path = INTERMEDIATE_DIR / output_name

        write_json(result, output_path)
        write_log(f"OK | segmented={input_path} | output={output_path}")
        print(f"Segmentation complete: {output_path}")
        return 0
    except Exception as exc:
        write_log(f"ERROR | file={input_path} | error={repr(exc)}")
        print(f"Segmentation failed: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
