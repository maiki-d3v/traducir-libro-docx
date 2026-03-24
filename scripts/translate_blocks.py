#!/usr/bin/env python3
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
BLOCK_TEMPLATES_DIR = TEMPLATES_DIR / "block_prompts"
INTERMEDIATE_DIR = BASE_DIR / "workspace" / "intermediate"
LOGS_DIR = BASE_DIR / "workspace" / "logs"


DEFAULT_MODEL = os.getenv("TRANSLATION_MODEL", "gpt-4.1")
DEFAULT_PROVIDER = os.getenv("TRANSLATION_PROVIDER", "mock")  # mock | openai_compatible
DEFAULT_API_URL = os.getenv("OPENAI_COMPATIBLE_API_URL", "").strip()
DEFAULT_API_KEY = os.getenv("OPENAI_COMPATIBLE_API_KEY", "").strip()


BLOCK_PROMPT_MAP = {
    "prose": "prose.md",
    "chapter_title": "heading.md",
    "section_title": "heading.md",
    "subsection_title": "heading.md",
    "definition": "theorem.md",
    "theorem": "theorem.md",
    "lemma": "theorem.md",
    "proposition": "theorem.md",
    "corollary": "theorem.md",
    "proof": "proof.md",
    "example": "prose.md",
    "exercise": "prose.md",
    "question": "prose.md",
    "algorithm": "prose.md",
    "code_block": "code_block.md",
    "console_command": "code_block.md",
    "reference": "reference.md",
    "figure_caption": "figure_caption.md",
    "table": "table.md",
    "quote": "prose.md",
    "callout": "prose.md",
    "footnote": "prose.md",
    "list_item": "prose.md",
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
    log_path = LOGS_DIR / "translate_blocks.log"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(message + "\n")


def read_text_file(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def load_master_prompt() -> str:
    return read_text_file(TEMPLATES_DIR / "master_prompt.md")


def load_block_prompt(semantic_type: str) -> str:
    filename = BLOCK_PROMPT_MAP.get(semantic_type, "prose.md")
    return read_text_file(BLOCK_TEMPLATES_DIR / filename)


def format_terminology_memory(data: Dict[str, Any]) -> str:
    # Espacio para evolución futura. Por ahora leemos si existe en raíz.
    terminology = data.get("terminology_memory", {})
    if not terminology:
        return "No terminology memory provided."

    return json.dumps(terminology, ensure_ascii=False, indent=2)


def build_system_prompt(document_data: Dict[str, Any], semantic_type: str) -> str:
    master_prompt = load_master_prompt()
    block_prompt = load_block_prompt(semantic_type)
    terminology = format_terminology_memory(document_data)

    return "\n\n".join(
        part for part in [
            master_prompt,
            f"Block semantic type: {semantic_type}",
            "Terminology memory:",
            terminology,
            "Additional block-specific instructions:",
            block_prompt,
            "Critical instruction: preserve all placeholders exactly as they appear.",
        ]
        if part
    )


def build_user_prompt(block: Dict[str, Any]) -> str:
    semantic_type = block.get("semantic_type", "prose")
    protected_text = block.get("protected_text", block.get("text", ""))

    return (
        f"Translate the following block.\n\n"
        f"Block ID: {block.get('block_id')}\n"
        f"Semantic type: {semantic_type}\n"
        f"Translation mode: {block.get('translation_mode')}\n\n"
        f"Source content:\n{protected_text}\n"
    )


def call_openai_compatible_api(system_prompt: str, user_prompt: str) -> str:
    if not DEFAULT_API_URL:
        raise RuntimeError("OPENAI_COMPATIBLE_API_URL is not configured.")
    if not DEFAULT_API_KEY:
        raise RuntimeError("OPENAI_COMPATIBLE_API_KEY is not configured.")

    payload = {
        "model": DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
    }

    request = urllib.request.Request(
        DEFAULT_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEFAULT_API_KEY}",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=120) as response:
        raw = response.read().decode("utf-8")
        data = json.loads(raw)

    try:
        return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        raise RuntimeError(f"Unexpected API response format: {data}") from exc


def translate_text(document_data: Dict[str, Any], block: Dict[str, Any]) -> str:
    provider = DEFAULT_PROVIDER.lower()
    semantic_type = block.get("semantic_type", "prose")
    source_text = block.get("protected_text", block.get("text", ""))

    if not source_text:
        return ""

    if provider == "mock":
        # Modo de prueba local: no traduce, solo deja el contenido protegido igual.
        return source_text

    if provider == "openai_compatible":
        system_prompt = build_system_prompt(document_data, semantic_type)
        user_prompt = build_user_prompt(block)
        return call_openai_compatible_api(system_prompt, user_prompt)

    raise RuntimeError(f"Unsupported TRANSLATION_PROVIDER: {DEFAULT_PROVIDER}")


def should_translate_block(block: Dict[str, Any]) -> bool:
    semantic_type = block.get("semantic_type")
    if semantic_type == "empty":
        return False
    return True


def translate_table_block(document_data: Dict[str, Any], block: Dict[str, Any]) -> Dict[str, Any]:
    translated_block = dict(block)
    translated_rows = []

    for row in block.get("rows", []):
        translated_row = []
        for cell in row:
            cell_copy = dict(cell)
            translated_paragraphs = []

            for paragraph in cell.get("paragraphs", []):
                p_copy = dict(paragraph)
                pseudo_block = {
                    "block_id": f"{block.get('block_id')}::cell[{cell.get('row_index')}:{cell.get('col_index')}]",
                    "semantic_type": "table",
                    "translation_mode": "translate_text_only",
                    "protected_text": paragraph.get("protected_text", paragraph.get("text", "")),
                    "text": paragraph.get("text", ""),
                }
                translated_text = translate_text(document_data, pseudo_block)
                p_copy["translated_text"] = translated_text
                translated_paragraphs.append(p_copy)

            cell_copy["paragraphs"] = translated_paragraphs
            cell_copy["translated_text"] = "\n".join(
                p.get("translated_text", "") for p in translated_paragraphs
            )
            translated_row.append(cell_copy)

        translated_rows.append(translated_row)

    translated_block["rows"] = translated_rows
    translated_block["translated_text"] = None
    return translated_block


def translate_standard_block(document_data: Dict[str, Any], block: Dict[str, Any]) -> Dict[str, Any]:
    translated_block = dict(block)

    if not should_translate_block(block):
        translated_block["translated_text"] = block.get("protected_text", block.get("text", ""))
        translated_block["translation_status"] = "skipped"
        return translated_block

    translated_text = translate_text(document_data, block)
    translated_block["translated_text"] = translated_text
    translated_block["translation_status"] = "translated"
    return translated_block


def translate_block(document_data: Dict[str, Any], block: Dict[str, Any]) -> Dict[str, Any]:
    if block.get("kind") == "table":
        translated_block = translate_table_block(document_data, block)
        translated_block["translation_status"] = "translated"
        return translated_block

    return translate_standard_block(document_data, block)


def translate_document(data: Dict[str, Any]) -> Dict[str, Any]:
    source_blocks = data.get("blocks", []) or []
    translated_blocks: List[Dict[str, Any]] = []

    stats = {
        "total_blocks": len(source_blocks),
        "translated_blocks": 0,
        "skipped_blocks": 0,
        "provider": DEFAULT_PROVIDER,
        "model": DEFAULT_MODEL,
    }

    for block in source_blocks:
        translated_block = translate_block(data, block)
        translated_blocks.append(translated_block)

        if translated_block.get("translation_status") == "translated":
            stats["translated_blocks"] += 1
        else:
            stats["skipped_blocks"] += 1

    return {
        "document_metadata": data.get("document_metadata", {}),
        "upstream_statistics": data.get("upstream_statistics", {}),
        "segmentation_statistics": data.get("segmentation_statistics", {}),
        "protection_statistics": data.get("protection_statistics", {}),
        "translation_statistics": stats,
        "blocks": translated_blocks,
    }


def main() -> int:
    ensure_dirs()

    if len(sys.argv) < 2:
        print("Usage: python translate_blocks.py <protected.json>")
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
        result = translate_document(data)

        suffix = ".translated.json"
        output_name = (
            input_path.name.replace(".protected.json", suffix)
            if input_path.name.endswith(".protected.json")
            else f"{input_path.stem}{suffix}"
        )
        output_path = INTERMEDIATE_DIR / output_name

        write_json(result, output_path)
        write_log(
            f"OK | translated={input_path} | output={output_path} "
            f"| provider={DEFAULT_PROVIDER} | model={DEFAULT_MODEL}"
        )
        print(f"Translation complete: {output_path}")
        return 0
    except Exception as exc:
        write_log(f"ERROR | file={input_path} | error={repr(exc)}")
        print(f"Translation failed: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
