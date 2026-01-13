from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, F, Q, Case, When, Value, IntegerField
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django_countries import countries
from .models import Competition, Club, Kit
from collections import Counter
import json
from django.urls import reverse
from urllib.parse import urlencode
from fkapi.api import get_random_kits, get_random_clubs

def assign_countries(request):
    """
    Vista para asignar países a las competiciones.
    Ordena las competiciones por la cantidad de kits relacionados.
    """
    # Obtener todas las competiciones ordenadas por cantidad de kits
    competitions = Competition.objects.filter(country__isnull=True).annotate(
        kit_count=Count('kit')
    ).order_by('-kit_count')
    
    # Paginación
    paginator = Paginator(competitions, 20)  # Mostrar 20 competiciones por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Obtener la lista de países
    country_list = list(countries)
    
    # Procesar el formulario si es una solicitud POST
    if request.method == 'POST':
        competition_id = request.POST.get('competition_id')
        country_code = request.POST.get('country')
        
        if competition_id and country_code:
            competition = Competition.objects.get(id=competition_id)
            competition.country = country_code
            competition.save()
            messages.success(request, f'País asignado correctamente a {competition.name}')
            return redirect('assign_countries')
    
    return render(request, 'core/assign_countries.html', {
        'page_obj': page_obj,
        'countries': country_list,
    })

@csrf_exempt
def update_competition_country(request):
    """
    Vista para actualizar el país de una competición mediante AJAX.
    """
    if request.method == 'POST':
        competition_id = request.POST.get('competition_id')
        country_code = request.POST.get('country')
        
        if competition_id and country_code:
            try:
                competition = Competition.objects.get(id=competition_id)
                competition.country = country_code
                competition.save()
                return JsonResponse({'status': 'success'})
            except Competition.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Competición no encontrada'})
    
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'})

def propagate_countries(request):
    """
    Vista para propagar países de competiciones a clubes.
    """
    if request.method == 'POST':
        # Resolver un conflicto específico
        if 'resolve_conflict' in request.POST:
            club_id = request.POST.get('club_id')
            country_code = request.POST.get('country_code')
            
            if club_id and country_code:
                club = Club.objects.get(id=club_id)
                club.country = country_code
                club.save()
                
                # Guardar esta resolución para evitar que aparezca de nuevo
                # Usamos una sesión para almacenar los conflictos resueltos
                resolved_conflicts = request.session.get('resolved_conflicts', {})
                resolved_conflicts[club_id] = country_code
                request.session['resolved_conflicts'] = resolved_conflicts
                
                messages.success(request, f'País actualizado para {club.name}')
                return redirect('assign_countries')
        
        # Resolver todos los conflictos con una estrategia
        elif 'resolve_all_conflicts' in request.POST:
            strategy = request.POST.get('strategy', 'keep_existing')
            conflicts = request.session.get('current_conflicts', [])
            
            resolved_count = 0
            resolved_conflicts = request.session.get('resolved_conflicts', {})
            
            for conflict in conflicts:
                club_id = conflict['club_id']
                existing_country = conflict['existing_country']
                new_country = conflict['new_country']
                
                try:
                    club = Club.objects.get(id=club_id)
                    
                    # Aplicar la estrategia seleccionada
                    if strategy == 'keep_existing':
                        # No cambiar nada, pero marcar como resuelto
                        country_code = existing_country
                    else:  # use_new
                        club.country = new_country
                        club.save()
                        country_code = new_country
                    
                    # Marcar como resuelto
                    resolved_conflicts[str(club_id)] = country_code
                    resolved_count += 1
                    
                except Exception as e:
                    messages.error(request, f'Error al resolver conflicto para club {club_id}: {str(e)}')
            
            # Guardar los conflictos resueltos en la sesión
            request.session['resolved_conflicts'] = resolved_conflicts
            
            messages.success(request, f'Se han resuelto {resolved_count} conflictos')
            return redirect('assign_countries')
        
        # Propagar países de competiciones a clubes
        else:
            # Obtener todas las competiciones con país asignado
            # No usar select_related para country porque es un CountryField, no una relación
            competitions_with_country = Competition.objects.filter(
                country__isnull=False
            )
            
            # Diccionario para almacenar el país más frecuente para cada club
            club_countries = {}
            club_competitions = {}
            
            # Para cada competición, obtener sus clubes
            for comp in competitions_with_country:
                # Obtener todos los clubes que participan en esta competición
                clubs = Club.objects.filter(kit__competition=comp).distinct()
                
                for club in clubs:
                    # Si el club ya tiene un país asignado, saltarlo
                    if club.id not in club_countries:
                        club_countries[club.id] = {}
                        club_competitions[club.id] = {}
                    
                    # Incrementar el contador para este país
                    country_code = comp.country.code
                    club_countries[club.id][country_code] = club_countries[club.id].get(country_code, 0) + 1
                    
                    # Guardar la competición para referencia
                    if country_code not in club_competitions[club.id]:
                        club_competitions[club.id][country_code] = []
                    club_competitions[club.id][country_code].append({
                        'id': comp.id,
                        'name': comp.name
                    })
            
            # Determinar el país más frecuente para cada club
            conflicts = []
            updated_count = 0
            resolved_conflicts = request.session.get('resolved_conflicts', {})
            
            for club_id, countries in club_countries.items():
                # Obtener el club
                try:
                    club = Club.objects.get(id=club_id)
                    
                    # Si este conflicto ya fue resuelto, aplicar la resolución guardada
                    if str(club_id) in resolved_conflicts:
                        if club.country is None or club.country.code != resolved_conflicts[str(club_id)]:
                            club.country = resolved_conflicts[str(club_id)]
                            club.save()
                            updated_count += 1
                        continue
                    
                    # Encontrar el país más frecuente
                    most_common_country = max(countries.items(), key=lambda x: x[1])[0]
                    
                    # Si el club ya tiene un país asignado y es diferente, registrar conflicto
                    if club.country and club.country.code != most_common_country:
                        # Obtener la competición de referencia
                        comp_ref = club_competitions[club_id][most_common_country][0]
                        
                        conflicts.append({
                            'club_id': club.id,
                            'club_name': club.name,
                            'existing_country': club.country.code,
                            'existing_country_name': club.country.name,
                            'new_country': most_common_country,
                            'new_country_name': dict(countries)[most_common_country],
                            'competition_id': comp_ref['id'],
                            'competition_name': comp_ref['name']
                        })
                    # Si no tiene país o es el mismo, actualizarlo
                    elif not club.country or club.country.code == most_common_country:
                        club.country = most_common_country
                        club.save()
                        updated_count += 1
                
                except Club.DoesNotExist:
                    continue
            
            # Guardar los conflictos actuales en la sesión
            request.session['current_conflicts'] = conflicts
            
            # Si hay conflictos, mostrar la página de resolución
            if conflicts:
                return render(request, 'core/resolve_conflicts.html', {
                    'conflicts': conflicts,
                    'conflict_count': len(conflicts),
                    'updated_count': updated_count,
                    'countries': countries
                })
            
            messages.success(request, f'Se han actualizado {updated_count} clubes con países de sus competiciones')
            return redirect('assign_countries')
    
    # Si es GET, redirigir a la página de asignación de países
    return redirect('assign_countries')

def competition_clubs(request, competition_id):
    """
    Vista para mostrar los clubes relacionados con una competición específica.
    """
    competition = get_object_or_404(Competition, id=competition_id)
    
    # Obtener todos los clubes que tienen kits en esta competición
    clubs = Club.objects.filter(
        kit__competition=competition
    ).annotate(
        kit_count=Count('kit')
    ).order_by('-kit_count')
    
    # Paginación
    paginator = Paginator(clubs, 50)  # Mostrar 50 clubes por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'core/competition_clubs.html', {
        'competition': competition,
        'page_obj': page_obj,
        'total_clubs': clubs.count(),
    })

def review_country_assignments(request):
    """
    Vista para revisar las asignaciones de países a equipos.
    Busca automáticamente equipos que puedan ser selecciones nacionales basándose en el nombre del país.
    """
    # Obtener la lista de países
    country_list = list(countries)
    
    # Inicializar variables
    selected_country = None
    clubs = []
    search_results = {}
    
    # Si se ha seleccionado un país específico
    if request.method == 'GET' and 'country' in request.GET:
        selected_country = request.GET.get('country')
        if selected_country:
            # Obtener todos los clubes con ese país asignado
            clubs = Club.objects.filter(country=selected_country).annotate(
                kit_count=Count('kit')
            ).order_by('-kit_count')
    
    # Si se está procesando una revisión
    if request.method == 'POST':
        if 'approve_all' in request.POST:
            # No hacemos nada, ya que por defecto están aprobados
            messages.success(request, 'Todas las asignaciones han sido aprobadas')
            return redirect('review_country_assignments')
        
        if 'reject_clubs' in request.POST:
            club_ids = request.POST.getlist('reject_clubs')
            if club_ids:
                # Limpiar el país de los clubes rechazados
                Club.objects.filter(id__in=club_ids).update(country=None)
                messages.success(request, f'Se han rechazado {len(club_ids)} asignaciones de país')
                
                # Redirigir a la misma página con el país seleccionado
                country = request.POST.get('selected_country')
                if country:
                    return redirect(f'{request.path}?country={country}')
                return redirect('review_country_assignments')
        
        if 'assign_country' in request.POST:
            club_ids = request.POST.getlist('selected_clubs')
            country_code = request.POST.get('country_code')
            
            if club_ids and country_code:
                # Asignar el país a los clubes seleccionados
                Club.objects.filter(id__in=club_ids).update(country=country_code)
                country_name = dict(countries)[country_code]
                messages.success(request, f'Se ha asignado {country_name} a {len(club_ids)} equipos')
                return redirect('review_country_assignments')
        
        if 'assign_all_countries' in request.POST:
            # Asignar todos los países a los equipos seleccionados
            total_assigned = 0
            countries_assigned = []
            
            for country_code, country_name in country_list:
                # Buscar clubes que contengan el nombre del país y no tengan país asignado
                # Primero buscamos coincidencias exactas (nombre del país completo)
                exact_matches = Club.objects.filter(
                    name__iexact=country_name,
                    country__isnull=True
                )
                
                # Luego buscamos coincidencias que contengan el nombre del país
                # Excluimos clubes que ya tienen país asignado
                partial_matches = Club.objects.filter(
                    name__icontains=country_name,
                    country__isnull=True
                ).exclude(id__in=exact_matches.values_list('id', flat=True))
                
                # Asignar el país a los clubes con coincidencia exacta
                if exact_matches.exists():
                    exact_matches.update(country=country_code)
                    total_assigned += exact_matches.count()
                    countries_assigned.append(f"{country_name} ({exact_matches.count()} exactos)")
                
                # Asignar el país a los clubes con coincidencia parcial
                if partial_matches.exists():
                    partial_matches.update(country=country_code)
                    total_assigned += partial_matches.count()
                    if f"{country_name}" in countries_assigned:
                        # Actualizar el contador si ya existe
                        idx = countries_assigned.index(f"{country_name}")
                        countries_assigned[idx] = f"{country_name} ({exact_matches.count()} exactos, {partial_matches.count()} parciales)"
                    else:
                        countries_assigned.append(f"{country_name} ({partial_matches.count()} parciales)")
            
            if total_assigned > 0:
                countries_text = ", ".join(countries_assigned[:5])
                if len(countries_assigned) > 5:
                    countries_text += f" y {len(countries_assigned) - 5} más"
                
                messages.success(request, f'Se han asignado países a {total_assigned} equipos automáticamente. Países asignados: {countries_text}')
            else:
                messages.info(request, 'No se encontraron equipos sin país asignado que coincidan con nombres de países.')
            
            return redirect('review_country_assignments')
    
    # Buscar automáticamente equipos que puedan ser selecciones nacionales
    if not selected_country:
        search_results = {}
        
        for country_code, country_name in country_list:
            # Buscar clubes que contengan el nombre del país
            country_clubs = Club.objects.filter(
                name__icontains=country_name
            ).annotate(
                kit_count=Count('kit')
            ).order_by('-kit_count')
            
            # Si hay resultados, guardarlos
            if country_clubs.exists():
                search_results[country_code] = {
                    'name': country_name,
                    'clubs': country_clubs,
                    'count': country_clubs.count()
                }
    
    # Paginación para el país seleccionado
    if selected_country:
        paginator = Paginator(clubs, 50)  # Mostrar 50 clubes por página
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
    else:
        page_obj = None
    
    return render(request, 'core/review_country_assignments.html', {
        'countries': country_list,
        'selected_country': selected_country,
        'page_obj': page_obj,
        'total_clubs': clubs.count() if clubs else 0,
        'search_results': search_results,
    })

@csrf_exempt
def get_club_competitions(request):
    """
    Vista para obtener las competiciones de un club mediante AJAX.
    """
    if request.method == 'GET':
        club_id = request.GET.get('club_id')
        
        if club_id:
            try:
                club = Club.objects.get(id=club_id)
                
                # Obtener las competiciones del club
                competitions = Competition.objects.filter(
                    kit__team=club
                ).annotate(
                    kit_count=Count('id')
                ).order_by('-kit_count').distinct()
                
                # Formatear las competiciones para la respuesta JSON
                competitions_data = []
                for competition in competitions:
                    competition_data = {
                        'id': competition.id,
                        'name': competition.name,
                        'logo': competition.logo,
                        'kit_count': competition.kit_count,
                    }
                    
                    if competition.country:
                        competition_data['country'] = competition.country.code
                        competition_data['country_name'] = dict(countries)[competition.country.code]
                    
                    competitions_data.append(competition_data)
                
                return JsonResponse({
                    'status': 'success',
                    'competitions': competitions_data
                })
            except Club.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Club no encontrado'
                })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Método no permitido'
    })

# Añadir la nueva vista para sugerir países a competiciones
def suggest_competition_countries(request):
    """
    Vista para sugerir y asignar países a competiciones basándose en los países
    de los equipos que participan en ellas.
    """
    # Parámetros de la solicitud
    min_clubs = int(request.GET.get('min_clubs', 3))
    min_percentage = float(request.GET.get('min_percentage', 65.0))
    only_without_country = request.GET.get('only_without_country', 'true') == 'true'
    exclude_international = request.GET.get('exclude_international', 'true') == 'true'
    page_number = request.GET.get('page', 1)
    
    # Palabras clave para identificar competiciones internacionales
    international_keywords = [
        'champions', 'copa', 'libertadores', 'mundial', 'world', 'international',
        'uefa', 'conmebol', 'concacaf', 'fifa', 'confederations', 'nations',
        'euro', 'america', 'africa', 'asia', 'oceania', 'supercopa', 'supercup',
        'intercontinental', 'confederation', 'league of nations', 'world cup'
    ]
    
    # Países que se separaron históricamente
    historical_countries = {
        'SU': 'Unión Soviética',
        'YU': 'Yugoslavia',
        'CS': 'Checoslovaquia',
        'DD': 'Alemania Oriental',
    }
    
    # Procesar asignaciones si es una solicitud POST
    if request.method == 'POST':
        if 'assign_country' in request.POST:
            competition_id = request.POST.get('competition_id')
            country_code = request.POST.get('country_code')
            
            if competition_id and country_code:
                try:
                    competition = Competition.objects.get(id=competition_id)
                    competition.country = country_code
                    competition.save()
                    messages.success(request, f'País {dict(countries)[country_code]} asignado a {competition.name}')
                except Exception as e:
                    messages.error(request, f'Error al asignar país: {str(e)}')
            
            # Redirigir a la misma página para evitar reenvío del formulario
            return redirect('suggest_competition_countries')
        
        elif 'assign_selected' in request.POST:
            competition_ids = request.POST.getlist('selected_competitions')
            
            if competition_ids:
                assigned_count = 0
                for comp_id in competition_ids:
                    country_code = request.POST.get(f'country_code_{comp_id}')
                    if country_code:
                        try:
                            competition = Competition.objects.get(id=comp_id)
                            competition.country = country_code
                            competition.save()
                            assigned_count += 1
                        except Exception as e:
                            messages.error(request, f'Error al asignar país a competición {comp_id}: {str(e)}')
                
                if assigned_count > 0:
                    messages.success(request, f'Países asignados a {assigned_count} competiciones')
                else:
                    messages.warning(request, 'No se asignaron países a ninguna competición')
            else:
                messages.warning(request, 'No se seleccionaron competiciones')
            
            # Redirigir a la misma página con los mismos parámetros de filtro
            params = {}
            if min_clubs != 3:
                params['min_clubs'] = min_clubs
            if min_percentage != 60.0:
                params['min_percentage'] = min_percentage
            if only_without_country:
                params['only_without_country'] = 'true'
            if exclude_international:
                params['exclude_international'] = 'true'
            if page_number != 1:
                params['page'] = page_number
                
            return redirect(f"{reverse('suggest_competition_countries')}?{urlencode(params)}")
    
    # Obtener todas las competiciones con anotaciones
    query = Competition.objects.annotate(
        club_count=Count('kit__team', distinct=True),
        clubs_with_country=Count('kit__team', distinct=True, filter=Q(kit__team__country__isnull=False))
    )
    
    if only_without_country:
        query = query.filter(country__isnull=True)
    
    # Ordenar por número de equipos (descendente)
    competitions = query.order_by('-club_count')
    
    # Preparar los resultados
    results = []
    
    for comp in competitions:
        # Saltarse competiciones sin equipos
        if comp.club_count == 0:
            continue
        
        # Verificar si ya tiene país asignado
        has_country = comp.country is not None
        
        # Obtener todos los equipos de esta competición
        clubs = Club.objects.filter(kit__competition=comp).distinct()
        
        # Contar los países de los equipos
        country_counter = Counter()
        for club in clubs:
            if club.country:
                country_counter[club.country.code] += 1
        
        # Si no hay suficientes equipos con país, continuar
        if sum(country_counter.values()) < min_clubs:
            continue
        
        # Encontrar el país más común
        most_common_countries = country_counter.most_common(3)  # Obtener los 3 más comunes
        if not most_common_countries:
            continue
        
        country_code, count = most_common_countries[0]
        confidence = (count / sum(country_counter.values())) * 100
        
        # Verificar si cumple con el porcentaje mínimo
        if confidence < min_percentage:
            continue
        
        # Verificar si es una competición internacional
        is_international = False
        comp_name_lower = comp.name.lower()
        for keyword in international_keywords:
            if keyword in comp_name_lower:
                is_international = True
                break
        
        # Si se excluyen internacionales y esta lo es, saltarla
        if exclude_international and is_international:
            continue
        
        # Preparar notas
        notes = []
        if is_international:
            notes.append("Posible competición internacional")
        
        if country_code in historical_countries:
            notes.append(f"País histórico: {historical_countries[country_code]}")
        
        if has_country and comp.country.code != country_code:
            notes.append(f"Ya tiene país asignado: {comp.country.name}")
        
        # Añadir a los resultados
        results.append({
            'id': comp.id,
            'name': comp.name,
            'club_count': comp.club_count,
            'clubs_with_country': sum(country_counter.values()),
            'suggested_country': dict(countries)[country_code],
            'country_code': country_code,
            'confidence': confidence,
            'notes': notes,
            'has_country': has_country,
            'current_country': comp.country.name if has_country else None,
            'current_country_code': comp.country.code if has_country else None,
            'is_international': is_international,
            'top_countries': [
                {
                    'code': code,
                    'name': dict(countries)[code],
                    'count': cnt,
                    'percentage': (cnt / sum(country_counter.values())) * 100
                }
                for code, cnt in most_common_countries
            ]
        })
    
    # Paginar los resultados
    paginator = Paginator(results, 20)  # 20 competiciones por página
    page_obj = paginator.get_page(page_number)
    
    # Preparar el contexto
    context = {
        'page_obj': page_obj,
        'min_clubs': min_clubs,
        'min_percentage': min_percentage,
        'only_without_country': only_without_country,
        'exclude_international': exclude_international,
        'total_results': len(results),
        'countries': countries,
    }
    
    return render(request, 'core/suggest_competition_countries.html', context)

def clubs_without_country(request):
    """
    Vista para mostrar los clubes con más kits que aún no tienen país asignado,
    permitiendo asignarles un país directamente.
    """
    # Obtener parámetros de la solicitud
    min_kits = int(request.GET.get('min_kits', 5))
    page_number = request.GET.get('page', 1)
    search_query = request.GET.get('search', '')
    
    # Obtener clubes sin país asignado, ordenados por cantidad de kits (descendente)
    clubs_query = Club.objects.filter(
        country__isnull=True
    ).annotate(
        kit_count=Count('kit')
    ).filter(
        kit_count__gte=min_kits
    ).order_by('-kit_count')
    
    # Aplicar filtro de búsqueda si existe
    if search_query:
        clubs_query = clubs_query.filter(name__icontains=search_query)
    
    # Procesar asignación de país si es una solicitud POST
    if request.method == 'POST':
        if 'assign_country' in request.POST:
            club_id = request.POST.get('club_id')
            country_code = request.POST.get('country_code')
            
            if club_id and country_code:
                try:
                    club = Club.objects.get(id=club_id)
                    club.country = country_code
                    club.save()
                    messages.success(request, f'País {dict(countries)[country_code]} asignado a {club.name}')
                except Exception as e:
                    messages.error(request, f'Error al asignar país: {str(e)}')
            
            # Redirigir a la misma página con los mismos parámetros
            params = {}
            if min_kits != 5:
                params['min_kits'] = min_kits
            if search_query:
                params['search'] = search_query
            if page_number != 1:
                params['page'] = page_number
                
            return redirect(f"{reverse('clubs_without_country')}?{urlencode(params)}")
        
        elif 'assign_selected' in request.POST:
            club_ids = request.POST.getlist('selected_clubs')
            country_code = request.POST.get('country_code')
            
            if club_ids and country_code:
                assigned_count = 0
                for club_id in club_ids:
                    try:
                        club = Club.objects.get(id=club_id)
                        club.country = country_code
                        club.save()
                        assigned_count += 1
                    except Exception as e:
                        messages.error(request, f'Error al asignar país a club {club_id}: {str(e)}')
                
                if assigned_count > 0:
                    messages.success(request, f'País {dict(countries)[country_code]} asignado a {assigned_count} clubes')
                else:
                    messages.warning(request, 'No se asignó país a ningún club')
            else:
                if not club_ids:
                    messages.warning(request, 'No se seleccionaron clubes')
                if not country_code:
                    messages.warning(request, 'No se seleccionó un país')
            
            # Redirigir a la misma página con los mismos parámetros
            params = {}
            if min_kits != 5:
                params['min_kits'] = min_kits
            if search_query:
                params['search'] = search_query
            if page_number != 1:
                params['page'] = page_number
                
            return redirect(f"{reverse('clubs_without_country')}?{urlencode(params)}")
    
    # Paginar los resultados
    paginator = Paginator(clubs_query, 20)  # 20 clubes por página
    page_obj = paginator.get_page(page_number)
    
    # Obtener las competiciones más frecuentes para cada club
    for club in page_obj:
        # Obtener las competiciones más frecuentes del club
        competitions = Competition.objects.filter(
            kit__team=club
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:3]
        
        # Añadir las competiciones al objeto club
        club.top_competitions = competitions
        
        # Sugerir un país basado en las competiciones
        suggested_country = None
        for comp in competitions:
            if comp.country:
                suggested_country = comp.country
                break
        
        club.suggested_country = suggested_country
    
    # Preparar el contexto
    context = {
        'page_obj': page_obj,
        'min_kits': min_kits,
        'search_query': search_query,
        'total_clubs': clubs_query.count(),
        'countries': countries,
    }
    
    return render(request, 'core/clubs_without_country.html', context)



def random_kits_view(request):
    """
    View for random kits page with infinite scroll.
    """
    return render(request, 'core/random_kits.html')


def random_clubs_view(request):
    """
    View for random clubs page with infinite scroll.
    """
    return render(request, 'core/random_clubs.html')


def load_more_kits(request):
    """
    AJAX endpoint to load more kits.
    """
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        
        # Call API function directly instead of HTTP request
        result = get_random_kits(request, page=page, page_size=page_size)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def load_more_clubs(request):
    """
    AJAX endpoint to load more clubs.
    """
    page = request.GET.get('page', 1)
    page_size = request.GET.get('page_size', 20)
    try:
        # Make request to our API
        response = requests.get(
            f'http://localhost:8787/api/random-clubs/?page={page}&page_size={page_size}',
            timeout=15
        )
        if response.status_code == 200:
            return JsonResponse(response.json())
        else:
            # Add more logging for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to load clubs -- status: {response.status_code}, response: {response.text}")
            return JsonResponse({'error': 'Failed to load clubs', 'status_code': response.status_code, 'response': response.text}, status=500)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Exception when loading clubs: {e}")
        return JsonResponse({'error': str(e)}, status=500)


def merge_suggestions_view(request):
    """View to display merge suggestions interface"""
    return render(request, 'core/merge_suggestions.html')


def top_clubs_by_country(request):
    """
    Vista para mostrar las naciones ordenadas por número de kits,
    mostrando los top 50 clubs de cada país (mínimo 20 kits).
    """
    min_kits = int(request.GET.get('min_kits', 20))
    page_number = request.GET.get('page', 1)
    
    countries_with_kits = Club.objects.filter(
        country__isnull=False
    ).values('country').annotate(
        total_kits=Count('kit')
    ).filter(
        total_kits__gte=min_kits
    ).order_by('-total_kits')
    
    paginator = Paginator(countries_with_kits, 20)
    page_obj = paginator.get_page(page_number)
    
    countries_data = []
    for country_data in page_obj:
        country_code = country_data['country']
        total_kits = country_data['total_kits']
        
        top_clubs = Club.objects.filter(
            country=country_code
        ).annotate(
            kit_count=Count('kit')
        ).filter(
            kit_count__gte=min_kits
        ).order_by('-kit_count')[:50]
        
        countries_data.append({
            'country_code': country_code,
            'country_name': dict(countries)[country_code] if country_code in dict(countries) else country_code,
            'total_kits': total_kits,
            'clubs': top_clubs,
            'club_count': top_clubs.count(),
        })
    
    return render(request, 'core/top_clubs_by_country.html', {
        'countries_data': countries_data,
        'page_obj': page_obj,
        'min_kits': min_kits,
    })
