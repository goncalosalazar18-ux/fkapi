from bs4 import BeautifulSoup
import requests
from .models import Kit, Competition, Season, Brand, Type_K, Club
from datetime import datetime
from django.utils.text import slugify
from dateutil import parser
from fkapi.proxy import get_proxy
import pytz
from colorama import Fore


def get_current_season() -> Season:
    current_season = Season.objects.get(first_year='2024')
    return current_season


def get_season(season_years: str) -> Season:
    if "-" in season_years:
        season_years = season_years.split("-")
        for i in range(2):
            if int(season_years[i]) > 35:
                season_years[i] = int("19"+season_years[i])
            else:
                season_years[i] = int("20"+season_years[i])
        try:
            season = Season.objects.get(
                year=str(season_years[0])+"-"+str(season_years[1])[2:])
        except:
            season, created = Season.objects.get_or_create(
                year=str(season_years[0])+"-"+str(season_years[1])[2:], first_year=season_years[0], second_year=season_years[1])
    else:
        season_years = [int(season_years)]
        # get or create season
        season, created = Season.objects.get_or_create(
            year=str(season_years[0]), first_year=season_years[0])
    return season


def get_season_e(season_years: str) -> Season:
    if "-" in season_years:
        season_years_split = season_years.split("-")
        first_year = season_years_split[0]
        if int(season_years_split[1]) > 35:
            second_year = "19"+season_years_split[1]
        else:
            second_year = "20"+season_years_split[1]
        season, created = Season.objects.get_or_create(
            year=season_years, first_year=first_year, second_year=second_year)
    else:
        # get or create season
        season, created = Season.objects.get_or_create(
            year=season_years, first_year=season_years)
    return season


def scrape_kit(slug: str, use_proxy: bool = False) -> Kit:
    max_retries = 3
    retry_count = 0
    while retry_count < max_retries:
        try:
            if use_proxy:
                response = requests.get(
                    "https://www.footballkitarchive.com/"+slug, timeout=10, proxies=get_proxy())
            else:
                response = requests.get(
                    "https://www.footballkitarchive.com/"+slug, timeout=10)
            if response.status_code == 403:
                print(Fore.RED + f"Received 403 status code. Retrying with a new proxy.")
                use_proxy = True
                retry_count += 1
                continue
            soup = BeautifulSoup(response.text, 'html.parser')
            # get the table

            table = soup.find("table", class_="fact-table")
            table_rows = table.find_all("tr")
            print(table_rows[0].find_all("td")[1].text.strip())

            team_slug = table_rows[0].find_all(
                "td")[1].find_all("a")[0]["href"]
            try:
                team = Club.objects.get(slug=team_slug.replace("/", ""))
            except:
                print(f'Team {team_slug.replace("/", "")} does not exist')
                # write to file
                with open('clubs_to_fix.txt', 'a', encoding='utf-8') as file:
                    file.write(team_slug.replace("/", "") + "\n")
                # skip
                return
            season_years = table_rows[1].find_all("td")[1].text.strip()
            season = get_season(season_years)
            type_k_str = table_rows[2].find_all("td")[1].text.strip()
            type_k, created = Type_K.objects.get_or_create(name=type_k_str)
            try:
                brand = Brand.objects.get(slug=slugify(table_rows[3].find_all("td")[1].find_all("a")[0]["href"]))
            except Brand.DoesNotExist:
                brand, created = Brand.objects.get_or_create(
                    name=table_rows[3].find_all("td")[1].text.strip(),
                    slug=slugify(table_rows[3].find_all("td")[1].find_all("a")[0]["href"]))

            rating = soup.find_all("span", id="rating")[0].text.strip()
            if rating == "":
                rating = 0
            # try:
            #     web_updated_str = soup.find(
            #         "span", class_="kit-details-updated").text.strip()
            #     web_updated_str = web_updated_str.replace("Updated ", "")
            #     cet_timezone = pytz.timezone('CET')
            #     web_updated = parser.parse(
            #         web_updated_str, dayfirst=True, tzinfos=cet_timezone)
            # except:
            #     web_updated = None
            main_img_url = soup.find("img", class_="top-image")["data-src"]
            kit, created = Kit.objects.get_or_create(name=table_rows[0].find_all("td")[1].text.strip() + " " + str(season) + " " + str(type_k), team=team, season=season, type=type_k, brand=brand,
                                                     rating=float(rating), slug=slug.replace("/", ""), main_img_url=main_img_url)

            competitions_str = table_rows[4].find_all("td")[1].text.strip()

            try:
                if "·" in competitions_str:
                    competitions = competitions_str.split("·")
                    for competition in competitions:
                        competition_obj, created = Competition.objects.get_or_create(
                            name=competition.strip(), slug=slugify(competition.strip()+"-kits"))
                        kit.competition.add(competition_obj)
                    kit.save()
                else:
                    competition, created = Competition.objects.get_or_create(
                        name=competitions_str.strip(), slug=slugify(competitions_str.strip()+"-kits"))
                    # Set many-to-many relationship for single object
                    kit.competition.add(competition)
                    kit.save()
            except Exception as e:
                print(
                    f'{kit} had an error with competitions {competitions_str.strip()}: {str(e)}')
                exit()

            return kit
        except Exception as e:
            print(f'Error scraping {slug}: {str(e)}')
            with open('kits_to_fix.txt', 'a', encoding='utf-8') as file:
                file.write(slug+ " -  "+ str(e) + "\n")
            return None


def scrape_competition(slug: str) -> Competition:
    response = requests.get(
        "https://www.footballkitarchive.com"+slug, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    return Competition


def scrape_club_details(slug: str, use_proxy: bool = False) -> Club:
    max_retries = 3
    retry_count = 0
    while retry_count < max_retries:
        proxy = get_proxy()
        print(Fore.MAGENTA + f"Scraping {slug} with proxy {proxy}")
        try:
            if use_proxy:
                response = requests.get(
                    "https://www.footballkitarchive.com/"+slug, timeout=10, proxies=proxy)
            else:
                response = requests.get(
                    "https://www.footballkitarchive.com/"+slug, timeout=10)

            if response.status_code == 404 or response.status_code == 403:
                raise Exception(
                    Fore.RED + f"Received {response.status_code} status code")

            soup = BeautifulSoup(response.text, 'html.parser')
            # find club from slug
            name = soup.find(
                "span", class_="main-title").text.replace("Kit History", "").strip()
            main_header = soup.find("div", class_="main-header")

            club, created = Club.objects.update_or_create(
                slug=slug, defaults={'name': name})

            try:
                logo = "https://www.footballkitarchive.com/" + \
                    main_header.find("img")[
                        "data-src"]
                if "_l " in logo:
                    logo_dark = logo
                    logo = logo.replace("_l", "")
                    club.logo_dark = logo_dark
                club.logo = logo
                club.save()
            except:
                print(Fore.LIGHTCYAN_EX +
                      f'{club} has no logo. Saving default')
                club.logo = "https://www.footballkitarchive.com/static/logos/not_found.png"
                club.save()
            print(Fore.BLUE + f"Scraped {club} with proxy {proxy}")
            return Club
        except Exception as e:
            print(f'Error scraping {slug}: {str(e)}')
            retry_count += 1

    print(f'Max retries exceeded for {slug}')
    with open('clubs_to_fix.txt', 'a', encoding='utf-8') as file:
        file.write(slug + "\n")
    return None


def scrape_whole_club(club: Club) -> Club:
    max_retries = 3
    retry_count = 0
    while retry_count < max_retries:
        proxy = get_proxy()
        print(Fore.MAGENTA + f"Scraping whole {club.name} with proxy {proxy}")
        try:
            response = requests.get(
                "https://www.footballkitarchive.com/"+club.slug, timeout=10, proxies=proxy)
            if response.status_code == 404 or response.status_code == 403:
                raise Exception(
                    Fore.RED + f"Received {response.status_code} status code")

            soup = BeautifulSoup(response.text, 'html.parser')
            container = soup.find("div", class_="archive-content-container")
            seasons_container = container.find_all(
                "div", class_="collection-container")
            for season_container in seasons_container:
                season_year = season_container.find("h3").text.strip()
                print(Fore.YELLOW + f"Scraping Season {season_year}")
                season = get_season_e(season_year)
                details = season_container.find("ul", class_="section-details")
                brand_slug = details.find_all("a")[0]["href"]
                kits_lite = season_container.find_all("div", class_="kit")
                for kit_lite in kits_lite:
                    slug = kit_lite.find("a")["href"].replace("/", "")
                    type_k = kit_lite.find(
                        "div", class_="kit-season").text.strip().replace(season.year, "")
                    try:
                        brand = Brand.objects.get(
                            slug=brand_slug.replace("/", ""))
                    except:
                        try:
                            brand = scrape_brand(brand_slug.replace("/", ""), True)
                        except:
                            brand = Brand.objects.create(name=brand_slug.replace("/", "").replace("-", " ").strip().title(), slug=brand_slug.replace("/", ""))
                    type_k_obj, created = Type_K.objects.get_or_create(
                        name=type_k.strip())
                    # Check if kit exists already in db
                    if not Kit.objects.filter(slug=slug).exists():
                        kit = scrape_kit_lite(
                            slug, brand, season, type_k_obj, club)
                print(Fore.CYAN + f"Scraped {club} {season_year} ")

            print(Fore.BLUE + f"Scraped {club} with proxy {proxy}")
            return Club
        except Exception as e:
            print(f'Error scraping {club.name}: {str(e)}')
            retry_count += 1

    print(f'Max retries exceeded for {club.name}')
    with open('clubs_to_fix.txt', 'a', encoding='utf-8') as file:
        file.write(club.name + "\n")
    return None


def scrape_kit_lite(slug: str, brand: Brand, season: Season, type_k: Type_K, club: Club) -> Kit:
    max_retries = 3
    retry_count = 0
    while retry_count < max_retries:
        try:

            response = requests.get(
                "https://www.footballkitarchive.com/"+slug, timeout=10, proxies=get_proxy())

            if response.status_code == 403:
                print(Fore.RED + f"Received 403 status code. Retrying with a new proxy.")
                use_proxy = True
                retry_count += 1
                continue
            soup = BeautifulSoup(response.text, 'html.parser')

            table = soup.find("table", class_="fact-table")
            table_rows = table.find_all("tr")

            rating = soup.find_all("span", id="rating")[0].text.strip()
            if rating == "":
                rating = 0
            main_img_url = soup.find("img", class_="top-image")["data-src"]
            kit, created = Kit.objects.get_or_create(name=table_rows[0].find_all("td")[1].text.strip() + " " + str(season) + " " + str(type_k), team=club, season=season, type=type_k, brand=brand,
                                                     rating=float(rating), slug=slug.replace("/", ""), main_img_url=main_img_url)

            competitions_str = table_rows[4].find_all("td")[1].text.strip()

            try:
                if "·" in competitions_str:
                    competitions = competitions_str.split("·")
                    for competition in competitions:
                        competition_obj, created = Competition.objects.get_or_create(
                            name=competition.strip(), slug=slugify(competition.strip()+"-kits"))
                        kit.competition.add(competition_obj)
                    kit.save()
                else:
                    competition, created = Competition.objects.get_or_create(
                        name=competitions_str.strip(), slug=slugify(competitions_str.strip()+"-kits"))
                    # Set many-to-many relationship for single object
                    kit.competition.add(competition)
                    kit.save()
            except Exception as e:
                print(
                    f'{kit} had an error with competitions {competitions_str.strip()}: {str(e)}')
                exit()

            return kit
        except Exception as e:
            print(f'Error scraping {slug}: {str(e)}')
            with open('kits_to_fix.txt', 'a', encoding='utf-8') as file:
                file.write(slug + " - " + str(e) + "\n")
            return None


def scrape_brand(slug: str, use_proxy: bool = False) -> Brand:
    try:
        url = "https://www.footballkitarchive.com/"+slug
        print(Fore.MAGENTA + f'Scraping {url}')
        if use_proxy:
            response = requests.get(url, timeout=10, proxies=get_proxy())
        else:
            response = requests.get(url, timeout=10)
        if response.status_code == 404 or response.status_code == 403:

            raise Exception(
                Fore.RED + f"Received {response.status_code} status code")

        soup = BeautifulSoup(response.text, 'html.parser')
        name = soup.find(
            "span", class_="main-title").text.replace("Football Kit History", "").strip()
        main_header = soup.find("div", class_="main-header")

        brand, created = Brand.objects.get_or_create(name=name, slug=slug)

        try:
            logo = "https://www.footballkitarchive.com/" + \
                main_header.find("img")[
                    "data-src"]
            if "_1 " in logo:
                logo_dark = logo
                logo = logo.replace("_1 ", "")
                brand.logo_dark = logo_dark
            brand.logo = logo
            brand.save()
        except:
            print(Fore.LIGHTCYAN_EX + f'{brand} has no logo. Setting default')
            brand.logo = "https://www.footballkitarchive.com/static/logos/not_found.png"
            brand.save()
        return Brand
    except Exception as e:
        print(f'Error scraping {slug}: {str(e)}')
        with open('brands_to_fix.txt', 'a', encoding='utf-8') as file:
            file.write(slug + "\n")
        return None


def scrape_lastest(page: int = 1, use_proxy: bool = False):
    if use_proxy:
        response = requests.get(
            f"https://www.footballkitarchive.com/latest/?p={page}", timeout=10, proxies=get_proxy())
    else:
        response = requests.get(
            f"https://www.footballkitarchive.com/latest/?p={page}", timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    kit_container = soup.find("div", class_="kit-container")
    kits = kit_container.find_all("div", class_="kit")
    for kit in kits:
        slug = kit.find("a")["href"]
        # season = kit.find("div", class_="kit-season").split(" ")[0]
        try:
            existing_kit = Kit.objects.get(slug=slug.replace("/", ""))
            print(f"Kit {existing_kit} already exists in the database.")
        except Kit.DoesNotExist:
            print(f"Scraping new kit found: {slug}")
            scrape_kit(slug)


def scrape_latest_pages(page_start: int = 1, page_end: int = 1, use_proxy: bool = False):
    for page in range(page_start, page_end):
        scrape_lastest(page, use_proxy)
