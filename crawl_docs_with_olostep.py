import os
import re
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from tqdm import tqdm
from olostep import Olostep


START_URL = "https://docs.olostep.com/"
MAX_PAGES = 10
MAX_DEPTH = 1

INCLUDE_URLS = [
    "/**"
]

EXCLUDE_URLS = []

OUTPUT_DIR = Path("olostep_docs_output")


def slugify_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip("/")

    if not path:
        path = "index"

    filename = re.sub(r"[^a-zA-Z0-9/_-]+", "-", path)
    filename = filename.replace("/", "__").strip("-_")

    return f"{filename or 'page'}.md"


def clean_markdown(markdown: str) -> str:
    text = markdown.replace("\r\n", "\n").strip()
    text = re.sub(r"\[\s*\u200b?\s*\]\(#.*?\)", "", text, flags=re.DOTALL)

    lines = [line.rstrip() for line in text.splitlines()]

    start_index = 0
    for index in range(len(lines) - 1):
        title = lines[index].strip()
        underline = lines[index + 1].strip()
        if title and underline and set(underline) == {"="}:
            start_index = index
            break
    else:
        for index, line in enumerate(lines):
            if line.lstrip().startswith("# "):
                start_index = index
                break

    lines = lines[start_index:]

    for index, line in enumerate(lines):
        if line.strip() == "Was this page helpful?":
            lines = lines[:index]
            break

    cleaned_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped in {"Copy page", "YesNo", "⌘I"}:
            continue
        if not stripped and cleaned_lines and not cleaned_lines[-1]:
            continue
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def save_markdown(output_dir: Path, url: str, markdown: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / slugify_url(url)

    content = f"""---
source_url: {url}
---

{markdown}
"""
    filepath.write_text(content, encoding="utf-8")


def clear_output_dir(output_dir: Path) -> None:
    if not output_dir.exists():
        return

    for filepath in output_dir.glob("*.md"):
        filepath.unlink()


def main() -> None:
    load_dotenv()
    api_key = os.getenv("OLOSTEP_API_KEY")

    if not api_key:
        raise RuntimeError("Missing OLOSTEP_API_KEY in your .env file.")

    client = Olostep(api_key=api_key)

    crawl = client.crawls.create(
        start_url=START_URL,
        max_pages=MAX_PAGES,
        max_depth=MAX_DEPTH,
        include_urls=INCLUDE_URLS,
        exclude_urls=EXCLUDE_URLS,
        include_external=False,
        include_subdomain=False,
        follow_robots_txt=True,
    )

    print(f"Started crawl: {crawl.id}")
    crawl.wait_till_done(check_every_n_secs=5)

    pages = list(crawl.pages())
    clear_output_dir(OUTPUT_DIR)

    for page in tqdm(pages, desc="Saving pages"):
        try:
            content = page.retrieve(["markdown"])
            markdown = getattr(content, "markdown_content", None)

            if markdown:
                save_markdown(OUTPUT_DIR, page.url, clean_markdown(markdown))
        except Exception as exc:
            print(f"Failed to retrieve {page.url}: {exc}")

    print(f"Done. Files saved in: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
