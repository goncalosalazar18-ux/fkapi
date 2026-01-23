# API Endpoint Catalog

Complete reference for all API endpoints in the Football Kit Archive API.

## Base URL

All endpoints are available at: `https://your-domain.com/api/`

## Authentication

API key authentication is optional and can be enabled by setting `DJANGO_API_ENABLE_AUTH=True`.
When enabled, include your API key in the request header:
```
X-API-Key: your-api-key-here
```

## Rate Limiting

The API is rate-limited to 100 requests per hour per IP address by default.
Rate limit can be configured via `API_RATE_LIMIT_RATE` environment variable.

## System Endpoints

### Health Check

**GET** `/api/health`

Check if the API and database are functioning correctly.

**Response:**
- `200 OK`: API and database are healthy
- `503 Service Unavailable`: Database connection failed

**Example Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "database": "connected"
}
```

### API Usage Metrics

**GET** `/api/metrics`

Get API usage statistics and performance metrics.

**Response:**
```json
{
  "total_requests": 1234,
  "requests_per_minute": 5.2,
  "average_response_time": 0.123,
  "endpoints": {
    "/api/health": {"count": 100, "avg_time": 0.01},
    "/api/kits": {"count": 500, "avg_time": 0.15}
  }
}
```

## Club Endpoints

### Search Clubs

**GET** `/api/clubs/search`

Search for clubs using a keyword. The search is performed on both club names and slugs using trigram word similarity.

**Query Parameters:**
- `keyword` (required): Keyword to search for in club names and slugs

**Response:** Array of `ClubSerializer` objects (max 10 results)

**Example:**
```
GET /api/clubs/search?keyword=manchester
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "Manchester United",
    "slug": "manchester-united",
    "logo": "https://...",
    "country": "GB"
  }
]
```

## Brand Endpoints

### Search Brands

**GET** `/api/brands/search`

Search for brands using a keyword.

**Query Parameters:**
- `keyword` (required): Keyword to search for in brand names or slugs

**Response:** Array of `BrandJsonSchema` objects (max 10 results)

**Example:**
```
GET /api/brands/search?keyword=adidas
```

## Competition Endpoints

### Search Competitions

**GET** `/api/competitions/search`

Search for competitions using a keyword.

**Query Parameters:**
- `keyword` (required): Keyword to search for in competition names or slugs

**Response:** Array of `CompetitionJsonSchema` objects (max 10 results)

**Example:**
```
GET /api/competitions/search?keyword=premier
```

## Season Endpoints

### Get Club Seasons

**GET** `/api/seasons`

Get all available seasons for a club.

**Query Parameters:**
- `id` (required): Club ID

**Response:** Array of `SeasonSerializer` objects

**Example:**
```
GET /api/seasons?id=1
```

### Search Seasons

**GET** `/api/seasons/search`

Search for seasons by year.

**Query Parameters:**
- `keyword` (required): Year or partial year to search for

**Response:** Array of `SeasonSerializer` objects

**Example:**
```
GET /api/seasons/search?keyword=2025
```

## Kit Endpoints

### Get Kits

**GET** `/api/kits`

Get kits for a specific club and season.

**Query Parameters:**
- `club` (required): Club ID
- `season` (required): Season ID

**Response:** Array of `KitSerializer` objects

**Example:**
```
GET /api/kits?club=1&season=1
```

### Get Kit Details

**GET** `/api/kit-json/{kit_id}`

Get detailed information for a specific kit.

**Path Parameters:**
- `kit_id` (required): Kit ID

**Response:** `KitJsonSchema` object

**Example:**
```
GET /api/kit-json/123
```

### Search Kits

**GET** `/api/kits/search`

Search for kits using a keyword and optionally a year.

**Query Parameters:**
- `keyword` (optional): Search query

**Response:** Array of `KitSearchResult` objects (max 10 results)

**Example:**
```
GET /api/kits/search?keyword=Málaga 2003
```

### Get Kits in Bulk

**GET** `/api/kits/bulk`

Retrieve multiple kits by their slugs or URLs in a single request. This endpoint is optimized for bulk operations and returns a reduced response format with only essential fields.

**Query Parameters:**
- `slugs` (required): Comma-separated list of kit slugs or full URLs
  - Minimum: 2 kits
  - Maximum: 30 kits

**Response:** Array of `KitBulkSchema` objects

**Example:**
```
GET /api/kits/bulk?slugs=manchester-united-2024-25-home-kit,liverpool-2024-25-away-kit
```

**Example with URLs:**
```
GET /api/kits/bulk?slugs=https://www.footballkitarchive.com/manchester-united-2024-25-home-kit,liverpool-2024-25-away-kit
```

**Response Format:**
```json
[
  {
    "name": "Manchester United 2024-25 Home Kit",
    "team": {
      "name": "Manchester United",
      "logo": "https://...",
      "logo_dark": "https://...",
      "country": "GB"
    },
    "season": {
      "year": "2024-25"
    },
    "brand": {
      "name": "Adidas",
      "logo": "https://...",
      "logo_dark": "https://..."
    },
    "main_img_url": "https://..."
  }
]
```

**Notes:**
- The endpoint accepts both slugs (e.g., `kit-slug-1`) and full URLs (e.g., `https://www.footballkitarchive.com/kit-slug-1`)
- URLs are automatically parsed to extract the slug
- Results are returned in the same order as the input slugs
- Missing kits are silently skipped (not included in the response)
- The response format is optimized for bulk operations and includes only essential fields

**Error Responses:**
- `400 Bad Request` or `422 Unprocessable Entity`: If less than 2 or more than 30 kits are requested
```json
{
  "detail": "Minimum 2 kits required"
}
```
or
```json
{
  "detail": "Maximum 30 kits allowed"
}
```

### Get Random Kits

**GET** `/api/random-kits/`

Get random kits with pagination.

**Query Parameters:**
- `page` (optional, default: 1): Page number (min: 1)
- `page_size` (optional, default: 20): Items per page (min: 1, max: 100)

**Response:**
```json
{
  "results": [...],
  "count": 1000,
  "page": 1,
  "page_size": 20,
  "total_pages": 50
}
```

### Get Random Clubs

**GET** `/api/random-clubs/`

Get random clubs with pagination.

**Query Parameters:**
- `page` (optional, default: 1): Page number (min: 1)
- `page_size` (optional, default: 20): Items per page (min: 1, max: 100)

**Response:**
```json
{
  "results": [...],
  "count": 500,
  "page": 1,
  "page_size": 20,
  "total_pages": 25
}
```

### Get Kit Details

**GET** `/api/kits/{kit_id}`

Get detailed information for a specific kit.

**Path Parameters:**
- `kit_id` (required): Kit ID

**Response:** `KitJsonSchema` object with complete kit information

**Example:**
```
GET /api/kits/1
```

**Response:**
```json
{
  "name": "Home Kit 2024-25",
  "slug": "manchester-united-2024-25-home-kit",
  "team": {
    "id": 1,
    "name": "Manchester United",
    "slug": "manchester-united",
    "logo": "https://...",
    "logo_dark": "https://...",
    "country": "GB"
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
      "logo": "https://...",
      "logo_dark": "https://...",
      "country": "GB"
    }
  ],
  "type": {
    "id": 1,
    "name": "Home",
    "category": "match",
    "category_order": 1,
    "order_priority": 1,
    "is_goalkeeper": false
  },
  "brand": {
    "id": 1,
    "name": "Adidas",
    "slug": "adidas-kits",
    "logo": "https://...",
    "logo_dark": "https://..."
  },
  "design": "Stripes",
  "primary_color": {
    "name": "Red",
    "color": "#FF0000"
  },
  "secondary_color": [
    {
      "name": "White",
      "color": "#FFFFFF"
    }
  ],
  "main_img_url": "https://..."
}
```

**Type_K Fields:**
- `id`: Unique identifier for the kit type
- `name`: Name of the kit type (e.g., "Home", "Away", "Training")
- `category`: Category of the kit type:
  - `match`: Game kits (default)
  - `prematch`: Pre-match, bench, warm-up, staff
  - `preseason`: Pre-season, temporary
  - `training`: Training kits
  - `travel`: Travel/Polo kits
  - `jacket`: Jackets (Anthem, Rain, Jacket, Windbreaker, Track, Vest)
- `category_order`: Order of category for sorting (1-6, lower = higher priority)
- `order_priority`: Priority within category for sorting (lower = higher priority)
- `is_goalkeeper`: Boolean indicating if this is a goalkeeper kit type

**Note:** When new kit types are created during scraping, they are automatically categorized based on their name.

### Get Kit (Legacy)

**GET** `/api/kit/{kit_id}`

Legacy endpoint for getting kit information. Returns JSON response. Redirects to `/api/kits/{kit_id}`.

**Path Parameters:**
- `kit_id` (required): Kit ID

**Response:** JSON object with kit details

### Send Kit to External API

**GET** `/api/send-kit/{kit_id}`

Send kit information to an external API endpoint.

**Path Parameters:**
- `kit_id` (required): Kit ID

**Response:**
```json
{
  "message": "Kit sent successfully",
  "response": {...}
}
```

## Admin Endpoints

### Get Merge Suggestions

**GET** `/api/merge-suggestions/`

Get suggestions for merging duplicate clubs.

**Response:** Array of merge suggestion objects

### Merge Clubs

**POST** `/api/merge-clubs/`

Merge two clubs together.

**Request Body:**
```json
{
  "source_id": 1,
  "target_id": 2
}
```

**Response:**
```json
{
  "message": "Clubs merged successfully",
  "merged_club_id": 2
}
```

## Error Responses

All error responses follow this format:

```json
{
  "detail": "Error message description"
}
```

### HTTP Status Codes

- `200 OK`: Successful request
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Missing or invalid API key (if authentication enabled)
- `403 Forbidden`: Rate limit exceeded
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service unavailable (e.g., database connection failed)

## Response Headers

All API responses include these headers:

- `X-API-Version`: API version (e.g., "v1")
- `X-Response-Time`: Response time in seconds (e.g., "0.123s")
- `X-Query-Count`: Number of database queries executed (if available)
