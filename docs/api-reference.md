# BAWT - API Reference

## Base URL

```
Development: http://localhost:5000/api
Production: https://api.bawt.kantar.com/api
```

---

## Authentication

> **Note:** Authentication is currently placeholder. Will integrate with enterprise SSO.

```http
Authorization: Bearer <token>
```

---

## Endpoints

### 1. Hierarchy

#### GET /hierarchy

Get the full Market → Brand → Sub-brand → Channel hierarchy and available weeks.

**Response:**
```json
{
  "success": true,
  "data": {
    "hierarchy": {
      "US": {
        "Brand A": {
          "All": ["Paid Social", "Display", "Search", "TV", "OOH"]
        },
        "Brand B": {
          "All": ["Paid Social", "Display", "Search"]
        }
      },
      "UK": {
        "Brand A": {
          "All": ["Paid Social", "Display", "Search", "TV"]
        }
      }
    },
    "weeks": ["2024-W52", "2024-W51", "2024-W50", "2024-W49", "2024-W48"]
  }
}
```

---

### 2. Response Curves

#### GET /response-curves

Get response curves filtered by market/brand.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| market | string | No | Filter by market (e.g., "US") |
| brand | string | No | Filter by brand (e.g., "Brand A") |
| sub_brand | string | No | Filter by sub-brand |

**Example:**
```
GET /response-curves?market=US&brand=Brand%20A
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "RC-US-A-PS",
      "market": "US",
      "brand": "Brand A",
      "sub_brand": "All",
      "channel": "Paid Social",
      "k": 300000,
      "s": 1.8,
      "max_response": 1000000,
      "adstock_rate": 0.3,
      "volume_coefficient": 1.2,
      "brand_lift_coefficient": 0.08,
      "model_date": "2024-11-01",
      "source": "database"
    }
  ]
}
```

#### POST /response-curves

Create or update a response curve.

**Request Body:**
```json
{
  "market": "US",
  "brand": "Brand A",
  "sub_brand": "All",
  "channel": "Paid Social",
  "k": 300000,
  "s": 1.8,
  "max_response": 1000000,
  "adstock_rate": 0.3,
  "volume_coefficient": 1.2,
  "brand_lift_coefficient": 0.08
}
```

**Response:**
```json
{
  "success": true,
  "id": "RC-ABC12345"
}
```

---

### 3. CPM Data

#### GET /cpms

Get CPM data filtered by criteria.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| market | string | No | Filter by market |
| brand | string | No | Filter by brand |
| week | string | No | Filter by week (e.g., "2024-W50") |

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "CPM-US-A-PS-2024-W50",
      "market": "US",
      "brand": "Brand A",
      "sub_brand": "All",
      "channel": "Paid Social",
      "week_start": "2024-W50",
      "cpm": 8.50,
      "min_spend": 50000,
      "max_spend": 500000
    }
  ]
}
```

#### POST /cpms

Create or update CPM data.

**Request Body:**
```json
{
  "market": "US",
  "brand": "Brand A",
  "channel": "Paid Social",
  "week_start": "2024-W50",
  "cpm": 8.50,
  "min_spend": 50000,
  "max_spend": 500000
}
```

---

### 4. Optimization

#### POST /optimize

Run marginal ROI optimization.

**Request Body:**
```json
{
  "market": "US",
  "brand": "Brand A",
  "week": "2024-W50",
  "total_budget": 1000000,
  "current_allocations": {
    "RC-US-A-PS": 200000,
    "RC-US-A-DI": 200000,
    "RC-US-A-SE": 200000,
    "RC-US-A-TV": 200000,
    "RC-US-A-OH": 200000
  },
  "constraints": {
    "RC-US-A-PS": {"min": 50000, "max": 500000},
    "RC-US-A-TV": {"min": 100000, "max": 800000}
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "allocations": {
      "RC-US-A-PS": {
        "curve_id": "RC-US-A-PS",
        "channel": "Paid Social",
        "current_spend": 200000,
        "optimized_spend": 215497,
        "change_amount": 15497,
        "change_pct": 7.7,
        "current_response": 350000,
        "optimized_response": 380000,
        "response_change_pct": 8.6,
        "marginal_roi": 0.0023,
        "roi": 1.76,
        "impressions": 25352941,
        "incr_volume": 456000,
        "brand_lift": 3.04
      }
    },
    "summary": {
      "total_budget": 1000000,
      "total_current_response": 2500000,
      "total_optimized_response": 2672500,
      "response_lift_pct": 6.9,
      "iterations": 29,
      "converged": true
    }
  }
}
```

---

### 5. Simulation

#### POST /simulate-mmm

Run simulation without optimization.

**Request Body:**
```json
{
  "market": "US",
  "brand": "Brand A",
  "week": "2024-W50",
  "allocations": {
    "RC-US-A-PS": 300000,
    "RC-US-A-DI": 150000,
    "RC-US-A-SE": 250000
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "results": {
      "RC-US-A-PS": {
        "curve_id": "RC-US-A-PS",
        "channel": "Paid Social",
        "spend": 300000,
        "response": 500000,
        "marginal_roi": 0.0018,
        "roi": 1.67,
        "impressions": 35294118,
        "incr_volume": 600000,
        "brand_lift": 4.0
      }
    },
    "summary": {
      "total_spend": 700000,
      "total_response": 1200000
    }
  }
}
```

---

### 6. File Upload

#### POST /upload/curves

Upload response curves from CSV.

**Request:**
- Content-Type: `multipart/form-data`
- Field: `file` (CSV file)

**CSV Format:**
```csv
market,brand,sub_brand,channel,k,s,max_response,adstock_rate,volume_coefficient,brand_lift_coefficient
US,Brand A,All,Paid Social,300000,1.8,1000000,0.3,1.2,0.08
```

**Response:**
```json
{
  "success": true,
  "imported": 5,
  "errors": []
}
```

#### POST /upload/cpms

Upload CPM data from CSV.

**CSV Format:**
```csv
market,brand,channel,week_start,cpm,min_spend,max_spend
US,Brand A,Paid Social,2024-W50,8.50,50000,500000
```

---

### 7. Results Management

#### GET /results

Get all saved results.

#### POST /results

Save a new result.

#### DELETE /results/{id}

Delete a result.

---

## Error Responses

All errors follow this format:

```json
{
  "success": false,
  "error": "Error message description"
}
```

**HTTP Status Codes:**
| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request (invalid input) |
| 401 | Unauthorized |
| 404 | Not Found |
| 500 | Server Error |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| GET endpoints | 100/minute |
| POST endpoints | 30/minute |
| File uploads | 10/minute |
