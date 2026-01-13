from __future__ import annotations

from dataclasses import dataclass

from bs4 import BeautifulSoup
from bs4.element import Tag


@dataclass(frozen=True)
class FactTable:
    """Lightweight representation of the kit fact table."""

    element: Tag
    rows: list[Tag]
    values: dict[str, Tag]

    def get_value_cell(self, label: str) -> Tag | None:
        return self.values.get(label.strip().lower())

    def get_text(self, label: str) -> str | None:
        cell = self.get_value_cell(label)
        if cell is not None:
            return cell.get_text(strip=True)
        return None


@dataclass(frozen=True)
class KitPageData:
    """Complete data extracted from a kit page."""

    team_name: str
    team_slug: str
    season_text: str | None
    rating: float
    main_img_url: str
    kit_type: str
    brand_name: str
    brand_slug: str
    design: str | None
    colors_str: str | None
    competitions_html: str


def extract_fact_table(soup: BeautifulSoup) -> FactTable:
    """Extract the fact table and return a normalized helper object."""
    table = soup.find("table", class_="fact-table")
    if table is None:
        raise ValueError("Kit fact table not found in HTML")

    rows = table.find_all("tr")
    if not rows:
        raise ValueError("Kit fact table has no rows")

    values: dict[str, Tag] = {}
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        label = cells[0].get_text(strip=True)
        if not label:
            continue
        values[label.strip().lower()] = cells[1]

    return FactTable(element=table, rows=rows, values=values)


def parse_kit_page(soup: BeautifulSoup) -> KitPageData:
    """Parse the kit page and return a KitPageData object."""
    fact_table = extract_fact_table(soup)

    # Team
    team_cell = fact_table.get_value_cell("team")
    if team_cell is None:
        raise ValueError("Team data not found")
    team_name = team_cell.get_text(strip=True)
    team_link = team_cell.find("a")
    if not team_link or not team_link.get("href"):
        raise ValueError("Team link not found")
    team_slug = team_link["href"].replace("/", "")

    # Season
    season_text = fact_table.get_text("season")

    # Rating
    rating = 0.0
    rating_span = soup.find("span", id="rating")
    rating_details = soup.find("span", id="rating-details-no")
    if rating_span and rating_span.text.strip() and not rating_details:
        try:
            rating = float(rating_span.text.strip())
        except ValueError:
            rating = 0.0

    # Main Image
    main_img = soup.find("img", class_="top-image")
    if not main_img:
        raise ValueError("Main image not found")
    main_img_url = main_img.get("data-src") or main_img.get("src")
    if not main_img_url:
        raise ValueError("Main image URL not found")

    # Kit Type
    kit_type = fact_table.get_text("kit type") or fact_table.get_text("type")
    if not kit_type:
        raise ValueError("Kit type not found")

    # Brand
    brand_cell = fact_table.get_value_cell("brand")
    if not brand_cell:
        raise ValueError("Brand not found")
    brand_name = brand_cell.get_text(strip=True)
    brand_link = brand_cell.find("a")
    if not brand_link or not brand_link.get("href"):
        raise ValueError("Brand link not found")
    brand_slug = brand_link["href"].replace("/", "")

    # Design
    design = fact_table.get_text("design")

    # Colors
    colors_str = fact_table.get_text("colors")

    # Competitions (League)
    comp_cell = fact_table.get_value_cell("league")
    if not comp_cell:
        raise ValueError("Competitions (League) not found")
    competitions_html = str(comp_cell)

    return KitPageData(
        team_name=team_name,
        team_slug=team_slug,
        season_text=season_text,
        rating=rating,
        main_img_url=main_img_url,
        kit_type=kit_type,
        brand_name=brand_name,
        brand_slug=brand_slug,
        design=design,
        colors_str=colors_str,
        competitions_html=competitions_html,
    )
