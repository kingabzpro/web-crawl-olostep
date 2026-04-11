# Olostep Web Crawl 

<img width="1837" height="845" alt="Screenshot 2026-04-11 151237" src="https://github.com/user-attachments/assets/38d9a159-c345-4b14-abd0-eba22c93fc46" />

Small Olostep crawler project with:
- `crawl_docs_with_olostep.py` for crawling docs pages and saving cleaned markdown
- `app.py` for a simple Gradio UI on top of the crawler

This project is useful if you want to crawl documentation websites, clean the extracted markdown, and quickly inspect the results from a small local web app.

The crawler:
- starts from a target URL
- follows the crawl settings you provide
- removes common docs-site UI noise from the markdown
- saves each crawled page as its own `.md` file

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file:

```env
OLOSTEP_API_KEY=your_api_key_here
```

## Project Files

- `crawl_docs_with_olostep.py`: main crawler script
- `app.py`: Gradio app for running and previewing crawls
- `requirements.txt`: project dependencies
- `.env`: local API key configuration
- generated output folders: saved markdown files for each crawled URL

## Run The Script

```bash
python crawl_docs_with_olostep.py
```

The script uses the values defined in `crawl_docs_with_olostep.py` and saves cleaned markdown files into the configured output folder.

## Run The App

```bash
python app.py
```

The app lets you:
- enter a URL
- set crawl limits
- set include and exclude patterns
- run or clear a crawl
- preview saved markdown files

## Output

The output folder is automatically based on the URL you provide.

Examples:
- `https://docs.olostep.com/` -> `docs.olostep.com`
- `https://docs.olostep.com/get-started/welcome` -> `docs.olostep.com__get-started-welcome`

Each saved markdown file includes:
- the original source URL in frontmatter
- cleaned markdown content for the page

## Notes

- The app and script both require a valid `OLOSTEP_API_KEY`
- The app is a thin wrapper around the crawler script, not a separate crawling backend
- Clear removes saved `.md` files for the current URL-based output folder
