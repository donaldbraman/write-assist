# cite-assist Integration Guide

**Version:** 1.0.0
**Last Updated:** 2025-12-15
**Status:** Stub - implementation pending

## Overview

write-assist integrates with cite-assist to query the local citation database during drafting. This allows drafter agents to find relevant scholarship without relying solely on web searches.

## Integration Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  write-assist   │────▶│   cite-assist   │────▶│     Qdrant      │
│  Drafter Agent  │     │   Search API    │     │  Vector Store   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │     Zotero      │
                        │  (metadata)     │
                        └─────────────────┘
```

## Prerequisites

1. **cite-assist running locally**
   - Qdrant container active
   - Library synced and embedded

2. **Network access**
   - cite-assist API endpoint accessible
   - Default: `http://localhost:8000`

## Planned API Endpoints

### Search Citations

```
POST /api/v1/search
```

**Request:**
```json
{
  "query": "prosecutor discretion charging decisions",
  "limit": 10,
  "filters": {
    "year_min": 2010,
    "year_max": 2024,
    "item_types": ["journalArticle", "book"]
  }
}
```

**Response:**
```json
{
  "results": [
    {
      "id": "zotero://select/items/ABC123",
      "title": "The Prosecutor's Discretion",
      "authors": ["Smith, John", "Doe, Jane"],
      "year": 2020,
      "journal": "Harvard Law Review",
      "volume": 100,
      "pages": "1-50",
      "abstract": "This article examines...",
      "relevance_score": 0.89,
      "citation_bluebook": "John Smith & Jane Doe, *The Prosecutor's Discretion*, 100 Harv. L. Rev. 1 (2020)."
    }
  ],
  "total": 45,
  "query_time_ms": 120
}
```

### Get Citation by ID

```
GET /api/v1/citation/{zotero_id}
```

**Response:**
```json
{
  "id": "zotero://select/items/ABC123",
  "metadata": { ... },
  "citation_formats": {
    "bluebook_full": "...",
    "bluebook_short": "...",
    "chicago": "..."
  }
}
```

## Usage in Drafter Agent

```python
# Pseudocode for drafter agent integration

async def research_topic(topic: str) -> list[Citation]:
    """Query cite-assist for relevant citations."""

    # Search local database
    results = await cite_assist_client.search(
        query=topic,
        limit=20,
        filters={"year_min": 2000}
    )

    # Filter to most relevant
    relevant = [r for r in results if r.relevance_score > 0.7]

    # Return formatted citations
    return [
        Citation(
            id=r.id,
            full=r.citation_bluebook,
            short=generate_short_form(r),
            abstract=r.abstract
        )
        for r in relevant
    ]
```

## Configuration

```python
# src/write_assist/config.py

CITE_ASSIST_CONFIG = {
    "base_url": "http://localhost:8000",
    "timeout": 30,
    "default_limit": 10,
    "min_relevance": 0.5,
}
```

## Fallback Behavior

If cite-assist is unavailable:

1. Log warning
2. Continue with web-only research
3. Note in output that local database was not queried

```python
try:
    local_results = await cite_assist_client.search(query)
except CiteAssistUnavailable:
    logger.warning("cite-assist unavailable, using web-only research")
    local_results = []
```

## Future Enhancements

- [ ] Implement actual API client
- [ ] Add caching layer for repeated queries
- [ ] Support batch queries for efficiency
- [ ] Add citation verification endpoint
- [ ] Integrate PDF retrieval for full-text search

## Related Documentation

- [cite-assist CLAUDE.md](https://github.com/donaldbraman/cite-assist/blob/main/CLAUDE.md)
- [cite-assist API documentation](https://github.com/donaldbraman/cite-assist/blob/main/docs/api.md) (when available)

---

*Integration with cite-assist enables research-grounded drafting.*
