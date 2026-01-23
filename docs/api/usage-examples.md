# API Usage Examples

This document provides code examples for using the Football Kit Archive API in different programming languages.

## Base URL

All API endpoints are available at: `https://your-domain.com/api/`

## Authentication

If API key authentication is enabled, include your API key in the request header:

```
X-API-Key: your-api-key-here
```

## Rate Limiting

The API is rate-limited to 100 requests per hour per IP address by default. When the rate limit is exceeded, you will receive a `403 Forbidden` response.

## Error Handling

All error responses follow this format:

```json
{
    "detail": "Error message description"
}
```

## Examples

### Python

```python
import requests

BASE_URL = "https://your-domain.com/api"
API_KEY = "your-api-key-here"  # Optional, only if authentication is enabled

headers = {}
if API_KEY:
    headers["X-API-Key"] = API_KEY

# Search for clubs
response = requests.get(
    f"{BASE_URL}/clubs/search",
    params={"keyword": "manchester"},
    headers=headers
)
clubs = response.json()
print(clubs)

# Get random kits with pagination
response = requests.get(
    f"{BASE_URL}/random-kits/",
    params={"page": 1, "page_size": 20},
    headers=headers
)
kits = response.json()
print(kits)

# Get kit details by ID
response = requests.get(
    f"{BASE_URL}/kits/1",
    headers=headers
)
kit = response.json()
print(kit)
# Kit type now includes: id, name, category, category_order, order_priority, is_goalkeeper
print(f"Kit type: {kit['type']['name']} (Category: {kit['type']['category']})")

# Search seasons
response = requests.get(
    f"{BASE_URL}/seasons/search",
    params={"keyword": "2025"},
    headers=headers
)
seasons = response.json()
print(seasons)
```

### JavaScript (Fetch API)

```javascript
const BASE_URL = 'https://your-domain.com/api';
const API_KEY = 'your-api-key-here'; // Optional, only if authentication is enabled

const headers = {
    'Content-Type': 'application/json',
};
if (API_KEY) {
    headers['X-API-Key'] = API_KEY;
}

// Search for clubs
async function searchClubs(keyword) {
    const response = await fetch(
        `${BASE_URL}/clubs/search?keyword=${encodeURIComponent(keyword)}`,
        { headers }
    );
    const clubs = await response.json();
    console.log(clubs);
    return clubs;
}

// Get random kits with pagination
async function getRandomKits(page = 1, pageSize = 20) {
    const response = await fetch(
        `${BASE_URL}/random-kits/?page=${page}&page_size=${pageSize}`,
        { headers }
    );
    const kits = await response.json();
    console.log(kits);
    return kits;
}

// Get kit details by ID
async function getKitDetails(kitId) {
    const response = await fetch(
        `${BASE_URL}/kit-json/${kitId}`,
        { headers }
    );
    const kit = await response.json();
    console.log(kit);
    return kit;
}

// Usage
searchClubs('manchester');
getRandomKits(1, 20);
getKitDetails(1);
```

### cURL

```bash
# Base URL
BASE_URL="https://your-domain.com/api"
API_KEY="your-api-key-here"  # Optional, only if authentication is enabled

# Search for clubs
curl -X GET "${BASE_URL}/clubs/search?keyword=manchester" \
  -H "X-API-Key: ${API_KEY}"

# Get random kits with pagination
curl -X GET "${BASE_URL}/random-kits/?page=1&page_size=20" \
  -H "X-API-Key: ${API_KEY}"

# Get kit details by ID
curl -X GET "${BASE_URL}/kit-json/1" \
  -H "X-API-Key: ${API_KEY}"

# Search seasons
curl -X GET "${BASE_URL}/seasons/search?keyword=2025" \
  -H "X-API-Key: ${API_KEY}"

# Get merge suggestions
curl -X GET "${BASE_URL}/merge-suggestions/" \
  -H "X-API-Key: ${API_KEY}"

# Merge clubs (POST request)
curl -X POST "${BASE_URL}/merge-clubs/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "source_id": 1,
    "target_id": 2
  }'
```

## Response Examples

### Club Search Response

```json
[
    {
        "id": 1,
        "name": "Manchester United",
        "slug": "manchester-united-kits",
        "logo": "https://www.footballkitarchive.com/static/logos/manchester-united.png",
        "logo_dark": "https://www.footballkitarchive.com/static/logos/manchester-united-dark.png",
        "country": "GB"
    }
]
```

### Random Kits Response

```json
{
    "count": 1000,
    "next": "https://your-domain.com/api/random-kits/?page=2",
    "previous": null,
    "results": [
        {
            "id": 1,
            "name": "Manchester United 2024-25 Home Kit",
            "main_img_url": "https://www.footballkitarchive.com/...",
            "team_name": "Manchester United",
            "season_year": "2024-25"
        }
    ]
}
```

### Kit Details Response

```json
{
    "name": "Manchester United 2024-25 Home Kit",
    "slug": "manchester-united-2024-25-home-kit",
    "team": {
        "id": 1,
        "name": "Manchester United",
        "slug": "manchester-united-kits",
        "logo": "https://www.footballkitarchive.com/...",
        "logo_dark": "https://www.footballkitarchive.com/...",
        "country": "GB",
        "country_name": "United Kingdom"
    },
    "season": {
        "id": 1,
        "year": "2024-25",
        "first_year": "2024",
        "second_year": "2025"
    },
    "competition": [
        {
            "id": 1,
            "name": "Premier League",
            "slug": "premier-league-kits",
            "logo": "https://www.footballkitarchive.com/..."
        }
    ],
    "type": {
        "id": 1,
        "name": "Home"
    },
    "brand": {
        "id": 1,
        "name": "Adidas",
        "slug": "adidas-kits",
        "logo": "https://www.footballkitarchive.com/..."
    },
    "design": "Classic red with white trim",
    "primary_color": {
        "name": "Red",
        "color": "#DA020E"
    },
    "secondary_color": [
        {
            "name": "White",
            "color": "#FFFFFF"
        }
    ],
    "main_img_url": "https://www.footballkitarchive.com/..."
}
```

## Error Response Examples

### 400 Bad Request

```json
{
    "detail": "Invalid request parameters"
}
```

### 401 Unauthorized

```json
{
    "detail": "Invalid or missing API key"
}
```

### 403 Forbidden (Rate Limit)

```json
{
    "detail": "Rate limit exceeded. Please try again later."
}
```

### 404 Not Found

```json
{
    "detail": "Kit not found"
}
```

### 500 Internal Server Error

```json
{
    "detail": "An error occurred processing your request"
}
```
