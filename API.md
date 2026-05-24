# API Reference

All endpoints return `application/json`. Dates are ISO 8601 strings (`YYYY-MM-DD`). Timestamps are ISO 8601 with timezone offset.

---

## GET /property/\<address\>/

Retrieve violation history and scofflaw status for a property address.

**Request URL**
```
GET /property/7120 S ROCKWELL ST/
```

**Request Payload** — none

**Response Code** — `200 OK`

**Response Payload**
```
{
  "address":              string,
  "last_violation_date":  string | null,   // ISO date of most recent violation
  "total_violation_count": number,
  "violations": [
    {
      "date":               string,         // ISO date
      "code":               string | null,
      "status":             string | null,
      "description":        string | null,
      "inspector_comments": string | null
    }
  ],
  "SCOFFLAW": boolean
}
```

**Error Responses**

| Code | Body |
|------|------|
| 404  | `{"error": "Address not found"}` |

---

## POST /property/\<address\>/comments/

Post a comment about a property.

**Request URL**
```
POST /property/7120 S ROCKWELL ST/comments/
```

**Request Payload**
```
{
  "author":  string,   // required, max 200 chars
  "comment": string    // required, max 5000 chars
}
```

**Response Code** — `201 Created`

**Response Payload**
```
{
  "message":    string,
  "id":         number,
  "address":    string,
  "author":     string,
  "created_at": string    // ISO 8601 timestamp with timezone
}
```

**Error Responses**

| Code | Body |
|------|------|
| 400  | `{"error": "Request body must be valid JSON"}` |
| 400  | `{"error": "author cannot be empty"}` |
| 400  | `{"error": "author must be 200 characters or fewer"}` |
| 400  | `{"error": "comment cannot be empty"}` |
| 400  | `{"error": "comment must be 5000 characters or fewer"}` |

---

## GET /property/scofflaws/violations

Return distinct scofflaw addresses that have at least one violation on or after the given date.

**Request URL**
```
GET /property/scofflaws/violations?since=2024-01-01
```

**Request Payload** — none

**Query Parameters**

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| since     | string | yes      | ISO date (`YYYY-MM-DD`) — lower bound (inclusive) on violation date |

**Response Code** — `200 OK`

**Response Payload**
```
{
  "since":     string,    // echo of the since parameter
  "count":     number,    // number of matching addresses
  "addresses": [string]   // distinct normalized addresses, sorted alphabetically
}
```

**Error Responses**

| Code | Body |
|------|------|
| 400  | `{"error": "since query parameter is required (format: YYYY-MM-DD)"}` |
| 400  | `{"error": "since must be a valid date in YYYY-MM-DD format"}` |
| 400  | `{"error": "since must be a valid calendar date"}` |

---

## GET /health

Liveness probe.

**Response Code** — `200 OK`

**Response Payload**
```
{"status": "ok"}
```
