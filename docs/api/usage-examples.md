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

# Get kits in bulk by slugs
response = requests.get(
    f"{BASE_URL}/kits/bulk",
    params={"slugs": "manchester-united-2024-25-home-kit,liverpool-2024-25-away-kit"},
    headers=headers
)
kits = response.json()
print(kits)

# Get kits in bulk with mixed slugs and URLs
response = requests.get(
    f"{BASE_URL}/kits/bulk",
    params={"slugs": "https://www.footballkitarchive.com/manchester-united-2024-25-home-kit,liverpool-2024-25-away-kit"},
    headers=headers
)
kits = response.json()
print(kits)

# Scrape user collection
userid = 148184
response = requests.post(
    f"{BASE_URL}/user-collection/{userid}/scrape",
    headers=headers
)
result = response.json()
print(result)

# If status is "processing", wait ~60 seconds, then get the collection
if result.get("status") == "processing":
    import time
    time.sleep(60)
    
    # Get user collection with pagination
    response = requests.get(
        f"{BASE_URL}/user-collection/{userid}",
        params={"page": 1, "page_size": 20},
        headers=headers
    )
    collection = response.json()
    print(collection)
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

// Get kits in bulk
async function getKitsBulk(slugs) {
    const response = await fetch(
        `${BASE_URL}/kits/bulk?slugs=${encodeURIComponent(slugs)}`,
        { headers }
    );
    const kits = await response.json();
    console.log(kits);
    return kits;
}

// Scrape user collection
async function scrapeUserCollection(userid) {
    const response = await fetch(
        `${BASE_URL}/user-collection/${userid}/scrape`,
        { method: 'POST', headers }
    );
    const result = await response.json();
    console.log(result);
    return result;
}

// Get user collection
async function getUserCollection(userid, page = 1, pageSize = 20) {
    const response = await fetch(
        `${BASE_URL}/user-collection/${userid}?page=${page}&page_size=${pageSize}`,
        { headers }
    );
    const collection = await response.json();
    console.log(collection);
    return collection;
}

// Usage
searchClubs('manchester');
getRandomKits(1, 20);
getKitDetails(1);
getKitsBulk('manchester-united-2024-25-home-kit,liverpool-2024-25-away-kit');

// Scrape and get user collection
const userid = 148184;
scrapeUserCollection(userid).then(result => {
    if (result.status === 'processing') {
        // Wait 60 seconds, then get collection
        setTimeout(() => {
            getUserCollection(userid, 1, 20);
        }, 60000);
    }
});
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

# Scrape user collection
USERID=148184
curl -X POST "${BASE_URL}/user-collection/${USERID}/scrape" \
  -H "X-API-Key: ${API_KEY}"

# Get user collection with pagination (wait ~60 seconds after scraping)
curl -X GET "${BASE_URL}/user-collection/${USERID}?page=1&page_size=20" \
  -H "X-API-Key: ${API_KEY}"
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

### Bulk Kits Response

```json
[
    {
        "name": "Manchester United 2024-25 Home Kit",
        "team": {
            "name": "Manchester United",
            "logo": "https://www.footballkitarchive.com/...",
            "logo_dark": "https://www.footballkitarchive.com/...",
            "country": "GB"
        },
        "season": {
            "year": "2024-25"
        },
        "brand": {
            "name": "Adidas",
            "logo": "https://www.footballkitarchive.com/...",
            "logo_dark": "https://www.footballkitarchive.com/..."
        },
        "main_img_url": "https://www.footballkitarchive.com/..."
    },
    {
        "name": "Liverpool 2024-25 Away Kit",
        "team": {
            "name": "Liverpool",
            "logo": "https://www.footballkitarchive.com/...",
            "logo_dark": "https://www.footballkitarchive.com/...",
            "country": "GB"
        },
        "season": {
            "year": "2024-25"
        },
        "brand": {
            "name": "Nike",
            "logo": "https://www.footballkitarchive.com/...",
            "logo_dark": "https://www.footballkitarchive.com/..."
        },
        "main_img_url": "https://www.footballkitarchive.com/..."
    }
]
```

### User Collection Scrape Response (202 Accepted)

```json
{
    "status": "processing",
    "task_id": "abc123-def456-ghi789",
    "message": "Scraping started. Check status in 60 seconds by calling GET /api/user-collection/148184"
}
```

### User Collection Response (200 OK)

```json
{
    "status": "ready",
    "data": {
        "success": true,
        "entries": [
            {
                "kit_id": 12345,
                "kit_name": "Manchester United 2024-25 Home Kit",
                "kit_slug": "manchester-united-2024-25-home-kit",
                "team_name": "Manchester United",
                "season_year": "2024-25",
                "main_img_url": "https://www.footballkitarchive.com/..."
            }
        ],
        "total_entries": 150,
        "pages_scraped": 8
    },
    "pagination": {
        "current_page": 1,
        "total_pages": 8,
        "total_count": 150,
        "page_size": 20,
        "has_next": true,
        "has_previous": false,
        "next_page": 2,
        "previous_page": null
    },
    "cached_until": "2026-02-02T12:00:00"
}
```

### User Collection Not Found Response (404 Not Found)

```json
{
    "status": "not_found",
    "message": "Collection not found for userid 148184. Call POST /api/user-collection/148184/scrape first to start scraping."
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
