# Standard library imports
import logging
import time
from contextlib import contextmanager
from typing import Any

# Third-party imports
import requests
from bs4 import BeautifulSoup
from colorama import Fore

# Django imports
from django.db import connection, transaction

from core.constants import (
    BASE_URL,
    BRAND_SLUG_SUFFIX,
    COLLECTION_CONTAINER_CLASS,
    CURRENT_CENTURY,
    CURRENT_SEASON_YEAR,
    DEFAULT_LOGO_URL,
    HTTP_STATUS_FORBIDDEN,
    KIT_CLASS,
    KIT_CONTAINER_CLASS,
    KIT_SEASON_CLASS,
    LATEST_PAGE_URL,
    MAX_RETRIES,
    RETRY_DELAY,
    SECTION_DETAILS_CLASS,
)
from core.exceptions import (
    ClubNotFoundError,
    InvalidSeasonError,
    KitNotFoundError,
    RateLimitExceededError,
    ScrapingError,
)
from core.http import http_get
from core.parsers import extract_fact_table, parse_kit_page
from core.services.scraping_service import ScrapingService

# Local imports
from .models import Brand, Club, Competition, Kit, Season, Type_K

logger = logging.getLogger(__name__)


def build_kit_url(slug: str, kit_id: str | None = None) -> str:
    """
    Builds the complete URL for scraping a kit.

    Args:
        slug (str): The kit's base slug
        kit_id (str, optional): The kit's ID for new format URLs

    Returns:
        str: Complete URL for scraping
    """
    if kit_id:
        return f"{BASE_URL}/{slug}/{kit_id}/"
    else:
        # Try to extract kit_id from slug if it ends with digits
        import re
        match = re.match(r'^(.+?)(\d+)$', slug)
        if match:
            base_slug = match.group(1)
            extracted_id = match.group(2)
            return f"{BASE_URL}/{base_slug}/{extracted_id}/"
        else:
            # Fallback to old format, but this will likely fail
            return f"{BASE_URL}/{slug}"


@contextmanager
def db_connection() -> Any:
    try:
        yield
    finally:
        connection.close()


def get_current_season() -> Season:
    """
    Gets the current season (2024).

    Returns:
        Season: Season object corresponding to the current season

    Raises:
        Season.DoesNotExist: If the 2024 season does not exist
    """
    try:
        return Season.objects.get(first_year=CURRENT_SEASON_YEAR)
    except Season.DoesNotExist as e:
        raise Season.DoesNotExist(f"The {CURRENT_SEASON_YEAR} season was not found") from e


def get_season(season_slug: str, season_display: str | None = None) -> Season:
    """
    Retrieves or creates a Season object using the full year from the slug.

    Args:
        season_slug: str - The full URL slug (e.g., 'olympique-marseille-2020-21-third-kit' or 'germany-2024-home-kit')
                          or a direct year string (e.g., '2024', '2023-24', '1999-00')
        season_display: str - Optional display format from the page (e.g., '2020-21' or '2024')

    The function handles both full kit slugs and direct year strings.
    """
    try:
        import re

        # Clean "(Carry-over)" text - we don't differentiate between carry-over and normal seasons
        season_slug = re.sub(r'\s*\(Carry-over\)\s*', '', season_slug, flags=re.IGNORECASE).strip()

        # Check if the input is a 2-digit year format (e.g., '24-25', '23-24', '99-00')
        two_digit_year_match = re.match(r'^(\d{2})(?:-(\d{2}))?$', season_slug)
        if two_digit_year_match and len(season_slug) <= 7:
            first_year_short = two_digit_year_match.group(1)
            second_year_short = two_digit_year_match.group(2)
            first_year_short_int = int(first_year_short)

            # Determine century for 2-digit years:
            # - Years >= 50 are likely from 1900s (1950-1999)
            # - Years < 50 are likely from 2000s (2000-2049)
            # This handles cases like '99-00' -> 1999-00, '24-25' -> 2024-25
            if first_year_short_int >= 50:
                first_century = "19"
            else:
                first_century = "20"

            first_year = first_century + first_year_short

            if second_year_short:
                # Determine century for second year
                second_year_short_int = int(second_year_short)
                first_year_int = int(first_year)
                
                # Try same century first
                second_year_candidate = int(first_century + second_year_short)
                
                # If second year would be before first year, it crossed century boundary
                if second_year_candidate < first_year_int:
                    # Crossed century boundary - second year is in next century
                    if first_century == "19":
                        second_century = "20"
                    else:
                        second_century = "21"
                else:
                    second_century = first_century

                second_year = second_century + second_year_short
                year_str = f"{first_year}-{second_year_short}"
            else:
                second_year = None
                year_str = first_year

            try:
                return Season.objects.get(year=year_str)
            except Season.DoesNotExist:
                return Season.objects.create(
                    year=year_str,
                    first_year=first_year,
                    second_year=second_year
                )

        # Check if the input is a direct year format (e.g., '2024', '2023-24', '1999-00', '2023-2024')
        direct_year_match = re.match(r'^(\d{4})(?:-(\d{2}|\d{4}))?$', season_slug)

        if direct_year_match:
            # Direct year format
            first_year = direct_year_match.group(1)
            second_year_part = direct_year_match.group(2)

            if second_year_part:
                # Handle both 2-digit and 4-digit second year formats
                if len(second_year_part) == 2:
                    # If the second year's first digit is less than the first year's first digit,
                    # then we've crossed into the next century
                    first_year_first_digit = int(first_year[2])
                    second_year_first_digit = int(second_year_part[0])

                    if second_year_first_digit < first_year_first_digit:
                        # We've crossed into the next century
                        century = str(int(first_year[:2]) + 1)
                    else:
                        # Same century
                        century = first_year[:2]

                    second_year = century + second_year_part
                    year_str = f"{first_year}-{second_year_part}"
                else:
                    # 4-digit year format (e.g., '2023-2024')
                    second_year = second_year_part
                    year_str = f"{first_year}-{second_year_part}"
            else:
                # Single year format (e.g., '2024')
                second_year = None
                year_str = first_year
        else:
            # Try to extract year from a full kit slug
            # Find ALL potential year matches to handle cases where club name contains a year
            # (e.g., "fc-rouen-1899-2023-24-home-kit" should use 2023, not 1899)
            all_year_matches = list(re.finditer(r'-(\d{4})(?:-(\d{2}))?-', season_slug + '-'))
            if not all_year_matches:
                raise ValueError(f"Could not find year in slug: {season_slug}")

            # If multiple matches, prefer the last one (most likely to be the actual season year)
            # Also validate that the year is in a reasonable range (1900-2100)
            year_match = None
            for match in reversed(all_year_matches):
                potential_year = int(match.group(1))
                # Prefer years in reasonable range (1900-2100) over very old years from club names
                if 1900 <= potential_year <= 2100:
                    year_match = match
                    break

            # If no match in reasonable range, use the last match
            if not year_match:
                year_match = all_year_matches[-1]

            first_year = year_match.group(1)
            second_year_short = year_match.group(2)

            if second_year_short:
                # If the second year's first digit is less than the first year's first digit,
                # then we've crossed into the next century
                first_year_first_digit = int(first_year[2])
                second_year_first_digit = int(second_year_short[0])

                if second_year_first_digit < first_year_first_digit:
                    # We've crossed into the next century
                    century = str(int(first_year[:2]) + 1)
                else:
                    # Same century
                    century = first_year[:2]

                second_year = century + second_year_short
                year_str = f"{first_year}-{second_year_short}"
            else:
                second_year = None
                year_str = first_year

        # Validate before creating
        try:
            first_year_int = int(first_year)
        except ValueError:
            raise InvalidSeasonError(
                season_slug,
                f"first_year '{first_year}' is not a valid integer"
            )

        # Validate year range for first_year
        if first_year_int < 1800 or first_year_int > 2100:
            raise InvalidSeasonError(
                season_slug,
                f"first_year '{first_year}' is out of valid range (1800-2100)"
            )

        if second_year:
            try:
                second_year_int = int(second_year)
            except ValueError:
                raise InvalidSeasonError(
                    season_slug,
                    f"second_year '{second_year}' is not a valid integer"
                )

            # Validate year range for second_year
            if second_year_int < 1800 or second_year_int > 2100:
                raise InvalidSeasonError(
                    season_slug,
                    f"second_year '{second_year}' is out of valid range (1800-2100)"
                )

            # Validate that second_year is not before first_year
            if second_year_int < first_year_int:
                raise InvalidSeasonError(
                    season_slug,
                    f"second_year '{second_year}' ({second_year_int}) cannot be before first_year '{first_year}' ({first_year_int})"
                )

            # Validate year span
            # For modern seasons (after 1960), max span is 2 years
            # For older seasons (before 1960), allow larger spans (up to 20 years)
            # This handles cases like "1937-49" or "1956-59" which were common in older football
            year_span = second_year_int - first_year_int
            max_span = 20 if first_year_int < 1960 else 2
            
            if year_span > max_span:
                raise InvalidSeasonError(
                    season_slug,
                    f"Year span is {year_span} years (max allowed: {max_span}). first_year: {first_year}, second_year: {second_year}"
                )

        # Try to get existing season first
        try:
            return Season.objects.get(year=year_str)
        except Season.DoesNotExist:
            return Season.objects.create(
                year=year_str,
                first_year=first_year,
                second_year=second_year
            )

    except Exception as e:
        raise InvalidSeasonError(season_slug, f"Error processing season from slug '{season_slug}': {str(e)}") from e


def get_season_e(season_slug: str) -> Season:
    """
    Extended version of get_season that handles additional formats like '2023-2024'.
    Normalizes formats before passing to get_season.
    """
    import re

    # Check if it's in the format '2023-2024' (4-digit year - 4-digit year)
    match = re.match(r'^(\d{4})-(\d{4})$', season_slug)
    if match:
        first_year = match.group(1)
        second_year = match.group(2)

        # Create or get the season
        try:
            return Season.objects.get(year=season_slug)
        except Season.DoesNotExist:
            return Season.objects.create(
                year=season_slug,
                first_year=first_year,
                second_year=second_year
            )

    # For other formats, use the standard get_season function
    return get_season(season_slug)


def scrape_kit(slug: str, kit_id: str | None = None, use_proxy: bool = False) -> Kit | None:
    """
    Scrapes a kit from footballkitarchive.com using its slug and optional kit_id.

    Args:
        slug (str): The kit's base slug from the URL
        kit_id (str, optional): The kit's ID for new format URLs. Defaults to None.
        use_proxy (bool, optional): Whether to use a proxy for the request. Defaults to False.

    Returns:
        Optional[Kit]: The created/updated Kit object, or None if scraping failed

    Raises:
        requests.exceptions.RequestException: For network-related errors
        ValueError: For invalid data in the response
    """
    max_retries = MAX_RETRIES
    retry_count = 0

    while retry_count < max_retries:
        try:
            logger.debug(f"Attempting to scrape kit: {slug} (attempt {retry_count + 1}/{max_retries})")
            logger.debug(f"Using proxy: {use_proxy}")

            url = build_kit_url(slug, kit_id)
            logger.debug(f"Making request to {url}")
            response = http_get(url, use_proxy=use_proxy)

            logger.debug(f"Response status code: {response.status_code}")

            # Handle HTTP errors
            if response.status_code == HTTP_STATUS_FORBIDDEN:
                if retry_count == max_retries - 1:
                    raise RateLimitExceededError("Rate limit exceeded while scraping kit")
                logger.warning("Received 403 status code. Retrying with a new proxy.")
                use_proxy = True
                retry_count += 1
                time.sleep(RETRY_DELAY)
                continue
            elif response.status_code == 404:
                logger.warning(f"Received 404 status code for {slug}. This could be network issue or page moved.")
                # Don't raise for 404, we'll check the content below
            else:
                response.raise_for_status()

            # Parse HTML
            logger.debug("Parsing HTML response")
            soup = BeautifulSoup(response.text, 'html.parser')

            # Check for actual page not found messages (not network 404s)
            # Look for specific "The requested page could not be found" message
            page_not_found_text = soup.find(string=lambda text: text and "The requested page could not be found" in text)
            if page_not_found_text:
                logger.warning(f"Page moved: Kit {slug} - 'The requested page could not be found'")
                raise KitNotFoundError(slug, f"Kit not found: {slug}")

            # Check for 404 Not Found in h1 tag (actual page not found)
            if soup.find("h1", string="404 Not Found"):
                logger.warning(f"404 Not Found: Kit {slug} does not exist")
                raise KitNotFoundError(slug, f"Kit not found: {slug}")

            # If we got a 404 status but the page content looks normal, it might be a network issue
            if response.status_code == 404:
                # Check if we can find the fact table - if yes, it's probably a network issue
                try:
                    extract_fact_table(soup)
                    logger.warning(f"Got 404 status but found fact table for {slug}. Likely network issue, retrying...")
                    retry_count += 1
                    if retry_count < max_retries:
                        time.sleep(RETRY_DELAY)
                        continue
                    else:
                        logger.error(f"Max retries reached for {slug} with 404 status")
                        return None
                except ValueError:
                    # No fact table found, try the new URL format with ID
                    logger.warning(f"404 status and no fact table found for {slug}. Trying new URL format...")

                    # Try to extract ID from slug and construct new URL
                    base_slug, extracted_kit_id = _try_new_url_format(slug)
                    if base_slug and extracted_kit_id:
                        logger.debug(f"Retrying with new URL format: {base_slug}/{extracted_kit_id}/")
                        # Update the slug and kit_id and retry
                        slug = base_slug
                        kit_id = extracted_kit_id
                        retry_count += 1
                        if retry_count < max_retries:
                            time.sleep(RETRY_DELAY)
                            continue
                        else:
                            logger.error(f"Max retries reached for {slug}")
                            return None
                    else:
                        # No new format available, probably actually moved
                        logger.warning(f"No new URL format available for {slug}. Page likely moved.")
                        raise KitNotFoundError(slug, f"Kit not found: {slug}") from None

            # Parse the page using our helper
            try:
                data = parse_kit_page(soup)
            except ValueError as exc:
                logger.error(f"Error parsing kit page: {exc}")
                raise

            # Use service layer to process kit data
            kit = ScrapingService.process_kit_data(data, slug, kit_id, use_proxy)
            return kit

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error scraping {slug}: {str(e)}")
            retry_count += 1
            if retry_count == max_retries:
                logger.error(f"Max retries ({max_retries}) reached. Giving up.")
                return None
            logger.warning(f"Retrying in 2 seconds... (attempt {retry_count + 1}/{max_retries})")
            time.sleep(2)

        except Exception as e:
            logger.error(f"Unexpected error scraping {slug}: {str(e)}")
            return None










def _try_new_url_format(slug: str) -> tuple[str | None, str | None]:
    """
    Tries to convert old URL format to new format with ID.

    Old format: granada-cf-2025-26-third-kit402174
    New format: (base_slug, kit_id) = (granada-cf-2025-26-third-kit, 402174)

    Args:
        slug (str): The old slug format

    Returns:
        tuple[Optional[str], Optional[str]]: (base_slug, kit_id) if conversion is possible, (None, None) otherwise
    """
    import re

    # Check if slug ends with digits (ID)
    match = re.match(r'^(.+?)(\d+)$', slug)
    if match:
        base_slug = match.group(1)
        kit_id = match.group(2)

        print(Fore.CYAN + f"[DEBUG] Converting {slug} -> base: {base_slug}, id: {kit_id}")
        return base_slug, kit_id

    return None, None


def scrape_competition(slug: str, use_proxy: bool = False) -> Competition | None:
    """
    Scrapes a competition from footballkitarchive.com using its slug.

    Args:
        slug (str): The competition's slug from the URL
        use_proxy (bool, optional): Whether to use a proxy for the request. Defaults to False.

    Returns:
        Optional[Competition]: The created/updated Competition object, or None if scraping failed

    Raises:
        requests.exceptions.RequestException: For network-related errors
        ValueError: For invalid data in the response
    """
    max_retries = MAX_RETRIES
    retry_count = 0

    while retry_count < max_retries:
        try:
            response = http_get(f"{BASE_URL}/{slug}", use_proxy=use_proxy)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Get competition name
            title = soup.find("span", class_="main-title")
            if not title:
                raise ValueError("Competition title not found")

            name = title.text.strip()

            # Create or update competition
            competition, created = Competition.objects.update_or_create(
                slug=slug.replace("/", ""),
                defaults={'name': name}
            )

            if created:
                print(Fore.GREEN + f"Created new competition: {competition}")
            else:
                print(Fore.CYAN + f"Updated competition: {competition}")

            return competition

        except requests.exceptions.RequestException as e:
            print(Fore.RED + f"Network error scraping competition {slug}: {str(e)}")
            retry_count += 1
            if retry_count == max_retries:
                return None
            time.sleep(2)

        except Exception as e:
            print(Fore.RED + f"Error scraping competition {slug}: {str(e)}")
            return None


def scrape_club_details(slug: str, use_proxy: bool = False) -> Club | None:
    """
    Scrapes club details from footballkitarchive.com using its slug.

    Args:
        slug (str): The club's slug from the URL
        use_proxy (bool, optional): Whether to use a proxy for the request. Defaults to False.

    Returns:
        Optional[Club]: The created/updated Club object, or None if scraping failed

    Raises:
        requests.exceptions.RequestException: For network-related errors
        ValueError: For invalid data in the response
    """
    max_retries = MAX_RETRIES
    retry_count = 0

    while retry_count < max_retries:
        print(Fore.MAGENTA + f"Scraping {slug}" + (" with proxy" if use_proxy else ""))

        try:
            # Make request
            response = http_get(f"{BASE_URL}/{slug}", use_proxy=use_proxy)

            # Handle HTTP errors
            if response.status_code == 403:
                raise RateLimitExceededError("Rate limit exceeded while scraping club")
            elif response.status_code == 404:
                raise ClubNotFoundError(slug, f"Club not found: {slug}")
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Get club name
            title_elem = soup.find("span", class_="main-title")
            if not title_elem:
                raise ValueError("Club title not found")

            name = title_elem.text.replace("Kit History", "").strip()

            # Get club logo
            main_header = soup.find("div", class_="main-header")
            if not main_header:
                raise ValueError("Club header not found")

            # Create or update club
            with transaction.atomic():
                club, created = Club.objects.update_or_create(
                    slug=slug,
                    defaults={'name': name}
                )

                try:
                    logo_img = main_header.find("img")
                    if logo_img and "data-src" in logo_img.attrs:
                        logo_path = logo_img['data-src'].lstrip('/')
                        logo_url = f"{BASE_URL.rstrip('/')}/{logo_path}"

                        # Handle dark logo variant
                        if "_l" in logo_url:
                            club.logo_dark = logo_url
                            club.logo = logo_url.replace("_l", "")
                        else:
                            club.logo = logo_url
                    else:
                        raise ValueError("Logo image not found")

                except Exception as e:
                    print(Fore.YELLOW + f'Logo error for {club}: {str(e)}. Using default.')
                    club.logo = DEFAULT_LOGO_URL

                club.save()

            status = "Created" if created else "Updated"
            print(Fore.GREEN + f"{status} club: {club}")
            return club

        except requests.exceptions.RequestException as e:
            print(Fore.RED + f"Network error scraping club {slug}: {str(e)}")
            retry_count += 1
            if retry_count == max_retries:
                return None
            time.sleep(2)

        except Exception as e:
            print(Fore.RED + f"Error scraping club {slug}: {str(e)}")
            return None


def scrape_whole_club(club: Club) -> Club | None:
    """
    Scrapes all kits for a given club from footballkitarchive.com.
    Always uses a proxy to prevent IP bans when making multiple requests.

    Args:
        club (Club): The club to scrape kits for

    Returns:
        Optional[Club]: The club object if successful, None if failed

    Raises:
        requests.exceptions.RequestException: For network-related errors
        ValueError: For invalid data in the response
    """
    max_retries = MAX_RETRIES
    retry_count = 0

    while retry_count < max_retries:
        print(Fore.MAGENTA + f"Scraping all kits for {club.name} with proxy")

        try:
            # Make request
            response = http_get(f"{BASE_URL}/{club.slug}", use_proxy=True)

            # Handle HTTP errors
            if response.status_code == 403:
                raise RateLimitExceededError("Rate limit exceeded while scraping club")
            elif response.status_code == 404:
                raise ClubNotFoundError(club.slug, f"Club not found: {club.slug}")
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            container = soup.find("div", class_="archive-content-container")
            if not container:
                raise ValueError("Archive content container not found")

            seasons_container = container.find_all("div", class_=COLLECTION_CONTAINER_CLASS)
            if not seasons_container:
                print(Fore.YELLOW + f"No seasons found for {club.name}")
                return club

            # Process each season
            with transaction.atomic():
                for season_container in seasons_container:
                    # Get season year from h3
                    season_header = season_container.find("h3")
                    if not season_header:
                        print(Fore.YELLOW + "Season header not found, skipping...")
                        continue

                    season_year = season_header.text.strip()
                    print(Fore.YELLOW + f"Processing season {season_year}")

                    # Get season
                    try:
                        season = get_season_e(season_year)
                    except Exception as e:
                        print(Fore.RED + f"Error getting season {season_year}: {str(e)}")
                        continue

                    # Get brand from section details
                    details = season_container.find("ul", class_=SECTION_DETAILS_CLASS)
                    if not details or not details.find_all("a"):
                        print(Fore.YELLOW + f"No brand found for season {season_year}")
                        continue

                    brand_link = details.find_all("a")[0]
                    brand_slug = brand_link["href"].replace("/", "")

                    # Get brand object
                    brand = _get_or_create_brand(brand_slug)
                    if not brand:
                        print(Fore.YELLOW + f"Could not get/create brand {brand_slug}, skipping season...")
                        continue

                    # Process each kit in the season
                    kits_lite = season_container.find_all("div", class_=KIT_CLASS)
                    if not kits_lite:
                        print(Fore.YELLOW + f"No kits found for season {season_year}")
                        continue

                    for kit_lite in kits_lite:
                        try:
                            kit = _process_kit(kit_lite, club, season, brand)
                            if kit:
                                print(Fore.GREEN + f"Successfully processed kit: {kit.name}")
                        except Exception as e:
                            print(Fore.RED + f"Error processing kit: {str(e)}")
                            continue

                    print(Fore.CYAN + f"Completed season {season_year} for {club.name}")

                print(Fore.GREEN + f"Successfully scraped all kits for {club.name}")
                return club

        except requests.exceptions.RequestException as e:
            print(Fore.RED + f"Network error scraping {club.name}: {str(e)}")
            retry_count += 1
            if retry_count == max_retries:
                return None
            time.sleep(2)

        except Exception as e:
            print(Fore.RED + f"Error scraping {club.name}: {str(e)}")
            return None


def _get_or_create_brand(brand_slug: str) -> Brand | None:
    """Helper function to get or create a brand."""
    try:
        return Brand.objects.get(slug=brand_slug)
    except Brand.DoesNotExist:
        try:
            return scrape_brand(brand_slug, True)
        except Exception as e:
            # Format brand name from slug by removing -kits suffix and formatting
            brand_name = brand_slug
            if brand_name.endswith(BRAND_SLUG_SUFFIX):
                brand_name = brand_name[: -len(BRAND_SLUG_SUFFIX)]  # Remove -kits suffix
            brand_name = brand_name.replace("-", " ").strip().title()

            print(f"Logo error for {brand_name}: {str(e)}. Using default.")
            brand = Brand.objects.create(
                name=brand_name,
                slug=brand_slug,
                logo=DEFAULT_LOGO_URL
            )
            print(f"Created brand: {brand.name}")
            return brand


def _process_kit(kit_element: BeautifulSoup, club: Club, season: Season, brand: Brand) -> Kit | None:
    """Helper function to process a single kit element."""
    try:
        # Extract kit data
        kit_link = kit_element.find("a")
        if not kit_link:
            return None

        # Extract slug and kit_id from href (format: slug/id/ or slug/id)
        href = kit_link["href"]
        slug_parts = href.strip("/").split("/")
        clean_slug = slug_parts[0]
        kit_id = slug_parts[1] if len(slug_parts) > 1 else None

        # Delete existing kit if it exists (for re-scraping)
        existing_kit = Kit.objects.filter(slug=clean_slug).first()
        if existing_kit:
            print(Fore.YELLOW + f"Deleting existing kit {clean_slug} for re-scrape...")
            existing_kit.delete()

        # Get kit type
        type_text = kit_element.find("div", class_=KIT_SEASON_CLASS)
        if not type_text:
            return None
        print(Fore.CYAN + f"[DEBUG] type_text: {type_text.text}")
        if season.year in type_text.text:
            type_name = type_text.text.strip().replace(season.year, "").strip()
        else:
            unformatted_year= f'{season.first_year}-{season.second_year[:2]}'
            type_name = type_text.text.strip().replace(unformatted_year, "").strip()
        type_k, _ = Type_K.objects.get_or_create(name=type_name)

        # Scrape full kit details
        return scrape_kit_lite(clean_slug, brand, season, type_k, club, kit_id=kit_id)

    except Exception as e:
        print(Fore.YELLOW + f"Error processing kit: {str(e)}")
        return None


def scrape_kit_lite(
    slug: str,
    brand: Brand,
    season: Season,
    type_k: Type_K,
    club: Club,
    kit_id: str | None = None,
    use_proxy: bool = True
) -> Kit | None:
    """
    Scrapes a kit with minimal information, used for bulk scraping.

    Args:
        slug (str): The kit's slug from the URL
        brand (Brand): The kit's brand
        season (Season): The kit's season
        type_k (Type_K): The kit's type
        club (Club): The kit's club
        use_proxy (bool, optional): Whether to use a proxy for requests. Defaults to True.

    Returns:
        Optional[Kit]: The created Kit object, or None if scraping failed

    Raises:
        requests.exceptions.RequestException: For network-related errors
        ValueError: For invalid data in the response
    """
    max_retries = MAX_RETRIES
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Make request
            response = http_get(build_kit_url(slug, kit_id), use_proxy=use_proxy)

            # Handle HTTP errors
            if response.status_code == HTTP_STATUS_FORBIDDEN:
                print(Fore.RED + "Received 403 status code. Retrying with a new proxy.")
                use_proxy = True
                retry_count += 1
                time.sleep(RETRY_DELAY)
                continue
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Get fact table
            table = soup.find("table", class_="fact-table")
            if not table:
                raise ValueError("Kit fact table not found")

            table_rows = table.find_all("tr")

            # Get kit name from table
            kit_name_cell = table_rows[0].find_all("td")[1]
            if not kit_name_cell:
                raise ValueError("Kit name not found")

            kit_name = f"{kit_name_cell.text.strip()} {season} {type_k}"

            # Get design (if available)
            design = None
            for row in table_rows:
                header = row.find("td")
                if header and header.text.strip() == "Design":
                    design = row.find_all("td")[1].text.strip()
                    break

            # Get colors (if available)
            colors_data = None
            for row in table_rows:
                header = row.find("td")
                if header and header.text.strip() == "Colors":
                    colors_data = row.find_all("td")[1].text.strip()
                    break

            # Get rating
            rating_span = soup.find("span", id="rating")
            rating_details = soup.find("span", id="rating-details-no")
            if rating_span and rating_span.text.strip() and not rating_details:
                rating = float(rating_span.text.strip())
            else:
                rating = 0.0

            # Get main image
            main_img = soup.find("img", class_="top-image")
            if not main_img or "data-src" not in main_img.attrs:
                raise ValueError("Main image not found")

            main_img_url = main_img["data-src"]

            # Create kit and process competitions atomically
            with transaction.atomic():
                # Create or get kit by slug (slug is unique)
                kit, created = Kit.objects.get_or_create(
                    slug=slug,
                    defaults={
                        'name': kit_name,
                        'team': club,
                        'season': season,
                        'type': type_k,
                        'brand': brand,
                        'rating': rating,
                        'kit_id': kit_id,
                        'main_img_url': main_img_url,
                        'design': design
                    }
                )

                # Update kit if it already existed
                if not created:
                    # Update all fields to ensure we have the latest data
                    kit.name = kit_name
                    kit.team = club
                    kit.season = season
                    kit.type = type_k
                    kit.brand = brand
                    kit.rating = rating
                    kit.main_img_url = main_img_url
                    kit.design = design
                    if kit_id:
                        kit.kit_id = kit_id
                    kit.save()

                # Process competitions (for both new and existing kits)
                competitions_cell = None
                for row in table_rows:
                    header = row.find("td")
                    if header and header.text.strip() == "League":
                        competitions_cell = row.find_all("td")[1]
                        break

                if competitions_cell:
                    competitions_html = str(competitions_cell)
                    from core.services.kits_service import KitsService

                    # Clear existing competitions and re-process
                    kit.competition.clear()
                    KitsService.process_competitions(kit, competitions_html, slug)

                # Process colors if available (for both new and existing kits)
                if colors_data:
                    from core.services.kits_service import KitsService

                    # Clear existing colors and re-process
                    kit.secondary_color.clear()
                    kit.primary_color = None
                    KitsService.process_colors(kit, colors_data)

                if created:
                    print(Fore.GREEN + f"Created new kit: {kit}")
                else:
                    print(Fore.CYAN + f"Updated existing kit: {kit}")

                return kit

        except requests.exceptions.RequestException as e:
            print(Fore.RED + f"Network error scraping kit {slug}: {str(e)}")
            retry_count += 1
            if retry_count == max_retries:
                return None
            time.sleep(2)

        except Exception as e:
            print(Fore.RED + f"Error scraping kit {slug}: {str(e)}")
            return None


def scrape_brand(slug: str, use_proxy: bool = False) -> Brand | None:
    """
    Scrapes brand information from footballkitarchive.com using its slug.

    Args:
        slug (str): The brand's slug from the URL
        use_proxy (bool, optional): Whether to use a proxy for the request. Defaults to False.

    Returns:
        Optional[Brand]: The created/updated Brand object, or None if scraping failed

    Raises:
        requests.exceptions.RequestException: For network-related errors
        ValueError: For invalid data in the response
    """
    max_retries = MAX_RETRIES
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Make request
            response = http_get(f"{BASE_URL}/{slug}", use_proxy=use_proxy)

            # Handle HTTP errors
            if response.status_code == 403:
                raise RateLimitExceededError("Rate limit exceeded while scraping brand")
            elif response.status_code == 404:
                raise ScrapingError(f"Brand not found: {slug}", slug)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Get brand name
            title_elem = soup.find("span", class_="main-title")
            if not title_elem:
                raise ValueError("Brand title not found")

            name = title_elem.text.replace("Football Kit History", "").strip()

            # Get brand logo
            main_header = soup.find("div", class_="main-header")
            if not main_header:
                raise ValueError("Brand header not found")

            # Create or update brand
            with transaction.atomic():
                brand, created = Brand.objects.get_or_create(
                    slug=slug,
                    defaults={'name': name}
                )

                try:
                    logo_img = main_header.find("img")
                    if logo_img and "data-src" in logo_img.attrs:
                        logo_path = logo_img['data-src'].lstrip('/')
                        logo_url = f"{BASE_URL.rstrip('/')}/{logo_path}"

                        # Handle dark logo variant
                        if "_l" in logo_url:
                            brand.logo_dark = logo_url
                            brand.logo = logo_url.replace("_l", "")
                        else:
                            brand.logo = logo_url
                    else:
                        raise ValueError("Logo image not found")

                except Exception as e:
                    print(Fore.YELLOW + f'Logo error for {brand}: {str(e)}. Using default.')
                    brand.logo = f"{BASE_URL}/static/logos/not_found.png"

                brand.save()

            status = "Created" if created else "Updated"
            print(Fore.GREEN + f"{status} brand: {brand}")
            return brand

        except requests.exceptions.RequestException as e:
            print(Fore.RED + f"Network error scraping brand {slug}: {str(e)}")
            retry_count += 1
            if retry_count == max_retries:
                return None
            time.sleep(2)

        except Exception as e:
            print(Fore.RED + f"Error scraping brand {slug}: {str(e)}")
            return None


def scrape_lastest(page: int = 1, use_proxy: bool = False) -> bool:
    """
    Scrapes the latest kits page from footballkitarchive.com.

    Args:
        page (int, optional): Page number to scrape. Defaults to 1.
        use_proxy (bool, optional): Whether to use a proxy for requests. Defaults to False.

    Returns:
        bool: True if page was successfully scraped, False otherwise

    Raises:
        requests.exceptions.RequestException: For network-related errors
        ValueError: For invalid data in the response
    """
    max_retries = MAX_RETRIES
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Make request
            response = http_get(f"{BASE_URL}{LATEST_PAGE_URL}{page}", use_proxy=use_proxy)

            # Handle HTTP errors
            if response.status_code == HTTP_STATUS_FORBIDDEN:
                print(Fore.RED + "Received 403 status code. Retrying with a new proxy.")
                use_proxy = True
                retry_count += 1
                time.sleep(RETRY_DELAY)
                continue
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            kit_container = soup.find("div", class_=KIT_CONTAINER_CLASS)
            if not kit_container:
                raise ValueError("Kit container not found")

            kits = kit_container.find_all("div", class_=KIT_CLASS)
            if not kits:
                print(Fore.YELLOW + f"No kits found on page {page}")
                return True  # Consider empty page as success

            # Process each kit
            processed_count = 0
            for kit in kits:
                kit_link = kit.find("a")
                if not kit_link or "href" not in kit_link.attrs:
                    continue

                slug = kit_link["href"]

                # Split by "/" and extract slug and kit_id
                slug_parts = slug.strip("/").split("/")
                clean_slug = slug_parts[0]
                kit_id = slug_parts[1] if len(slug_parts) > 1 else None


                try:
                    print(Fore.CYAN + f"[DEBUG] Processing kit: {clean_slug}")

                    # Check if kit already exists (slug is already cleaned)
                    existing_kit = Kit.objects.filter(slug=clean_slug).first()
                    if existing_kit:
                        print(Fore.CYAN + f"Kit {clean_slug} already exists.")
                        # Update kit_id if it's missing and we have one
                        if not existing_kit.kit_id and kit_id:
                            print(Fore.YELLOW + f"Updating kit_id for existing kit: {clean_slug} -> {kit_id}")
                            existing_kit.kit_id = kit_id
                            existing_kit.save()
                        continue

                    print(Fore.YELLOW + f"Found new kit: {clean_slug}")
                    if scrape_kit(clean_slug, kit_id=kit_id, use_proxy=use_proxy):
                        processed_count += 1

                    time.sleep(1)  # Delay between kits

                except Exception as e:
                    print(Fore.RED + f"Error processing kit {clean_slug}: {str(e)}")
                    continue

            print(Fore.GREEN + f"Successfully processed {processed_count} new kits from page {page}")
            return True

        except requests.exceptions.RequestException as e:
            print(Fore.RED + f"Network error on page {page}, attempt {retry_count + 1}: {str(e)}")
            retry_count += 1
            if retry_count == max_retries:
                print(Fore.RED + f"Failed to scrape page {page} after {max_retries} attempts")
                return False
            time.sleep(2)

        except Exception as e:
            print(Fore.RED + f"Unexpected error on page {page}: {str(e)}")
            return False


def scrape_latest_pages(
    page_start: int = 1,
    page_end: int = 1,
    use_proxy: bool = False,
    delay: int = 2,
    progress_callback: callable = None,
    reverse_order: bool = False
) -> tuple[int, int]:
    """
    Scrapes a range of latest kit pages from footballkitarchive.com.

    Args:
        page_start (int, optional): First page to scrape. Defaults to 1.
        page_end (int, optional): Last page to scrape. Defaults to 1.
        use_proxy (bool, optional): Whether to use a proxy for requests. Defaults to False.
        delay (int, optional): Delay in seconds between pages. Defaults to 2.
        progress_callback (callable, optional): Callback function to report progress. Defaults to None.
        reverse_order (bool, optional): If True, process pages in reverse order. Defaults to False.

    Returns:
        tuple[int, int]: Count of (successful pages, failed pages)
    """
    if page_start > page_end and not reverse_order:
        raise ValueError("page_start cannot be greater than page_end unless reverse_order=True")

    success_count = 0
    failure_count = 0

    # Determine page range and direction
    if reverse_order:
        page_range = range(page_start, page_end - 1, -1)
        print(Fore.CYAN + f"Starting backward scrape of pages {page_start} down to {page_end}")
    else:
        page_range = range(page_start, page_end + 1)
        print(Fore.CYAN + f"Starting forward scrape of pages {page_start} to {page_end}")

    for page in page_range:
        if progress_callback:
            progress_callback(page, page_start, page_end)
        try:
            print(Fore.CYAN + f"\nProcessing page {page} of {page_end}")

            if scrape_lastest(page, use_proxy):
                success_count += 1
                print(Fore.GREEN + f"Successfully scraped page {page}")
            else:
                failure_count += 1
                print(Fore.RED + f"Failed to scrape page {page}")

            # Add delay between pages (except for the last page)
            if (reverse_order and page > page_end) or (not reverse_order and page < page_end):
                print(Fore.CYAN + f"Waiting {delay} seconds before next page...")
                time.sleep(delay)

        except Exception as e:
            failure_count += 1
            print(Fore.RED + f"Error processing page {page}: {str(e)}")
            continue

    # Print summary
    print(Fore.CYAN + "\nScraping completed!")
    print(f"Pages processed successfully: {success_count}")
    print(f"Pages failed: {failure_count}")

    return success_count, failure_count


