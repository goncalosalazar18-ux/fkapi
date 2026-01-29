from collections import Counter
from urllib.parse import urlencode

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django_countries import countries

from fkapi.api import get_random_clubs, get_random_kits

from .models import Club, Competition


def assign_countries(request: HttpRequest) -> HttpResponse:
    """
    View to assign countries to competitions.
    Orders competitions by the number of related kits.
    """
    # Get all competitions ordered by kit count (descending)
    competitions = (
        Competition.objects.filter(country__isnull=True).annotate(kit_count=Count("kit")).order_by("-kit_count")
    )

    # Pagination
    paginator = Paginator(competitions, 20)  # Show 20 competitions per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Get list of countries
    country_list = list(countries)

    # Process form on POST request
    if request.method == "POST":
        competition_id = request.POST.get("competition_id")
        country_code = request.POST.get("country")

        if competition_id and country_code:
            competition = Competition.objects.get(id=competition_id)
            competition.country = country_code
            competition.save()
            messages.success(request, f"Country assigned successfully to {competition.name}")
            return redirect("assign_countries")

    return render(
        request,
        "core/assign_countries.html",
        {
            "page_obj": page_obj,
            "countries": country_list,
        },
    )


def update_competition_country(request: HttpRequest) -> JsonResponse:
    """
    View to update the country of a competition via AJAX.
    """
    if request.method == "POST":
        competition_id = request.POST.get("competition_id")
        country_code = request.POST.get("country")

        if competition_id and country_code:
            try:
                competition = Competition.objects.get(id=competition_id)
                competition.country = country_code
                competition.save()
                return JsonResponse({"status": "success"})
            except Competition.DoesNotExist:
                return JsonResponse({"status": "error", "message": "Competition not found"})

    return JsonResponse({"status": "error", "message": "Method not allowed"})


def propagate_countries(request: HttpRequest) -> HttpResponse:
    """
    View to propagate competition countries to clubs.
    """
    # Get list of countries
    country_list = list(countries)

    if request.method == "POST":
        # Resolve a specific conflict
        if "resolve_conflict" in request.POST:
            club_id = request.POST.get("club_id")
            country_code = request.POST.get("country_code")

            if club_id and country_code:
                club = Club.objects.get(id=club_id)
                club.country = country_code
                club.save()

                # Save this resolution to prevent it from appearing again
                # Use session to store resolved conflicts
                resolved_conflicts = request.session.get("resolved_conflicts", {})
                resolved_conflicts[club_id] = country_code
                request.session["resolved_conflicts"] = resolved_conflicts

                messages.success(request, f"Country updated for {club.name}")
                return redirect("assign_countries")

        # Resolve all conflicts with a strategy
        elif "resolve_all_conflicts" in request.POST:
            strategy = request.POST.get("strategy", "keep_existing")
            conflicts = request.session.get("current_conflicts", [])

            resolved_count = 0
            resolved_conflicts = request.session.get("resolved_conflicts", {})

            for conflict in conflicts:
                club_id = conflict["club_id"]
                existing_country = conflict["existing_country"]
                new_country = conflict["new_country"]

                try:
                    club = Club.objects.get(id=club_id)

                    # Apply selected strategy
                    if strategy == "keep_existing":
                        # Don't change, just mark as resolved
                        country_code = existing_country
                    else:  # use_new
                        club.country = new_country
                        club.save()
                        country_code = new_country

                    # Mark as resolved
                    resolved_conflicts[str(club_id)] = country_code
                    resolved_count += 1

                except Exception as e:
                    messages.error(request, f"Error resolving conflict for club {club_id}: {str(e)}")

            # Save resolved conflicts in session
            request.session["resolved_conflicts"] = resolved_conflicts

            messages.success(request, f"{resolved_count} conflicts have been resolved")
            return redirect("assign_countries")

        # Propagate competition countries to clubs
        else:
            # Get all competitions with a country assigned
            competitions_with_country = Competition.objects.filter(country__isnull=False)

            # Dict to store the most frequent country for each club
            club_countries = {}
            club_competitions = {}

            # For each competition, get its clubs
            for comp in competitions_with_country:
                clubs = Club.objects.filter(kit__competition=comp).distinct()

                for club in clubs:
                    if club.id not in club_countries:
                        club_countries[club.id] = {}
                        club_competitions[club.id] = {}

                    # Increment country counter
                    country_code = comp.country.code
                    club_countries[club.id][country_code] = club_countries[club.id].get(country_code, 0) + 1

                    # Store competition for reference
                    if country_code not in club_competitions[club.id]:
                        club_competitions[club.id][country_code] = []
                    club_competitions[club.id][country_code].append({"id": comp.id, "name": comp.name})

            # Determine most frequent country for each club
            conflicts = []
            updated_count = 0
            resolved_conflicts = request.session.get("resolved_conflicts", {})

            for club_id, country_counts in club_countries.items():
                try:
                    club = Club.objects.get(id=club_id)

                    # If this conflict was already resolved, apply the saved resolution
                    if str(club_id) in resolved_conflicts:
                        if club.country is None or club.country.code != resolved_conflicts[str(club_id)]:
                            club.country = resolved_conflicts[str(club_id)]
                            club.save()
                            updated_count += 1
                        continue

                    # Find most common country
                    most_common_country = max(country_counts.items(), key=lambda x: x[1])[0]

                    # If the club already has a country assigned and it is different, register conflict
                    if club.country and club.country.code != most_common_country:
                        comp_ref = club_competitions[club_id][most_common_country][0]

                        conflicts.append(
                            {
                                "club_id": club.id,
                                "club_name": club.name,
                                "existing_country": club.country.code,
                                "existing_country_name": club.country.name,
                                "new_country": most_common_country,
                                "new_country_name": dict(country_counts)[most_common_country],
                                "competition_id": comp_ref["id"],
                                "competition_name": comp_ref["name"],
                            }
                        )
                    # If no country assigned or is the same, update it
                    elif not club.country or club.country.code == most_common_country:
                        club.country = most_common_country
                        club.save()
                        updated_count += 1

                except Club.DoesNotExist:
                    continue

            # Save current conflicts in session
            request.session["current_conflicts"] = conflicts

            # If there are conflicts, show the conflict resolution page
            if conflicts:
                return render(
                    request,
                    "core/resolve_conflicts.html",
                    {
                        "conflicts": conflicts,
                        "conflict_count": len(conflicts),
                        "updated_count": updated_count,
                        "countries": country_list,
                    },
                )

            messages.success(request, f"{updated_count} clubs updated with competition countries")
            return redirect("assign_countries")

    # If GET, redirect to country assignment page
    return redirect("assign_countries")


def competition_clubs(request: HttpRequest, competition_id: int) -> HttpResponse:
    """
    View to show clubs related to a specific competition.
    """
    competition = get_object_or_404(Competition, id=competition_id)

    # Get all clubs with kits in this competition
    clubs = Club.objects.filter(kit__competition=competition).annotate(kit_count=Count("kit")).order_by("-kit_count")

    # Pagination
    paginator = Paginator(clubs, 50)  # Show 50 clubs per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "core/competition_clubs.html",
        {
            "competition": competition,
            "page_obj": page_obj,
            "total_clubs": clubs.count(),
        },
    )


def review_country_assignments(request: HttpRequest) -> HttpResponse:
    """
    View to review country assignments for clubs.
    Automatically looks for clubs that might be national teams based on the country name.
    """
    # Get list of countries
    country_list = list(countries)

    # Initialize variables
    selected_country = None
    clubs = []
    search_results = {}

    # If a specific country is selected
    if request.method == "GET" and "country" in request.GET:
        selected_country = request.GET.get("country")
        if selected_country:
            # Get all clubs with that country assigned
            clubs = (
                Club.objects.filter(country=selected_country).annotate(kit_count=Count("kit")).order_by("-kit_count")
            )

    # Processing a review
    if request.method == "POST":
        if "approve_all" in request.POST:
            # Do nothing, by default all are approved
            messages.success(request, "All assignments have been approved")
            return redirect("review_country_assignments")

        if "reject_clubs" in request.POST:
            club_ids = request.POST.getlist("reject_clubs")
            if club_ids:
                # Clear country from rejected clubs
                Club.objects.filter(id__in=club_ids).update(country=None)
                messages.success(request, f"{len(club_ids)} country assignments have been rejected")

                # Redirect to same page with selected country
                country = request.POST.get("selected_country")
                if country:
                    return redirect(f"{request.path}?country={country}")
                return redirect("review_country_assignments")

        if "assign_country" in request.POST:
            club_ids = request.POST.getlist("selected_clubs")
            country_code = request.POST.get("country_code")

            if club_ids and country_code:
                # Assign country to selected clubs
                Club.objects.filter(id__in=club_ids).update(country=country_code)
                country_name = dict(countries)[country_code]
                messages.success(request, f"{country_name} has been assigned to {len(club_ids)} clubs")
                return redirect("review_country_assignments")

        if "assign_all_countries" in request.POST:
            # Assign countries to all selected clubs automatically
            total_assigned = 0
            countries_assigned = []

            for country_code, country_name in country_list:
                # Find clubs whose name matches the country
                exact_matches = Club.objects.filter(name__iexact=country_name, country__isnull=True)
                partial_matches = Club.objects.filter(name__icontains=country_name, country__isnull=True).exclude(
                    id__in=exact_matches.values_list("id", flat=True)
                )

                # Assign the country to exactly matching clubs
                if exact_matches.exists():
                    exact_matches.update(country=country_code)
                    total_assigned += exact_matches.count()
                    countries_assigned.append(f"{country_name} ({exact_matches.count()} exact)")

                # Assign the country to partially matching clubs
                if partial_matches.exists():
                    partial_matches.update(country=country_code)
                    total_assigned += partial_matches.count()
                    if f"{country_name}" in countries_assigned:
                        idx = countries_assigned.index(f"{country_name}")
                        countries_assigned[idx] = (
                            f"{country_name} ({exact_matches.count()} exact, {partial_matches.count()} partial)"
                        )
                    else:
                        countries_assigned.append(f"{country_name} ({partial_matches.count()} partial)")

            if total_assigned > 0:
                countries_text = ", ".join(countries_assigned[:5])
                if len(countries_assigned) > 5:
                    countries_text += f" and {len(countries_assigned) - 5} more"

                messages.success(
                    request,
                    f"Countries assigned to {total_assigned} clubs automatically. Countries: {countries_text}",
                )
            else:
                messages.info(
                    request, "No clubs without a country that match country names were found."
                )

            return redirect("review_country_assignments")

    # Automatically search for clubs that may be national teams
    if not selected_country:
        search_results = {}

        for country_code, country_name in country_list:
            clubs_in_country = (
                Club.objects.filter(name__icontains=country_name)
                .annotate(kit_count=Count("kit"))
                .order_by("-kit_count")
            )

            # Store results if any
            if clubs_in_country.exists():
                search_results[country_code] = {
                    "name": country_name,
                    "clubs": clubs_in_country,
                    "count": clubs_in_country.count(),
                }

    # Pagination for selected country
    if selected_country:
        paginator = Paginator(clubs, 50)  # Show 50 clubs per page
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)
    else:
        page_obj = None

    return render(
        request,
        "core/review_country_assignments.html",
        {
            "countries": country_list,
            "selected_country": selected_country,
            "page_obj": page_obj,
            "total_clubs": clubs.count() if clubs else 0,
            "search_results": search_results,
        },
    )


@csrf_exempt
def get_club_competitions(request: HttpRequest) -> JsonResponse:
    """
    View to get a club's competitions via AJAX.
    """
    if request.method == "GET":
        club_id = request.GET.get("club_id")

        if club_id:
            try:
                club = Club.objects.get(id=club_id)

                # Get competitions for the club
                competitions = (
                    Competition.objects.filter(kit__team=club)
                    .annotate(kit_count=Count("id"))
                    .order_by("-kit_count")
                    .distinct()
                )

                # Format competitions for JSON response
                competitions_data = []
                for competition in competitions:
                    competition_data = {
                        "id": competition.id,
                        "name": competition.name,
                        "logo": competition.logo,
                        "kit_count": competition.kit_count,
                    }

                    if competition.country:
                        competition_data["country"] = competition.country.code
                        competition_data["country_name"] = dict(countries)[competition.country.code]

                    competitions_data.append(competition_data)

                return JsonResponse({"status": "success", "competitions": competitions_data})
            except Club.DoesNotExist:
                return JsonResponse({"status": "error", "message": "Club not found"})

    return JsonResponse({"status": "error", "message": "Method not allowed"})


def suggest_competition_countries(request: HttpRequest) -> JsonResponse:
    """
    View to suggest/assign countries to competitions based on the countries of the clubs participating in them.
    """
    # Request parameters
    min_clubs = int(request.GET.get("min_clubs", 3))
    min_percentage = float(request.GET.get("min_percentage", 65.0))
    only_without_country = request.GET.get("only_without_country", "true") == "true"
    exclude_international = request.GET.get("exclude_international", "true") == "true"
    page_number = request.GET.get("page", 1)

    # Keywords to detect international competitions
    international_keywords = [
        "champions",
        "copa",
        "libertadores",
        "mundial",
        "world",
        "international",
        "uefa",
        "conmebol",
        "concacaf",
        "fifa",
        "confederations",
        "nations",
        "euro",
        "america",
        "africa",
        "asia",
        "oceania",
        "supercopa",
        "supercup",
        "intercontinental",
        "confederation",
        "league of nations",
        "world cup",
    ]

    # Historical countries
    historical_countries = {
        "SU": "Soviet Union",
        "YU": "Yugoslavia",
        "CS": "Czechoslovakia",
        "DD": "East Germany",
    }

    # Process assignment (POST)
    if request.method == "POST":
        if "assign_country" in request.POST:
            competition_id = request.POST.get("competition_id")
            country_code = request.POST.get("country_code")

            if competition_id and country_code:
                try:
                    competition = Competition.objects.get(id=competition_id)
                    competition.country = country_code
                    competition.save()
                    messages.success(request, f"Country {dict(countries)[country_code]} assigned to {competition.name}")
                except Exception as e:
                    messages.error(request, f"Error assigning country: {str(e)}")

            return redirect("suggest_competition_countries")

        elif "assign_selected" in request.POST:
            competition_ids = request.POST.getlist("selected_competitions")

            if competition_ids:
                assigned_count = 0
                for comp_id in competition_ids:
                    country_code = request.POST.get(f"country_code_{comp_id}")
                    if country_code:
                        try:
                            competition = Competition.objects.get(id=comp_id)
                            competition.country = country_code
                            competition.save()
                            assigned_count += 1
                        except Exception as e:
                            messages.error(request, f"Error assigning country to competition {comp_id}: {str(e)}")

                if assigned_count > 0:
                    messages.success(request, f"Countries assigned to {assigned_count} competitions")
                else:
                    messages.warning(request, "No countries were assigned to any competitions")
            else:
                messages.warning(request, "No competitions were selected")

            # Redirect to same page with filter parameters
            params = {}
            if min_clubs != 3:
                params["min_clubs"] = min_clubs
            if min_percentage != 60.0:
                params["min_percentage"] = min_percentage
            if only_without_country:
                params["only_without_country"] = "true"
            if exclude_international:
                params["exclude_international"] = "true"
            if page_number != 1:
                params["page"] = page_number

            return redirect(f"{reverse('suggest_competition_countries')}?{urlencode(params)}")

    # Get competitions with annotations
    query = Competition.objects.annotate(
        club_count=Count("kit__team", distinct=True),
        clubs_with_country=Count("kit__team", distinct=True, filter=Q(kit__team__country__isnull=False)),
    )

    if only_without_country:
        query = query.filter(country__isnull=True)

    competitions = query.order_by("-club_count")

    results = []

    for comp in competitions:
        if comp.club_count == 0:
            continue

        has_country = comp.country is not None
        clubs = Club.objects.filter(kit__competition=comp).distinct()

        country_counter = Counter()
        for club in clubs:
            if club.country:
                country_counter[club.country.code] += 1

        if sum(country_counter.values()) < min_clubs:
            continue

        most_common_countries = country_counter.most_common(3)
        if not most_common_countries:
            continue

        country_code, count = most_common_countries[0]
        confidence = (count / sum(country_counter.values())) * 100

        if confidence < min_percentage:
            continue

        is_international = False
        comp_name_lower = comp.name.lower()
        for keyword in international_keywords:
            if keyword in comp_name_lower:
                is_international = True
                break

        if exclude_international and is_international:
            continue

        notes = []
        if is_international:
            notes.append("Possible international competition")

        if country_code in historical_countries:
            notes.append(f"Historical country: {historical_countries[country_code]}")

        if has_country and comp.country.code != country_code:
            notes.append(f"Already assigned country: {comp.country.name}")

        results.append(
            {
                "id": comp.id,
                "name": comp.name,
                "club_count": comp.club_count,
                "clubs_with_country": sum(country_counter.values()),
                "suggested_country": dict(countries)[country_code],
                "country_code": country_code,
                "confidence": confidence,
                "notes": notes,
                "has_country": has_country,
                "current_country": comp.country.name if has_country else None,
                "current_country_code": comp.country.code if has_country else None,
                "is_international": is_international,
                "top_countries": [
                    {
                        "code": code,
                        "name": dict(countries)[code],
                        "count": cnt,
                        "percentage": (cnt / sum(country_counter.values())) * 100,
                    }
                    for code, cnt in most_common_countries
                ],
            }
        )

    paginator = Paginator(results, 20)  # 20 competitions per page
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "min_clubs": min_clubs,
        "min_percentage": min_percentage,
        "only_without_country": only_without_country,
        "exclude_international": exclude_international,
        "total_results": len(results),
        "countries": countries,
    }

    return render(request, "core/suggest_competition_countries.html", context)


def clubs_without_country(request: HttpRequest) -> HttpResponse:
    """
    View to display clubs with the most kits that do not yet have a country assigned,
    allowing assignment of a country directly.
    """
    # Get request parameters
    min_kits = int(request.GET.get("min_kits", 5))
    page_number = request.GET.get("page", 1)
    search_query = request.GET.get("search", "")

    # Get clubs without a country, ordered by number of kits (descending)
    clubs_query = (
        Club.objects.filter(country__isnull=True)
        .annotate(kit_count=Count("kit"))
        .filter(kit_count__gte=min_kits)
        .order_by("-kit_count")
    )

    # Search filter if any
    if search_query:
        clubs_query = clubs_query.filter(name__icontains=search_query)

    # Process country assignment (POST)
    if request.method == "POST":
        if "assign_country" in request.POST:
            club_id = request.POST.get("club_id")
            country_code = request.POST.get("country_code")

            if club_id and country_code:
                try:
                    club = Club.objects.get(id=club_id)
                    club.country = country_code
                    club.save()
                    messages.success(request, f"Country {dict(countries)[country_code]} assigned to {club.name}")
                except Exception as e:
                    messages.error(request, f"Error assigning country: {str(e)}")

            params = {}
            if min_kits != 5:
                params["min_kits"] = min_kits
            if search_query:
                params["search"] = search_query
            if page_number != 1:
                params["page"] = page_number

            return redirect(f"{reverse('clubs_without_country')}?{urlencode(params)}")

        elif "assign_selected" in request.POST:
            club_ids = request.POST.getlist("selected_clubs")
            country_code = request.POST.get("country_code")

            if club_ids and country_code:
                assigned_count = 0
                for club_id in club_ids:
                    try:
                        club = Club.objects.get(id=club_id)
                        club.country = country_code
                        club.save()
                        assigned_count += 1
                    except Exception as e:
                        messages.error(request, f"Error assigning country to club {club_id}: {str(e)}")

                if assigned_count > 0:
                    messages.success(
                        request, f"Country {dict(countries)[country_code]} assigned to {assigned_count} clubs"
                    )
                else:
                    messages.warning(request, "No club was assigned a country")
            else:
                if not club_ids:
                    messages.warning(request, "No clubs were selected")
                if not country_code:
                    messages.warning(request, "No country was selected")

            params = {}
            if min_kits != 5:
                params["min_kits"] = min_kits
            if search_query:
                params["search"] = search_query
            if page_number != 1:
                params["page"] = page_number

            return redirect(f"{reverse('clubs_without_country')}?{urlencode(params)}")

    paginator = Paginator(clubs_query, 20)  # 20 clubs per page
    page_obj = paginator.get_page(page_number)

    # Get most frequent competitions per club and suggest country
    for club in page_obj:
        competitions = Competition.objects.filter(kit__team=club).annotate(count=Count("id")).order_by("-count")[:3]
        club.top_competitions = competitions

        # Suggest a country based on competitions
        suggested_country = None
        for comp in competitions:
            if comp.country:
                suggested_country = comp.country
                break

        club.suggested_country = suggested_country

    context = {
        "page_obj": page_obj,
        "min_kits": min_kits,
        "search_query": search_query,
        "total_clubs": clubs_query.count(),
        "countries": countries,
    }

    return render(request, "core/clubs_without_country.html", context)


def random_kits_view(request: HttpRequest) -> HttpResponse:
    """
    View for random kits page with infinite scroll.
    """
    return render(request, "core/random_kits.html")


def random_clubs_view(request: HttpRequest) -> HttpResponse:
    """
    View for random clubs page with infinite scroll.
    """
    return render(request, "core/random_clubs.html")


def load_more_kits(request: HttpRequest) -> JsonResponse:
    """
    AJAX endpoint to load more kits.
    """
    try:
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 20))

        result = get_random_kits(request, page=page, page_size=page_size)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def load_more_clubs(request: HttpRequest) -> JsonResponse:
    """
    AJAX endpoint to load more clubs.
    """
    try:
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 20))

        result = get_random_clubs(request, page=page, page_size=page_size)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def top_clubs_by_country(request: HttpRequest) -> HttpResponse:
    """
    View to display nations ordered by total number of kits,
    showing the top 50 clubs per country (at least 20 kits).
    """
    min_kits = int(request.GET.get("min_kits", 20))
    page_number = request.GET.get("page", 1)

    countries_with_kits = (
        Club.objects.filter(country__isnull=False)
        .values("country")
        .annotate(total_kits=Count("kit"))
        .filter(total_kits__gte=min_kits)
        .order_by("-total_kits")
    )

    paginator = Paginator(countries_with_kits, 20)
    page_obj = paginator.get_page(page_number)

    countries_data = []
    for country_data in page_obj:
        country_code = country_data["country"]
        total_kits = country_data["total_kits"]

        top_clubs = (
            Club.objects.filter(country=country_code)
            .annotate(kit_count=Count("kit"))
            .filter(kit_count__gte=min_kits)
            .order_by("-kit_count")[:50]
        )

        countries_data.append(
            {
                "country_code": country_code,
                "country_name": dict(countries)[country_code] if country_code in dict(countries) else country_code,
                "total_kits": total_kits,
                "clubs": top_clubs,
                "club_count": top_clubs.count(),
            }
        )

    return render(
        request,
        "core/top_clubs_by_country.html",
        {
            "countries_data": countries_data,
            "page_obj": page_obj,
            "min_kits": min_kits,
        },
    )
