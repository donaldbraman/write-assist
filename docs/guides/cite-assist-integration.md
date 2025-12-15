# cite-assist Integration Guide

**Version:** 1.1.0
**Last Updated:** 2025-12-15
**Status:** Implemented

## Overview

write-assist integrates with cite-assist to query the local citation database during drafting. This allows drafter agents to find relevant scholarship without relying solely on web searches.

## Integration Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  write-assist   │────▶│   cite-assist   │────▶│     Qdrant      │
│    Pipeline     │     │   v3 Search API │     │  Vector Store   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │
        ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│  Drafter Agent  │     │     Zotero      │
│  (with citations)│     │  (metadata)     │
└─────────────────┘     └─────────────────┘
```

## Prerequisites

1. **cite-assist running locally**
   - Qdrant container active
   - Library synced and embedded

2. **Network access**
   - cite-assist API endpoint accessible
   - Default: `http://localhost:8000`

## API Integration

### v3 Search Endpoint

```
POST /api/v3/search
```

**Request:**
```json
{
  "query": "prosecutor discretion charging decisions",
  "library_id": 5673253,
  "max_results": 10,
  "min_score": 0.3,
  "output_mode": "chunks"
}
```

**Response:**
```json
{
  "results": [
    {
      "id": "SCC7P3FV",
      "title": "The Prosecutor's Discretion",
      "result_type": "chunk",
      "score": 0.85,
      "chunk_text": "Prosecutorial discretion allows...",
      "chunk_index": 5,
      "authors": ["Smith, John", "Doe, Jane"],
      "year": 2020,
      "journal": "Harvard Law Review",
      "volume": "100",
      "pages": "1-50"
    }
  ],
  "total": 45,
  "query_time_ms": 372
}
```

## Usage

### Python Client

```python
from write_assist.citations import CiteAssistClient, CiteAssistUnavailable

async with CiteAssistClient() as client:
    # Search for citations
    response = await client.search(
        query="prosecutorial discretion",
        max_results=10,
        min_score=0.3,
        output_mode="chunks"
    )

    for result in response.results:
        print(f"{result.title} (score: {result.score})")
        print(f"  {result.to_bluebook()}")
```

### Pipeline Integration

The `WritingPipeline` automatically queries cite-assist before drafting:

```python
from write_assist.pipeline import WritingPipeline

# Create pipeline with cite-assist enabled (default)
pipeline = WritingPipeline(
    cite_assist_url="http://localhost:8000",
    cite_assist_library_id=5673253,
    use_cite_assist=True  # default
)

# Run pipeline - citations fetched automatically
result = await pipeline.run(
    topic="The doctrine of consideration",
    document_type="article",
    section_outline="1. Introduction\n2. History\n3. Conclusion"
)
```

### Disabling cite-assist

```python
# Disable cite-assist queries
pipeline = WritingPipeline(use_cite_assist=False)
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CITE_ASSIST_URL` | API base URL | `http://localhost:8000` |
| `CITE_ASSIST_LIBRARY_ID` | Zotero library ID | `5673253` |

### Python Configuration

```python
from write_assist.citations import CiteAssistClient

client = CiteAssistClient(
    base_url="http://localhost:8000",
    library_id=5673253,
    timeout=30.0,
)
```

## Fallback Behavior

If cite-assist is unavailable:

1. Log warning
2. Continue with empty citations list
3. Pipeline proceeds without local citations

```python
# Safe search that never raises
response = await client.search_safe("query")  # Returns empty on failure

# Health check
is_available = await client.health_check()
```

## Data Models

### CitationResult

```python
from write_assist.citations import CitationResult

result = CitationResult(
    id="SCC7P3FV",
    title="The Test Article",
    result_type="chunk",
    score=0.85,
    chunk_text="...",
    authors=["John Smith"],
    year=2020,
    journal="Harvard Law Review",
    volume="100",
    pages="1-50",
)

# Format in Bluebook style
print(result.to_bluebook())
# John Smith, *The Test Article*, 100 Harvard Law Review 1-50 (2020).

# Get relevant text
print(result.relevant_text)  # chunk_text or summary
```

### LocalCitation (for Drafter)

```python
from write_assist.agents.models import LocalCitation

citation = LocalCitation(
    id="SCC7P3FV",
    title="The Test Article",
    authors=["John Smith"],
    year=2020,
    journal="Harvard Law Review",
    volume="100",
    pages="1-50",
    relevance_score=0.85,
    relevant_text="..."
)
```

## Future Enhancements

- [x] Implement API client
- [x] Add graceful fallback
- [ ] Add caching layer for repeated queries
- [ ] Support batch queries for efficiency
- [ ] Add citation verification endpoint
- [ ] Integrate PDF retrieval for full-text search

## Related Documentation

- [cite-assist CLAUDE.md](https://github.com/donaldbraman/cite-assist/blob/main/CLAUDE.md)
- [cite-assist pin-citer integration](https://github.com/donaldbraman/cite-assist/blob/main/docs/guides/pin-citer-integration.md)

---

*Integration with cite-assist enables research-grounded drafting.*
