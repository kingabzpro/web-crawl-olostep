import re
from pathlib import Path
from urllib.parse import urlparse

import gradio as gr

import crawl_docs_with_olostep as backend


ROOT_DIR = Path(__file__).resolve().parent


def folder_name_from_url(url: str) -> str:
    parsed = urlparse(url.strip())
    host = (parsed.netloc or "output").lower()
    path = parsed.path.strip("/")

    if not path:
        return host

    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", path).strip("-")
    return f"{host}__{slug}" if slug else host


def parse_patterns(text: str) -> list[str]:
    raw_items = text.replace(",", "\n").splitlines()
    return [item.strip() for item in raw_items if item.strip()]


def list_markdown_files(output_dir: Path) -> list[str]:
    if not output_dir.exists():
        return []
    return [path.name for path in sorted(output_dir.glob("*.md"))]


def read_file(output_dir: str, filename: str | None) -> str:
    if not output_dir or not filename:
        return ""

    path = Path(output_dir) / filename
    if not path.exists():
        return ""

    return path.read_text(encoding="utf-8")


def render_preview(output_dir: str, filename: str | None) -> str:
    content = read_file(output_dir, filename)
    if not content:
        return ""

    match = re.match(r"^---\n(.*?)\n---\n+", content, flags=re.DOTALL)
    if not match:
        return content

    source_url = ""
    for line in match.group(1).splitlines():
        if line.startswith("source_url:"):
            source_url = line.partition(":")[2].strip()
            break

    body = content[match.end():].strip()
    if source_url:
        return f"[Source URL]({source_url})\n\n{body}"
    return body


def suggested_output_dir(url: str) -> str:
    return str(ROOT_DIR / folder_name_from_url(url))


def output_state(output_dir: str):
    files = list_markdown_files(Path(output_dir))
    selected = files[0] if files else None
    preview = render_preview(output_dir, selected)
    return gr.update(choices=files, value=selected), preview


def clear_output(url: str):
    output_dir = Path(suggested_output_dir(url))
    if output_dir.exists():
        for path in output_dir.glob("*.md"):
            path.unlink()

    return (
        "Cleared crawl output.",
        str(output_dir),
        gr.update(choices=[], value=None),
        "",
    )


def run_crawl(
    start_url: str,
    max_pages: float,
    max_depth: float,
    include_urls_text: str,
    exclude_urls_text: str,
):
    output_dir = Path(suggested_output_dir(start_url))
    include_urls = parse_patterns(include_urls_text) or ["/**"]
    exclude_urls = parse_patterns(exclude_urls_text)
    backend.START_URL = start_url.strip()
    backend.MAX_PAGES = int(max_pages)
    backend.MAX_DEPTH = int(max_depth)
    backend.INCLUDE_URLS = include_urls
    backend.EXCLUDE_URLS = exclude_urls
    backend.OUTPUT_DIR = output_dir

    try:
        backend.main()
    except Exception as exc:
        return (
            f"Error: `{exc}`",
            str(output_dir),
            gr.update(choices=[], value=None),
            "",
        )

    files = list_markdown_files(output_dir)
    selected_file = files[0] if files else None
    preview = render_preview(str(output_dir), selected_file)
    status = f"Saved `{len(files)}` files in `{output_dir.name}`"

    return (
        status,
        str(output_dir),
        gr.update(choices=files, value=selected_file),
        preview,
    )


with gr.Blocks(title="Olostep Crawl App", fill_width=True, fill_height=True) as demo:
    gr.Markdown("## Olostep Crawl App")
    current_output_dir = gr.State(suggested_output_dir(backend.START_URL))

    with gr.Row(equal_height=True):
        start_url = gr.Textbox(label="Start URL", value=backend.START_URL, scale=6)
        max_pages = gr.Number(label="Max Pages", value=backend.MAX_PAGES, precision=0, scale=1)
        max_depth = gr.Number(label="Max Depth", value=backend.MAX_DEPTH, precision=0, scale=1)
        run_button = gr.Button("Run Crawl", variant="primary", scale=1, size="lg")
        clear_button = gr.Button("Clear", variant="secondary", scale=1, size="lg")

    with gr.Accordion("Advanced", open=False):
        with gr.Row():
            include_urls = gr.Textbox(
                label="Include URLs",
                value="\n".join(backend.INCLUDE_URLS),
                lines=3,
                placeholder="One pattern per line or comma-separated",
            )
            exclude_urls = gr.Textbox(
                label="Exclude URLs",
                value="\n".join(backend.EXCLUDE_URLS),
                lines=3,
                placeholder="One pattern per line or comma-separated",
            )

    status = gr.Markdown()

    with gr.Row():
        files = gr.Dropdown(label="Files", choices=[], scale=1)

    with gr.Row(equal_height=True):
        with gr.Column(scale=5):
            preview = gr.Markdown(label="Markdown Preview", height=420)

    start_url.change(
        lambda url: (suggested_output_dir(url),) + output_state(suggested_output_dir(url)),
        inputs=start_url,
        outputs=[current_output_dir, files, preview],
    )

    run_button.click(
        run_crawl,
        inputs=[start_url, max_pages, max_depth, include_urls, exclude_urls],
        outputs=[status, current_output_dir, files, preview],
    )

    clear_button.click(
        clear_output,
        inputs=[start_url],
        outputs=[status, current_output_dir, files, preview],
    )

    files.change(render_preview, inputs=[current_output_dir, files], outputs=preview)

    demo.load(
        lambda: output_state(suggested_output_dir(backend.START_URL)),
        outputs=[files, preview],
    )


if __name__ == "__main__":
    demo.launch(
        theme=gr.themes.Soft(),
    )
