import os
import subprocess
import sys
import zipfile
from pathlib import Path

import gradio as gr


ROOT_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = ROOT_DIR / "crawl_docs_with_olostep.py"
OUTPUT_DIR = ROOT_DIR / "olostep_docs_output"
ZIP_PATH = ROOT_DIR / "olostep_docs_output.zip"


APP_THEME = gr.themes.Ocean(
    primary_hue="teal",
    secondary_hue="amber",
    neutral_hue="stone",
    font=(
        gr.themes.GoogleFont("Space Grotesk"),
        "ui-sans-serif",
        "system-ui",
        "sans-serif",
    ),
    font_mono=(
        gr.themes.GoogleFont("IBM Plex Mono"),
        "Consolas",
        "monospace",
    ),
).set(
    body_background_fill="#f5efe2",
    body_background_fill_dark="#10261f",
    block_background_fill="#fffaf0",
    block_border_width="1px",
    block_border_color="#d8ccb6",
    button_primary_background_fill="#0f766e",
    button_primary_background_fill_hover="#115e59",
    button_secondary_background_fill="#f59e0b",
    button_secondary_background_fill_hover="#d97706",
    link_text_color="#0f766e",
    link_text_color_hover="#115e59",
)


APP_CSS = """
body {
  background:
    radial-gradient(circle at top left, rgba(245, 158, 11, 0.14), transparent 28%),
    radial-gradient(circle at top right, rgba(15, 118, 110, 0.18), transparent 30%),
    linear-gradient(180deg, #f7f1e4 0%, #f3ede1 100%);
}

.app-shell {
  max-width: 1240px;
  margin: 0 auto;
}

.hero {
  padding: 28px;
  border: 1px solid rgba(109, 92, 61, 0.18);
  border-radius: 24px;
  background:
    linear-gradient(135deg, rgba(255, 250, 240, 0.98), rgba(244, 236, 213, 0.92));
  box-shadow: 0 18px 50px rgba(46, 40, 29, 0.08);
}

.hero-kicker {
  display: inline-block;
  margin-bottom: 12px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(15, 118, 110, 0.12);
  color: #0f766e;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero h1 {
  margin: 0;
  font-size: 3rem;
  line-height: 0.95;
  letter-spacing: -0.04em;
  color: #1f2937;
}

.hero p {
  margin: 14px 0 0;
  max-width: 760px;
  color: #4b5563;
  font-size: 1rem;
}

.panel {
  border-radius: 22px;
}

.status-card {
  border-left: 6px solid #0f766e;
}
"""


def list_output_files() -> list[Path]:
    if not OUTPUT_DIR.exists():
        return []
    return sorted(OUTPUT_DIR.glob("*.md"))


def build_zip_archive() -> str | None:
    files = list_output_files()
    if not files:
        return None

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, arcname=f"{OUTPUT_DIR.name}/{path.name}")

    return str(ZIP_PATH)


def parse_saved_markdown(path: Path) -> tuple[str, str]:
    content = path.read_text(encoding="utf-8")
    source_url = ""
    body = content

    if content.startswith("---\n"):
        parts = content.split("---\n", 2)
        if len(parts) == 3:
            frontmatter = parts[1]
            body = parts[2].lstrip()
            for line in frontmatter.splitlines():
                if line.startswith("source_url:"):
                    source_url = line.partition(":")[2].strip()
                    break

    return source_url, body


def build_file_rows(files: list[Path]) -> list[list[str]]:
    rows: list[list[str]] = []
    for path in files:
        source_url, _ = parse_saved_markdown(path)
        rows.append(
            [
                path.name,
                source_url,
                f"{path.stat().st_size / 1024:.1f} KB",
            ]
        )
    return rows


def build_status(title: str, detail: str, files_count: int) -> str:
    return (
        f"### {title}\n\n"
        f"{detail}\n\n"
        f"- Output folder: `{OUTPUT_DIR}`\n"
        f"- Saved markdown files: `{files_count}`\n"
        f"- Backend: `{SCRIPT_PATH.name}`"
    )


def preview_file(filename: str | None) -> tuple[str, str, str]:
    if not filename:
        return "", "_No file selected._", ""

    path = OUTPUT_DIR / filename
    if not path.exists():
        return "", "_Selected file is missing._", ""

    source_url, body = parse_saved_markdown(path)
    return source_url, body, body


def load_dashboard(selected_file: str | None = None):
    files = list_output_files()
    file_names = [path.name for path in files]
    file_rows = build_file_rows(files)
    zip_path = build_zip_archive()

    if not files:
        return (
            build_status("Ready", "Run the crawler to generate clean markdown files.", 0),
            file_rows,
            gr.update(choices=[], value=None),
            "",
            "_No crawl output yet._",
            "",
            zip_path,
            "",
        )

    active_file = selected_file if selected_file in file_names else file_names[0]
    source_url, rendered_body, raw_body = preview_file(active_file)

    return (
        build_status("Output Ready", "Browse the latest crawl results below.", len(files)),
        file_rows,
        gr.update(choices=file_names, value=active_file),
        source_url,
        rendered_body,
        raw_body,
        zip_path,
        "",
    )


def run_backend_script():
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"

    process = subprocess.Popen(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=ROOT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=env,
    )

    log_output = ""
    baseline = load_dashboard()
    yield (
        build_status("Running Crawl", "Launching backend script...", len(list_output_files())),
        baseline[1],
        baseline[2],
        baseline[3],
        baseline[4],
        baseline[5],
        baseline[6],
        log_output,
    )

    assert process.stdout is not None
    for line in process.stdout:
        clean_line = line.replace("\r", "").rstrip()
        if not clean_line:
            continue
        log_output = f"{log_output}{clean_line}\n"
        yield (
            build_status(
                "Running Crawl",
                clean_line,
                len(list_output_files()),
            ),
            baseline[1],
            baseline[2],
            baseline[3],
            baseline[4],
            baseline[5],
            baseline[6],
            log_output,
        )

    return_code = process.wait()
    if return_code != 0:
        files_count = len(list_output_files())
        yield (
            build_status(
                "Run Failed",
                f"The backend script exited with code {return_code}.",
                files_count,
            ),
            baseline[1],
            baseline[2],
            baseline[3],
            baseline[4],
            baseline[5],
            baseline[6],
            log_output,
        )
        return

    final_state = load_dashboard()
    files_count = len(list_output_files())
    yield (
        build_status("Crawl Complete", "Fresh crawl results are ready to inspect.", files_count),
        final_state[1],
        final_state[2],
        final_state[3],
        final_state[4],
        final_state[5],
        final_state[6],
        log_output,
    )


with gr.Blocks(
    title="Olostep Crawl Studio",
    fill_width=True,
) as demo:
    with gr.Column(elem_classes="app-shell"):
        gr.HTML(
            """
            <section class="hero">
              <div class="hero-kicker">Olostep + Gradio</div>
              <h1>Crawl Studio</h1>
              <p>
                Run the existing crawler script, stream backend logs, inspect cleaned markdown pages,
                and download the latest output folder from one place.
              </p>
            </section>
            """
        )

        with gr.Row():
            with gr.Column(scale=4, elem_classes=["panel", "status-card"]):
                status = gr.Markdown()
                with gr.Row():
                    run_button = gr.Button("Run Crawl", variant="primary", size="lg")
                    refresh_button = gr.Button("Refresh Output", variant="secondary")
                download_zip = gr.File(label="Download Output Zip")
                logs = gr.Code(
                    label="Backend Log",
                    language="shell",
                    lines=16,
                    interactive=False,
                )
                gr.Markdown(
                    "`crawl_docs_with_olostep.py` remains the backend source of truth. "
                    "This app only runs it and reads the generated markdown files."
                )

            with gr.Column(scale=8, elem_classes="panel"):
                files_table = gr.Dataframe(
                    headers=["File", "Source URL", "Size"],
                    datatype=["str", "str", "str"],
                    interactive=False,
                    wrap=True,
                    label="Saved Markdown Files",
                )
                file_selector = gr.Dropdown(
                    label="Preview File",
                    choices=[],
                    interactive=True,
                )
                source_url = gr.Textbox(label="Source URL", interactive=False)
                with gr.Tabs():
                    with gr.Tab("Rendered Preview"):
                        rendered_preview = gr.Markdown()
                    with gr.Tab("Raw Markdown"):
                        raw_preview = gr.Code(
                            language="markdown",
                            interactive=False,
                            lines=24,
                        )

    demo.load(
        load_dashboard,
        outputs=[
            status,
            files_table,
            file_selector,
            source_url,
            rendered_preview,
            raw_preview,
            download_zip,
            logs,
        ],
    )

    refresh_button.click(
        load_dashboard,
        inputs=file_selector,
        outputs=[
            status,
            files_table,
            file_selector,
            source_url,
            rendered_preview,
            raw_preview,
            download_zip,
            logs,
        ],
    )

    run_button.click(
        run_backend_script,
        outputs=[
            status,
            files_table,
            file_selector,
            source_url,
            rendered_preview,
            raw_preview,
            download_zip,
            logs,
        ],
    )

    file_selector.change(
        preview_file,
        inputs=file_selector,
        outputs=[source_url, rendered_preview, raw_preview],
    )


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1).launch(
        theme=APP_THEME,
        css=APP_CSS,
    )
