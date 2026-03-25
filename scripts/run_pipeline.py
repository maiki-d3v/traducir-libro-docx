#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path
from typing import List


BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
WORKSPACE_DIR = BASE_DIR / "workspace"
INPUT_DIR = WORKSPACE_DIR / "input"
INTERMEDIATE_DIR = WORKSPACE_DIR / "intermediate"
OUTPUT_DIR = WORKSPACE_DIR / "output"
LOGS_DIR = WORKSPACE_DIR / "logs"

EXPORT_SCRIPT = SCRIPTS_DIR / "export_github.sh"


PIPELINE_STEPS = [
    ("extract", "extract_xml.py"),
    ("segment", "segment_blocks.py"),
    ("protect", "protect_content.py"),
    ("translate", "translate_blocks.py"),
    ("restore", "restore_content.py"),
    ("validate", "validate_translation.py"),
    ("reconstruct", "reconstruct_xml.py"),
]


def ensure_dirs() -> None:
    for path in [INPUT_DIR, INTERMEDIATE_DIR, OUTPUT_DIR, LOGS_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def run_step(script_name: str, input_path: Path) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(SCRIPTS_DIR / script_name), str(input_path)]
    return subprocess.run(cmd, capture_output=True, text=True)


def run_export(output_path: Path) -> subprocess.CompletedProcess:
    cmd = [str(EXPORT_SCRIPT), str(output_path)]
    return subprocess.run(cmd, capture_output=True, text=True)


def expected_next_path(step_name: str, current_path: Path) -> Path:
    name = current_path.name

    if step_name == "extract":
        out = name.replace(".xml", ".extracted.json")
        return INTERMEDIATE_DIR / out

    if step_name == "segment":
        out = name.replace(".extracted.json", ".segmented.json")
        return INTERMEDIATE_DIR / out

    if step_name == "protect":
        out = name.replace(".segmented.json", ".protected.json")
        return INTERMEDIATE_DIR / out

    if step_name == "translate":
        out = name.replace(".protected.json", ".translated.json")
        return INTERMEDIATE_DIR / out

    if step_name == "restore":
        out = name.replace(".translated.json", ".restored.json")
        return INTERMEDIATE_DIR / out

    if step_name == "validate":
        out = name.replace(".restored.json", ".validated.json")
        return INTERMEDIATE_DIR / out

    if step_name == "reconstruct":
        stem = name.replace(".validated.json", "")
        return OUTPUT_DIR / f"{stem}.translated.en.xml"

    raise ValueError(f"Unknown step: {step_name}")


def write_pipeline_log(lines: List[str]) -> None:
    log_path = LOGS_DIR / "run_pipeline.log"
    with log_path.open("a", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")


def append_process_output(pipeline_log: List[str], result: subprocess.CompletedProcess) -> None:
    if result.stdout.strip():
        pipeline_log.append(f"STDOUT | {result.stdout.strip()}")
    if result.stderr.strip():
        pipeline_log.append(f"STDERR | {result.stderr.strip()}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the full XML translation pipeline.")
    parser.add_argument("input_xml", help="Path to the input .xml file")
    parser.add_argument(
        "--stop-after",
        choices=[name for name, _ in PIPELINE_STEPS],
        help="Stop after a given pipeline step",
    )
    parser.add_argument(
        "--export-github",
        action="store_true",
        help="Export the final XML to the configured Git repository using export_github.sh",
    )
    args = parser.parse_args()

    ensure_dirs()

    input_path = Path(args.input_xml).resolve()
    if not input_path.exists():
        print(f"Error: file not found: {input_path}")
        return 1

    if input_path.suffix.lower() != ".xml":
        print("Error: input file must be a .xml")
        return 1

    current_path = input_path
    pipeline_log: List[str] = [f"START | input={input_path}"]

    for step_name, script_name in PIPELINE_STEPS:
        print(f"Running step: {step_name}")
        result = run_step(script_name, current_path)

        pipeline_log.append(
            f"STEP | name={step_name} | script={script_name} | returncode={result.returncode}"
        )
        append_process_output(pipeline_log, result)

        if result.stdout.strip():
            print(result.stdout.strip())

        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)

        if result.returncode != 0:
            pipeline_log.append(f"FAILED | step={step_name}")
            write_pipeline_log(pipeline_log)
            print(f"Pipeline failed at step: {step_name}")
            return result.returncode

        next_path = expected_next_path(step_name, current_path)
        pipeline_log.append(f"OUTPUT | step={step_name} | path={next_path}")

        current_path = next_path

        if args.stop_after == step_name:
            pipeline_log.append(f"STOPPED | after={step_name}")
            write_pipeline_log(pipeline_log)
            print(f"Pipeline stopped after step: {step_name}")
            print(f"Current output: {current_path}")
            return 0

    if args.export_github:
        if not EXPORT_SCRIPT.exists():
            pipeline_log.append(f"FAILED | export_script_missing={EXPORT_SCRIPT}")
            write_pipeline_log(pipeline_log)
            print(f"Export script not found: {EXPORT_SCRIPT}")
            return 2

        print("Running GitHub export...")
        export_result = run_export(current_path)

        pipeline_log.append(
            f"EXPORT | script={EXPORT_SCRIPT} | returncode={export_result.returncode}"
        )
        append_process_output(pipeline_log, export_result)

        if export_result.stdout.strip():
            print(export_result.stdout.strip())

        if export_result.stderr.strip():
            print(export_result.stderr.strip(), file=sys.stderr)

        if export_result.returncode != 0:
            pipeline_log.append("FAILED | step=export_github")
            write_pipeline_log(pipeline_log)
            print("Pipeline completed, but GitHub export failed.")
            print(f"Final XML is still available at: {current_path}")
            return export_result.returncode

        pipeline_log.append("DONE | export_github=ok")
    else:
        pipeline_log.append("DONE | export_github=skipped")

    pipeline_log.append(f"FINAL_OUTPUT | {current_path}")
    write_pipeline_log(pipeline_log)

    print("Pipeline completed successfully.")
    print(f"Final output: {current_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
