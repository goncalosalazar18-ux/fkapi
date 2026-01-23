"""
Simple views to serve markdown documentation.
Minimal implementation - just reads .md files and renders them.
"""

from pathlib import Path

import markdown
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render


def get_docs_dir() -> Path:
    """Get docs directory path."""
    # From fkapi/core/views_docs.py, go up to project root
    # fkapi/core/views_docs.py -> fkapi/core/ -> fkapi/ -> FKApi/ -> docs/
    project_root = Path(__file__).parent.parent.parent
    return project_root / "docs"


def docs_index(request: HttpRequest) -> HttpResponse:
    """Main docs index - redirects to README."""
    return docs_view(request, "README")


def docs_view(request: HttpRequest, doc_path: str = "README") -> HttpResponse:
    """
    Render a markdown file.

    Args:
        doc_path: Path like "README", "GETTING_STARTED", "api/endpoint-catalog"
    """
    docs_dir = get_docs_dir()

    # Build file path
    if doc_path == "README" or not doc_path:
        file_path = docs_dir / "README.md"
    elif "/" in doc_path:
        file_path = docs_dir / f"{doc_path}.md"
    else:
        file_path = docs_dir / f"{doc_path}.md"

    # Check if file is in excluded directory
    excluded_dirs = {"tmp", "__pycache__", ".git"}
    if any(excluded in str(file_path) for excluded in excluded_dirs):
        raise Http404(f"Documentation not found: {doc_path}")

    if not file_path.exists():
        raise Http404(f"Documentation not found: {doc_path}")

    # Read markdown
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        raise Http404(f"Error reading file: {e}") from e

    # Convert to HTML
    md = markdown.Markdown(extensions=["fenced_code", "tables", "toc", "nl2br"])
    html_content = md.convert(content)
    toc = md.toc if hasattr(md, "toc") else ""

    # Get title from first h1
    title = file_path.stem.replace("_", " ").replace("-", " ").title()
    if html_content:
        import re

        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html_content, re.IGNORECASE)
        if h1:
            title = re.sub(r"<[^>]+>", "", h1.group(1)).strip()

    # List available docs for sidebar
    doc_files = []
    subdirs = {}
    excluded_dirs = {"tmp", "__pycache__", ".git"}  # Exclude untracked/temporary directories

    if docs_dir.exists():
        # Top-level files
        for f in sorted(docs_dir.glob("*.md")):
            if f.name != "README.md":
                doc_files.append({"name": f.stem.replace("_", " ").replace("-", " ").title(), "path": f.stem})

        # Subdirectories (api/, decisions/, etc.)
        for subdir in sorted(docs_dir.iterdir()):
            if subdir.is_dir() and not subdir.name.startswith(".") and subdir.name not in excluded_dirs:
                subdir_docs = []
                for f in sorted(subdir.glob("*.md")):
                    subdir_docs.append(
                        {"name": f.stem.replace("_", " ").replace("-", " ").title(), "path": f"{subdir.name}/{f.stem}"}
                    )
                if subdir_docs:
                    subdirs[subdir.name.title()] = subdir_docs

    return render(
        request,
        "core/docs.html",
        {
            "title": title,
            "content": html_content,
            "toc": toc,
            "doc_files": doc_files,
            "subdirs": subdirs,
            "current_path": doc_path,
        },
    )
