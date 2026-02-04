from bs4 import BeautifulSoup
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

ALLOWED_TAGS = {
    "p", "div", "span", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "a", "strong", "em", "b", "i", "code", "pre",
    "blockquote", "table", "thead", "tbody", "tr", "th", "td",
    "hr", "br", "img",
}
ALLOWED_ATTRS = {"a": ["href"], "img": ["src", "alt"]}


@register.filter
def sanitize_html(value: str) -> str:
    if not value:
        return ""
    soup = BeautifulSoup(value, "html.parser")
    for tag in soup.find_all(True):
        if tag.name not in ALLOWED_TAGS:
            tag.decompose()
            continue
        attrs_ok = ALLOWED_ATTRS.get(tag.name, [])
        bad_attrs = [a for a in tag.attrs if a not in attrs_ok or a.startswith("on")]
        for attr in bad_attrs:
            del tag[attr]
    return mark_safe(str(soup))
