# Standard library imports
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

# Third-party imports
import pytz
import requests
from bs4 import BeautifulSoup
from colorama import Fore
from dateutil import parser

# Django imports
from django.db import connection, transaction
from django.utils.text import slugify

# Local imports
from .models import (
    Brand,
    Club,
    Competition,
    Kit,
    Season,
    Type_K
)
from fkapi.proxy import get_proxy

BASE_URL = "https://www.footballkitarchive.com"


@contextmanager
def db_connection():
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
        return Season.objects.get(first_year='2024')
    except Season.DoesNotExist:
        raise Season.DoesNotExist("The 2024 season was not found")


def get_season(season_years: str) -> Season:
    """
    Retrieves or creates a Season object from a string of years.
    
    Args:
        season_years (str): String with the year or range of years (e.g., "2024" or "2023-24")
    
    Returns:
        Season: Season object corresponding to the year or range of years
    """
    if "-" not in season_years:
        season, _ = Season.objects.get_or_create(
            year=season_years,
            defaults={'first_year': season_years}
        )
        return season

    first_year, second_year = season_years.split("-")
    
    # Convert 2-digit years to 4-digit years
    if len(first_year) == 2:
        first_year = "20" + first_year
    
    if len(second_year) == 2:
        first_year_int = int(first_year)
        second_year_int = int(second_year)
        
        if first_year.startswith("19"):
            # Si el primer año es 19XX
            if second_year_int < int(first_year[-2:]):
                # Si el segundo año es menor, asumimos que es del siguiente siglo
                second_year = "20" + second_year
            else:
                second_year = "19" + second_year
        else:
            # Si el primer año es 20XX, el segundo también lo será
            second_year = "20" + second_year

    season_year = f"{first_year}-{second_year[-2:]}"
    
    try:
        return Season.objects.get(year=season_year)
    except Season.DoesNotExist:
        return Season.objects.create(
            year=season_year,
            first_year=first_year,
            second_year=second_year
        )


def get_season_e(season_years: str) -> Season:
    """
    Extended version of get_season that handles full years in the second year.
    
    Args:
        season_years (str): String with the year or range of years (e.g., "2024" or "2023-2024")
    
    Returns:
        Season: Season object corresponding to the year or range of years
    """
    if "-" not in season_years:
        season, _ = Season.objects.get_or_create(
            year=season_years,
            defaults={'first_year': season_years}
        )
        return season

    first_year, second_year = season_years.split("-")
    
    # Convert 2-digit years to 4-digit years
    if len(second_year) == 2:
        first_year_int = int(first_year)
        second_year_int = int(second_year)
        
        if first_year.startswith("19"):
            # Si el primer año es 19XX y el segundo es 00-99
            if second_year_int < int(first_year[-2:]):
                # Si el segundo año es menor, asumimos que es del siguiente siglo
                second_year = "20" + second_year
            else:
                second_year = "19" + second_year
        elif first_year.startswith("20"):
            # Si el primer año es 20XX, el segundo año también será 20XX
            second_year = "20" + second_year
        else:
            # Para otros casos (muy antiguos), asumimos el mismo siglo que el primer año
            second_year = first_year[:2] + second_year

    season, _ = Season.objects.get_or_create(
        year=season_years,
        defaults={
            'first_year': first_year,
            'second_year': second_year
        }
    )
    return season


def scrape_kit(slug: str, use_proxy: bool = False) -> Optional[Kit]:
    """
    Scrapes a kit from footballkitarchive.com using its slug.

    Args:
        slug (str): The kit's slug from the URL
        use_proxy (bool, optional): Whether to use a proxy for the request. Defaults to False.

    Returns:
        Optional[Kit]: The created/updated Kit object, or None if scraping failed

    Raises:
        requests.exceptions.RequestException: For network-related errors
        ValueError: For invalid data in the response
    """
    BASE_URL = "https://www.footballkitarchive.com"
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            print(Fore.CYAN + f"[DEBUG] Attempting to scrape kit: {slug} (attempt {retry_count + 1}/{max_retries})")
            print(Fore.CYAN + f"[DEBUG] Using proxy: {use_proxy}")
            
            # Make request with or without proxy
            proxy = get_proxy() if use_proxy else None
            print(Fore.CYAN + f"[DEBUG] Making request to {BASE_URL}/{slug}")
            response = requests.get(
                f"{BASE_URL}/{slug}",
                timeout=15,
                proxies=proxy
            )
            
            print(Fore.CYAN + f"[DEBUG] Response status code: {response.status_code}")
            
            # Handle HTTP errors
            if response.status_code == 403:
                print(Fore.RED + "[DEBUG] Received 403 status code. Retrying with a new proxy.")
                use_proxy = True
                retry_count += 1
                time.sleep(2)
                continue
            response.raise_for_status()

            # Parse HTML
            print(Fore.CYAN + "[DEBUG] Parsing HTML response")
            soup = BeautifulSoup(response.text, 'html.parser')
            if soup.find("h1", text="404 Not Found"):
                print(Fore.YELLOW + f"[DEBUG] 404 Not Found: Kit {slug} does not exist")
                return None

            # Extract data from table
            print(Fore.CYAN + "[DEBUG] Looking for fact table...")
            table = soup.find("table", class_="fact-table")
            if not table:
                print(Fore.RED + "[DEBUG] No fact table found in HTML")
                print(Fore.RED + "[DEBUG] First 500 chars of HTML content:")
                print(soup.prettify()[:500])
                raise ValueError("Kit fact table not found in HTML")
            
            print(Fore.CYAN + "[DEBUG] Found fact table, looking for rows...")
            table_rows = table.find_all("tr")
            if not table_rows:
                print(Fore.RED + "[DEBUG] No rows found in fact table")
                print(Fore.RED + "[DEBUG] Table content:")
                print(table.prettify())
                raise ValueError("No rows found in fact table")
            
            # Get team information
            print(Fore.CYAN + "[DEBUG] Looking for team data...")
            team_data = table_rows[0].find_all("td")
            if not team_data or len(team_data) < 2:
                print(Fore.RED + "[DEBUG] Team data not found or incomplete")
                print(Fore.RED + "[DEBUG] First row content:")
                print(table_rows[0].prettify())
                raise ValueError("Team data not found or incomplete")

            team_name = team_data[1].text.strip()
            team_link = team_data[1].find("a")
            if not team_link:
                print(Fore.RED + "[DEBUG] Team link not found")
                print(Fore.RED + "[DEBUG] Team data content:")
                print(team_data[1].prettify())
                raise ValueError("Team link not found")

            team_slug = team_link["href"].replace("/", "")
            
            print(Fore.CYAN + f"[DEBUG] Processing kit for team: {team_name} (slug: {team_slug})")

            # Get or create team
            try:
                print(Fore.CYAN + f"[DEBUG] Attempting to get team from database: {team_slug}")
                team = Club.objects.get(slug=team_slug)
                print(Fore.CYAN + f"[DEBUG] Found existing team: {team}")
            except Club.DoesNotExist:
                print(Fore.YELLOW + f"[DEBUG] Team {team_slug} not found, attempting to scrape it")
                team = scrape_club_details(team_slug, use_proxy)
                if not team:
                    print(Fore.RED + f'[DEBUG] Failed to scrape team {team_slug}')
                    return None

            # Get season
            print(Fore.CYAN + "[DEBUG] Getting season information...")
            season_years = table_rows[1].find_all("td")[1].text.strip()
            print(Fore.CYAN + f"[DEBUG] Season years from HTML: {season_years}")
            season = get_season(season_years)
            print(Fore.CYAN + f"[DEBUG] Created/retrieved season: {season}")

            # Get kit type
            print(Fore.CYAN + "[DEBUG] Getting kit type...")
            type_k_str = table_rows[2].find_all("td")[1].text.strip()
            type_k, _ = Type_K.objects.get_or_create(name=type_k_str)
            print(Fore.CYAN + f"[DEBUG] Kit type: {type_k}")

            # Get brand
            print(Fore.CYAN + "[DEBUG] Getting brand information...")
            brand_data = table_rows[3].find_all("td")[1]
            brand_slug = slugify(brand_data.find("a")["href"])
            try:
                brand = Brand.objects.get(slug=brand_slug)
                print(Fore.CYAN + f"[DEBUG] Found existing brand: {brand}")
            except Brand.DoesNotExist:
                print(Fore.YELLOW + f"[DEBUG] Creating new brand: {brand_slug}")
                brand, _ = Brand.objects.get_or_create(
                    name=brand_data.text.strip(),
                    slug=brand_slug
                )

            # Get rating
            print(Fore.CYAN + "[DEBUG] Getting rating...")
            rating_span = soup.find("span", id="rating")
            rating_details = soup.find("span", id="rating-details-no")
            if rating_span and rating_span.text.strip() and not rating_details:
                rating = float(rating_span.text.strip())
            else:
                rating = 0.0
            print(Fore.CYAN + f"[DEBUG] Found rating: {rating}")

            # Get main image
            print(Fore.CYAN + "[DEBUG] Getting main image...")
            main_img = soup.find("img", class_="top-image")
            if not main_img:
                print(Fore.RED + "[DEBUG] Main image element not found")
                print(Fore.RED + "[DEBUG] HTML content around where image should be:")
                raise ValueError("Main image not found")
            
            main_img_url = main_img.get("data-src")
            if not main_img_url:
                print(Fore.RED + "[DEBUG] Main image URL not found")
                print(Fore.RED + "[DEBUG] Image element content:")
                print(main_img.prettify())
                raise ValueError("Main image URL not found")
            
            print(Fore.CYAN + f"[DEBUG] Found main image URL: {main_img_url}")

            # Create or update kit
            print(Fore.CYAN + "[DEBUG] Creating/updating kit in database...")
            with transaction.atomic():
                kit_name = f"{team_name} {season} {type_k}"
                print(Fore.CYAN + f"[DEBUG] Kit name: {kit_name}")
                kit, created = Kit.objects.update_or_create(
                    slug=slug.replace("/", ""),
                    defaults={
                        'name': kit_name,
                        'team': team,
                        'season': season,
                        'type': type_k,
                        'brand': brand,
                        'rating': rating,
                        'main_img_url': main_img_url
                    }
                )

                # Process competitions
                print(Fore.CYAN + "[DEBUG] Processing competitions...")
                competitions_str = table_rows[4].find_all("td")[1].text.strip()
                print(Fore.CYAN + f"[DEBUG] Competitions string: {competitions_str.strip()}")
                _process_competitions(kit, competitions_str, slug)

                if not created:
                    print(Fore.GREEN + f"[DEBUG] Updated existing kit: {kit}")
                else:
                    print(Fore.GREEN + f"[DEBUG] Created new kit: {kit}")

                return kit

        except requests.exceptions.RequestException as e:
            print(Fore.RED + f"[DEBUG] Network error scraping {slug}: {str(e)}")
            retry_count += 1
            if retry_count == max_retries:
                print(Fore.RED + f"[DEBUG] Max retries ({max_retries}) reached. Giving up.")
                _log_missing_item('kits_to_fix.txt', f"{slug} - Network error: {str(e)}")
                return None
            print(Fore.YELLOW + f"[DEBUG] Retrying in 2 seconds... (attempt {retry_count + 1}/{max_retries})")
            time.sleep(2)

        except Exception as e:
            print(Fore.RED + f"[DEBUG] Unexpected error scraping {slug}: {str(e)}")
            print(Fore.RED + "[DEBUG] Stack trace:")
            import traceback
            print(traceback.format_exc())
            _log_missing_item('kits_to_fix.txt', f"{slug} - {str(e)}")
            return None


def _process_competitions(kit: Kit, competitions_str: str, slug: str) -> None:
    """Helper function to process and add competitions to a kit."""
    try:
        if "·" in competitions_str:
            competitions = competitions_str.split("·")
            for comp_name in competitions:
                comp_name = comp_name.strip()
                competition, _ = Competition.objects.get_or_create(
                    name=comp_name,
                    slug=slugify(f"{comp_name}-kits")
                )
                kit.competition.add(competition)
        else:
            competition, _ = Competition.objects.get_or_create(
                name=competitions_str.strip(),
                slug=slugify(f"{competitions_str.strip()}-kits")
            )
            kit.competition.add(competition)
        
        kit.save()
    except Exception as e:
        print(Fore.RED + f'Error processing competitions for {kit}: {str(e)}')
        _log_missing_item('kits_to_fix.txt', f"{slug} - Competition error: {str(e)} - {competitions_str}")


def _log_missing_item(filename: str, content: str) -> None:
    """Helper function to log missing or error items to a file."""
    with open(filename, 'a', encoding='utf-8') as file:
        file.write(f"{content}\n")


def scrape_competition(slug: str, use_proxy: bool = False) -> Optional[Competition]:
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
    BASE_URL = "https://www.footballkitarchive.com"
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            response = requests.get(
                f"{BASE_URL}/{slug}",
                timeout=15,
                proxies=get_proxy() if use_proxy else None
            )
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
                _log_missing_item('competitions_to_fix.txt', f"{slug} - Network error: {str(e)}")
                return None
            time.sleep(2)

        except Exception as e:
            print(Fore.RED + f"Error scraping competition {slug}: {str(e)}")
            _log_missing_item('competitions_to_fix.txt', f"{slug} - {str(e)}")
            return None


def scrape_club_details(slug: str, use_proxy: bool = False) -> Optional[Club]:
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
    BASE_URL = "https://www.footballkitarchive.com"
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        proxy = get_proxy() if use_proxy else None
        print(Fore.MAGENTA + f"Scraping {slug}" + (f" with proxy {proxy}" if proxy else ""))

        try:
            # Make request
            response = requests.get(
                f"{BASE_URL}/{slug}",
                timeout=15,
                proxies=proxy
            )
            
            # Handle HTTP errors
            if response.status_code in [403, 404]:
                raise requests.exceptions.HTTPError(
                    f"Received {response.status_code} status code")
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
                    club.logo = f"{BASE_URL}/static/logos/not_found.png"
                
                club.save()

            status = "Created" if created else "Updated"
            print(Fore.GREEN + f"{status} club: {club}")
            return club

        except requests.exceptions.RequestException as e:
            print(Fore.RED + f"Network error scraping club {slug}: {str(e)}")
            retry_count += 1
            if retry_count == max_retries:
                _log_missing_item('clubs_to_fix.txt', f"{slug} - Network error: {str(e)}")
                return None
            time.sleep(2)

        except Exception as e:
            print(Fore.RED + f"Error scraping club {slug}: {str(e)}")
            _log_missing_item('clubs_to_fix.txt', f"{slug} - {str(e)}")
            return None


def scrape_whole_club(club: Club) -> Optional[Club]:
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
    BASE_URL = "https://www.footballkitarchive.com"
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        proxy = get_proxy()
        print(Fore.MAGENTA + f"Scraping all kits for {club.name} with proxy {proxy}")
        
        try:
            # Make request
            response = requests.get(
                f"{BASE_URL}/{club.slug}",
                timeout=15,
                proxies=proxy
            )
            
            # Handle HTTP errors
            if response.status_code in [403, 404]:
                raise requests.exceptions.HTTPError(
                    f"Received {response.status_code} status code")
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            container = soup.find("div", class_="archive-content-container")
            if not container:
                raise ValueError("Archive content container not found")
            
            seasons_container = container.find_all("div", class_="collection-container")
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
                    details = season_container.find("ul", class_="section-details")
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
                    kits_lite = season_container.find_all("div", class_="kit")
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
                _log_missing_item('clubs_to_fix.txt', f"{club.slug} - Network error: {str(e)}")
                return None
            time.sleep(2)
            
        except Exception as e:
            print(Fore.RED + f"Error scraping {club.name}: {str(e)}")
            _log_missing_item('clubs_to_fix.txt', f"{club.slug} - {str(e)}")
            return None


def _get_or_create_brand(brand_slug: str) -> Optional[Brand]:
    """Helper function to get or create a brand."""
    try:
        return Brand.objects.get(slug=brand_slug)
    except Brand.DoesNotExist:
        try:
            return scrape_brand(brand_slug, True)
        except Exception as e:
            # Format brand name from slug by removing -kits suffix and formatting
            brand_name = brand_slug
            if brand_name.endswith("-kits"):
                brand_name = brand_name[:-5]  # Remove -kits suffix
            brand_name = brand_name.replace("-", " ").strip().title()
            
            print(f"Logo error for {brand_name}: {str(e)}. Using default.")
            brand = Brand.objects.create(
                name=brand_name,
                slug=brand_slug,
                logo=f"{BASE_URL}/static/logos/not_found.png"
            )
            print(f"Created brand: {brand.name}")
            return brand


def _process_kit(kit_element: BeautifulSoup, club: Club, season: Season, brand: Brand) -> Optional[Kit]:
    """Helper function to process a single kit element."""
    try:
        # Extract kit data
        kit_link = kit_element.find("a")
        if not kit_link:
            return None
            
        slug = kit_link["href"].replace("/", "")
        
        # Skip if kit already exists
        if Kit.objects.filter(slug=slug).exists():
            return None
            
        # Get kit type
        type_text = kit_element.find("div", class_="kit-season")
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
        return scrape_kit_lite(slug, brand, season, type_k, club)
        
    except Exception as e:
        print(Fore.YELLOW + f"Error processing kit {slug}: {str(e)}")
        return None


def scrape_kit_lite(
    slug: str,
    brand: Brand,
    season: Season,
    type_k: Type_K,
    club: Club,
    use_proxy: bool = True
) -> Optional[Kit]:
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
    BASE_URL = "https://www.footballkitarchive.com"
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Make request
            response = requests.get(
                f"{BASE_URL}/{slug}",
                timeout=15,
                proxies=get_proxy() if use_proxy else None
            )
            
            # Handle HTTP errors
            if response.status_code == 403:
                print(Fore.RED + f"Received 403 status code. Retrying with a new proxy.")
                use_proxy = True
                retry_count += 1
                time.sleep(2)
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
                # Create or get kit
                kit, created = Kit.objects.get_or_create(
                    name=kit_name,
                    defaults={
                        'team': club,
                        'season': season,
                        'type': type_k,
                        'brand': brand,
                        'rating': rating,
                        'slug': slug.replace("/", ""),
                        'main_img_url': main_img_url
                    }
                )

                if created:
                    # Process competitions only for new kits
                    competitions_cell = table_rows[4].find_all("td")[1]
                    if competitions_cell:
                        competitions_str = competitions_cell.text.strip()
                        _process_competitions(kit, competitions_str, slug)
                    
                    print(Fore.GREEN + f"Created new kit: {kit}")
                else:
                    print(Fore.CYAN + f"Kit already exists: {kit}")

                return kit

        except requests.exceptions.RequestException as e:
            print(Fore.RED + f"Network error scraping kit {slug}: {str(e)}")
            retry_count += 1
            if retry_count == max_retries:
                _log_missing_item('kits_to_fix.txt', f"{slug} - Network error: {str(e)}")
                return None
            time.sleep(2)

        except Exception as e:
            print(Fore.RED + f"Error scraping kit {slug}: {str(e)}")
            _log_missing_item('kits_to_fix.txt', f"{slug} - {str(e)}")
            return None


def scrape_brand(slug: str, use_proxy: bool = False) -> Optional[Brand]:
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
    BASE_URL = "https://www.footballkitarchive.com"
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Make request
            response = requests.get(
                f"{BASE_URL}/{slug}",
                timeout=15,
                proxies=get_proxy() if use_proxy else None
            )
            
            # Handle HTTP errors
            if response.status_code in [403, 404]:
                print(Fore.RED + f"Network error scraping brand {slug}: Received {response.status_code} status code")
                return None
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
                _log_missing_item('brands_to_fix.txt', f"{slug} - Network error: {str(e)}")
                return None
            time.sleep(2)

        except Exception as e:
            print(Fore.RED + f"Error scraping brand {slug}: {str(e)}")
            _log_missing_item('brands_to_fix.txt', f"{slug} - {str(e)}")
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
    BASE_URL = "https://www.footballkitarchive.com"
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Make request
            response = requests.get(
                f"{BASE_URL}/latest/?p={page}",
                timeout=15,
                proxies=get_proxy() if use_proxy else None
            )
            
            # Handle HTTP errors
            if response.status_code == 403:
                print(Fore.RED + f"Received 403 status code. Retrying with a new proxy.")
                use_proxy = True
                retry_count += 1
                time.sleep(2)
                continue
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            kit_container = soup.find("div", class_="kit-container")
            if not kit_container:
                raise ValueError("Kit container not found")
            
            kits = kit_container.find_all("div", class_="kit")
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
                clean_slug = slug.replace("/", "")
                
                try:
                    if Kit.objects.filter(slug=clean_slug).exists():
                        print(Fore.CYAN + f"Kit {clean_slug} already exists.")
                        continue
                        
                    print(Fore.YELLOW + f"Found new kit: {clean_slug}")
                    if scrape_kit(slug, use_proxy=use_proxy):
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
    delay: int = 2
) -> tuple[int, int]:
    """
    Scrapes a range of latest kit pages from footballkitarchive.com.

    Args:
        page_start (int, optional): First page to scrape. Defaults to 1.
        page_end (int, optional): Last page to scrape. Defaults to 1.
        use_proxy (bool, optional): Whether to use a proxy for requests. Defaults to False.
        delay (int, optional): Delay in seconds between pages. Defaults to 2.

    Returns:
        tuple[int, int]: Count of (successful pages, failed pages)
    """
    if page_start > page_end:
        raise ValueError("page_start cannot be greater than page_end")
        
    success_count = 0
    failure_count = 0
    
    print(Fore.CYAN + f"Starting scrape of pages {page_start} to {page_end}")
    
    for page in range(page_start, page_end + 1):
        try:
            print(Fore.CYAN + f"\nProcessing page {page} of {page_end}")
            
            if scrape_lastest(page, use_proxy):
                success_count += 1
                print(Fore.GREEN + f"Successfully scraped page {page}")
            else:
                failure_count += 1
                print(Fore.RED + f"Failed to scrape page {page}")
            
            if page < page_end:
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
