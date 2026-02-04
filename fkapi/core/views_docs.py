"""
Simple views to serve markdown documentation.
Minimal implementation - just reads .md files and renders them.
"""

import re
from pathlib import Path

import markdown
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

_EXCLUDED_DIRS = {"tmp", "__pycache__", ".git"}


def get_docs_dir() -> Path:
    """Get docs directory path."""
    project_root = Path(__file__).parent.parent.parent
    return project_root / "docs"


def _docs_resolve_file_path(docs_dir: Path, doc_path: str) -> Path:
    if doc_path == "README" or not doc_path:
        return docs_dir / "README.md"
    return docs_dir / f"{doc_path}.md"


def _docs_validate_path(file_path: Path, doc_path: str) -> None:
    if any(excluded in str(file_path) for excluded in _EXCLUDED_DIRS):
        raise Http404(f"Documentation not found: {doc_path}")
    if not file_path.exists():
        raise Http404(f"Documentation not found: {doc_path}")


def _docs_read_and_convert(file_path: Path) -> tuple[str, str]:
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        raise Http404(f"Error reading file: {e}") from e
    md = markdown.Markdown(extensions=["fenced_code", "tables", "toc", "nl2br"])
    html_content = md.convert(content)
    toc = md.toc if hasattr(md, "toc") else ""
    return html_content, toc


def _docs_extract_title(file_path: Path, html_content: str) -> str:
    title = file_path.stem.replace("_", " ").replace("-", " ").title()
    if not html_content:
        return title
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html_content, re.IGNORECASE)
    if h1:
        return re.sub(r"<[^>]+>", "", h1.group(1)).strip()
    return title


def _docs_format_doc_name(stem: str) -> str:
    return stem.replace("_", " ").replace("-", " ").title()


def _docs_build_sidebar(docs_dir: Path) -> tuple[list[dict], dict]:
    doc_files = []
    subdirs = {}
    if not docs_dir.exists():
        return doc_files, subdirs
    for f in sorted(docs_dir.glob("*.md")):
        if f.name != "README.md":
            doc_files.append({"name": _docs_format_doc_name(f.stem), "path": f.stem})
    for subdir in sorted(docs_dir.iterdir()):
        if not subdir.is_dir() or subdir.name.startswith(".") or subdir.name in _EXCLUDED_DIRS:
            continue
        subdir_docs = [
            {"name": _docs_format_doc_name(f.stem), "path": f"{subdir.name}/{f.stem}"}
            for f in sorted(subdir.glob("*.md"))
        ]
        if subdir_docs:
            subdirs[subdir.name.title()] = subdir_docs
    return doc_files, subdirs


@require_GET
def docs_index(request: HttpRequest) -> HttpResponse:
    """Main docs index - redirects to README."""
    return docs_view(request, "README")


@require_GET
def docs_view(request: HttpRequest, doc_path: str = "README") -> HttpResponse:
    """
    Render a markdown file.

    Args:
        doc_path: Path like "README", "GETTING_STARTED", "api/endpoint-catalog"
    """
    docs_dir = get_docs_dir()
    file_path = _docs_resolve_file_path(docs_dir, doc_path)
    _docs_validate_path(file_path, doc_path)
    html_content, toc = _docs_read_and_convert(file_path)
    title = _docs_extract_title(file_path, html_content)
    doc_files, subdirs = _docs_build_sidebar(docs_dir)
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
