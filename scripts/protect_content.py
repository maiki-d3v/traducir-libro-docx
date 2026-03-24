#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


BASE_DIR = Path(__file__).resolve().parent.parent
INTERMEDIATE_DIR = BASE_DIR / "workspace" / "intermediate"
LOGS_DIR = BASE_DIR / "workspace" / "logs"


URL_RE = re.compile(r"https?://[^\s)>]+", re.IGNORECASE)
INLINE_CODE_RE = re.compile(r"`([^`]+)`")
INLINE_MATH_RE = re.compile(r"(\$[^$\n]+\$)")
PATH_RE = re.compile(
    r"(?:(?:[A-Za-z]:[\\/])|(?:\./)|(?:\.\./)|(?:/))(?:(?:[^\\/\s]+[\\/])*)(?:[^\\/\s]+)?"
)
FILENAME_RE = re.compile(
    r"\b[\w.\-]+\.(?:py|js|ts|java|c|cpp|h|hpp|cs|go|rs|php|rb|sh|zsh|bash|sql|json|yaml|yml|xml|html|css|md|txt|csv|docx|pdf|tex)\b",
    re.IGNORECASE,
)
COMMAND_TOKEN_RE = re.compile(
    r"(?<!\w)(?:--?[A-Za-z0-9][A-Za-z0-9\-_]*|docker|git|python3?|pip3?|npm|node|kubectl|mysql|psql|bash|sh|zsh)(?!\w)"
)

REFERENCE_LINE_RE = re.compile(
    r"^\s*(?:\[[0-9]+\]|[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ'`\-]+,\s+[A-Z]|.+\bdoi:\s*\S+|.+https?://\S+)",
    re.IGNORECASE,
)


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
    log_path = LOGS_DIR / "protect_content.log"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(message + "\n")


class PlaceholderFactory:
    def __init__(self) -> None:
        self.counters: Dict[str, int] = {}

    def make(self, category: str) -> str:
        self.counters[category] = self.counters.get(category, 0) + 1
        return f"{{{{{category}_{self.counters[category]:03d}}}}}"


def add_protected_span(
    spans: List[Dict[str, Any]],
    placeholder: str,
    original: str,
    mode: str,
    category: str,
) -> None:
    spans.append(
        {
            "placeholder": placeholder,
            "original": original,
            "mode": mode,
            "category": category,
        }
    )


def replace_matches(
    text: str,
    pattern: re.Pattern,
    placeholder_factory: PlaceholderFactory,
    spans: List[Dict[str, Any]],
    category: str,
    mode: str,
) -> str:
    matches = list(pattern.finditer(text))
    if not matches:
        return text

    result_parts = []
    last_end = 0

    for match in matches:
        original = match.group(0)
        placeholder = placeholder_factory.make(category)
        add_protected_span(spans, placeholder, original, mode, category)

        result_parts.append(text[last_end:match.start()])
        result_parts.append(placeholder)
        last_end = match.end()

    result_parts.append(text[last_end:])
    return "".join(result_parts)


def replace_inline_code_content(
    text: str,
    placeholder_factory: PlaceholderFactory,
    spans: List[Dict[str, Any]],
) -> str:
    matches = list(INLINE_CODE_RE.finditer(text))
    if not matches:
        return text

    result_parts = []
    last_end = 0

    for match in matches:
        original = match.group(0)
        placeholder = placeholder_factory.make("INLINE_CODE")
        add_protected_span(spans, placeholder, original, "preserve_exact", "inline_code")

        result_parts.append(text[last_end:match.start()])
        result_parts.append(placeholder)
        last_end = match.end()

    result_parts.append(text[last_end:])
    return "".join(result_parts)


def replace_inline_math_content(
    text: str,
    placeholder_factory: PlaceholderFactory,
    spans: List[Dict[str, Any]],
) -> str:
    matches = list(INLINE_MATH_RE.finditer(text))
    if not matches:
        return text

    result_parts = []
    last_end = 0

    for match in matches:
        original = match.group(0)
        placeholder = placeholder_factory.make("INLINE_MATH")
        add_protected_span(spans, placeholder, original, "preserve_notation", "inline_math")

        result_parts.append(text[last_end:match.start()])
        result_parts.append(placeholder)
        last_end = match.end()

    result_parts.append(text[last_end:])
    return "".join(result_parts)


def protect_text_content(
    text: str,
    semantic_type: str,
    placeholder_factory: PlaceholderFactory,
) -> Tuple[str, List[Dict[str, Any]]]:
    spans: List[Dict[str, Any]] = []
    protected = text

    # Protección por bloque completo
    if semantic_type == "reference" and text.strip():
        placeholder = placeholder_factory.make("REFERENCE")
        add_protected_span(spans, placeholder, text, "preserve_reference", "reference")
        return placeholder, spans

    if semantic_type == "console_command" and text.strip():
        placeholder = placeholder_factory.make("COMMAND")
        add_protected_span(spans, placeholder, text, "preserve_exact", "command")
        return placeholder, spans

    if semantic_type == "code_block" and text.strip():
        placeholder = placeholder_factory.make("CODE_BLOCK")
        add_protected_span(spans, placeholder, text, "translate_comments_only", "code_block")
        return placeholder, spans

    # Protección parcial dentro de prosa y headings
    protected = replace_matches(
        protected,
        URL_RE,
        placeholder_factory,
        spans,
        "URL",
        "preserve_exact",
    )

    protected = replace_inline_code_content(
        protected,
        placeholder_factory,
        spans,
    )

    protected = replace_inline_math_content(
        protected,
        placeholder_factory,
        spans,
    )

    protected = replace_matches(
        protected,
        PATH_RE,
        placeholder_factory,
        spans,
        "PATH",
        "preserve_exact",
    )

    protected = replace_matches(
        protected,
        FILENAME_RE,
        placeholder_factory,
        spans,
        "FILENAME",
        "preserve_exact",
    )

    protected = replace_matches(
        protected,
        COMMAND_TOKEN_RE,
        placeholder_factory,
        spans,
        "IDENTIFIER",
        "preserve_identifier",
    )

    return protected, spans


def protect_runs(
    runs: List[Dict[str, Any]],
    semantic_type: str,
    placeholder_factory: PlaceholderFactory,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Protege también el texto por run para facilitar reconstrucción posterior.
    """
    all_spans: List[Dict[str, Any]] = []
    protected_runs: List[Dict[str, Any]] = []

    # En bloques protegidos completos, no tocamos runs individualmente;
    # la protección principal queda a nivel de bloque.
    if semantic_type in {"reference", "console_command", "code_block"}:
        return runs, all_spans

    for run in runs:
        run_copy = dict(run)
        run_text = run_copy.get("text", "")

        protected_text, spans = protect_text_content(
            run_text,
            semantic_type="inline_fragment",
            placeholder_factory=placeholder_factory,
        )
        run_copy["protected_text"] = protected_text
        protected_runs.append(run_copy)
        all_spans.extend(spans)

    return protected_runs, all_spans


def protect_table_block(
    block: Dict[str, Any],
    placeholder_factory: PlaceholderFactory,
) -> Dict[str, Any]:
    protected_block = dict(block)
    protected_block["protected_spans"] = []

    protected_rows = []
    for row in block.get("rows", []):
        protected_row = []
        for cell in row:
            cell_copy = dict(cell)
            new_paragraphs = []
            for paragraph in cell.get("paragraphs", []):
                p_copy = dict(paragraph)
                p_text = p_copy.get("text", "")
                protected_text, spans = protect_text_content(
                    p_text,
                    semantic_type="table_cell",
                    placeholder_factory=placeholder_factory,
                )
                p_copy["protected_text"] = protected_text
                p_copy["protected_spans"] = spans
                new_paragraphs.append(p_copy)
                protected_block["protected_spans"].extend(spans)

            cell_copy["paragraphs"] = new_paragraphs
            cell_copy["protected_text"] = "\n".join(
                p.get("protected_text", p.get("text", "")) for p in new_paragraphs
            )
            protected_row.append(cell_copy)
        protected_rows.append(protected_row)

    protected_block["rows"] = protected_rows
    return protected_block


def protect_block(
    block: Dict[str, Any],
    placeholder_factory: PlaceholderFactory,
) -> Dict[str, Any]:
    semantic_type = block.get("semantic_type", "")
    protected_block = dict(block)

    if block.get("kind") == "table":
        return protect_table_block(block, placeholder_factory)

    text = block.get("text", "") or ""
    protected_text, spans = protect_text_content(text, semantic_type, placeholder_factory)
    protected_runs, run_spans = protect_runs(block.get("runs", []) or [], semantic_type, placeholder_factory)

    # Evitar duplicados exactos en spans
    merged_spans = spans[:]
    existing = {(s["placeholder"], s["original"], s["category"]) for s in merged_spans}
    for span in run_spans:
        key = (span["placeholder"], span["original"], span["category"])
        if key not in existing:
            merged_spans.append(span)
            existing.add(key)

    protected_block["protected_text"] = protected_text
    protected_block["protected_runs"] = protected_runs
    protected_block["protected_spans"] = merged_spans

    return protected_block


def protect_document(data: Dict[str, Any]) -> Dict[str, Any]:
    placeholder_factory = PlaceholderFactory()
    source_blocks = data.get("blocks", []) or []

    protected_blocks = [protect_block(block, placeholder_factory) for block in source_blocks]

    stats: Dict[str, int] = {}
    total_spans = 0

    for block in protected_blocks:
        for span in block.get("protected_spans", []):
            category = span.get("category", "unknown")
            stats[category] = stats.get(category, 0) + 1
            total_spans += 1

    return {
        "document_metadata": data.get("document_metadata", {}),
        "upstream_statistics": data.get("upstream_statistics", {}),
        "segmentation_statistics": data.get("segmentation_statistics", {}),
        "protection_statistics": {
            "total_blocks": len(protected_blocks),
            "total_protected_spans": total_spans,
            "by_category": stats,
        },
        "blocks": protected_blocks,
    }


def main() -> int:
    ensure_dirs()

    if len(sys.argv) < 2:
        print("Usage: python protect_content.py <segmented.json>")
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
        result = protect_document(data)

        suffix = ".protected.json"
        output_name = (
            input_path.name.replace(".segmented.json", suffix)
            if input_path.name.endswith(".segmented.json")
            else f"{input_path.stem}{suffix}"
        )
        output_path = INTERMEDIATE_DIR / output_name

        write_json(result, output_path)
        write_log(f"OK | protected={input_path} | output={output_path}")
        print(f"Protection complete: {output_path}")
        return 0
    except Exception as exc:
        write_log(f"ERROR | file={input_path} | error={repr(exc)}")
        print(f"Protection failed: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
