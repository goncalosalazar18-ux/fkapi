"""Tests for API endpoints."""
import pytest
from django.test import Client
from django.contrib.auth import get_user_model

from core.models import Brand, Club, Competition, Kit, Season, Type_K

User = get_user_model()


@pytest.fixture
def api_client():
    """Create a test API client."""
    return Client()


@pytest.fixture
def test_data(db):
    """Create test data for API tests."""
    season = Season.objects.create(year="2024-25", first_year="2024", second_year="2025")
    club = Club.objects.create(slug="test-club", name="Test Club", logo="https://example.com/logo.png")
    brand = Brand.objects.create(slug="test-brand", name="Test Brand", logo="https://example.com/brand.png")
    competition = Competition.objects.create(slug="test-competition", name="Test Competition")
    type_k = Type_K.objects.create(name="Home")
    
    kit = Kit.objects.create(
        slug="test-kit",
        name="Test Kit",
        team=club,
        season=season,
        type=type_k,
        brand=brand,
        main_img_url="https://example.com/kit.jpg",
        rating=8.5
    )
    kit.competition.add(competition)
    
    return {
        "season": season,
        "club": club,
        "brand": brand,
        "competition": competition,
        "type_k": type_k,
        "kit": kit,
    }


@pytest.mark.django_db
def test_health_check(api_client):
    """Test health check endpoint."""
    response = api_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "unhealthy"]


@pytest.mark.django_db
def test_search_clubs(api_client, test_data):
    """Test club search endpoint."""
    response = api_client.get("/api/clubs/search", {"keyword": "test"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        assert "id" in data[0]
        assert "name" in data[0]


@pytest.mark.django_db
def test_search_brands(api_client, test_data):
    """Test brand search endpoint."""
    response = api_client.get("/api/brands/search", {"keyword": "test"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.django_db
def test_search_competitions(api_client, test_data):
    """Test competition search endpoint."""
    response = api_client.get("/api/competitions/search", {"keyword": "test"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.django_db
def test_search_seasons(api_client, test_data):
    """Test season search endpoint."""
    response = api_client.get("/api/seasons/search", {"keyword": "2024"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.django_db
def test_get_kit_json(api_client, test_data):
    """Test get kit details endpoint."""
    kit_id = test_data["kit"].id
    response = api_client.get(f"/api/kit-json/{kit_id}")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "team" in data
    assert "season" in data


@pytest.mark.django_db
def test_get_random_kits(api_client, test_data):
    """Test random kits endpoint with pagination."""
    response = api_client.get("/api/random-kits/", {"page": 1, "page_size": 20})
    assert response.status_code == 200
    data = response.json()
    assert "kits" in data
    assert "pagination" in data
    assert "current_page" in data["pagination"]


@pytest.mark.django_db
def test_get_random_clubs(api_client, test_data):
    """Test random clubs endpoint with pagination."""
    response = api_client.get("/api/random-clubs/", {"page": 1, "page_size": 20})
    assert response.status_code == 200
    data = response.json()
    assert "clubs" in data
    assert "pagination" in data


@pytest.mark.django_db
def test_get_merge_suggestions(api_client, test_data):
    """Test merge suggestions endpoint."""
    response = api_client.get("/api/merge-suggestions/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.django_db
def test_search_kits(api_client, test_data):
    """Test kit search endpoint."""
    response = api_client.get("/api/kits/search", {"keyword": "test"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
