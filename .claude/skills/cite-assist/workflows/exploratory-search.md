# Exploratory Search Workflow

**Purpose:** Initial research on a topic to understand available sources and key themes.

## When to Use

- Starting research on a new topic
- Unsure what sources exist in the library
- Need to map the landscape before diving deep

## Steps

### 1. Formulate Initial Query

Start with a broad, conceptual query:
- Good: "criminal justice reform"
- Too narrow: "Larry Krasner's 2018 policy on drug offenses"

### 2. Execute Auto-Mode Search

```json
{
  "query": "your broad topic",
  "output_mode": "auto",
  "max_results": 15,
  "min_score": 0.25
}
```

Use lower `min_score` (0.25) to cast a wider net initially.

### 3. Review Results

Examine the results for:
- **Themes:** What subtopics emerge?
- **Authors:** Who writes about this topic?
- **Relevance:** Which results are most on-point?

### 4. Identify Follow-up Queries

Based on results, generate targeted queries:
- Subtopic queries for specific themes
- Author-focused queries
- Methodology queries (empirical, theoretical)

### 5. Document Findings

Create a brief map:
```
Topic: [Your Topic]
Key Sources:
- [Title 1] - [One-sentence summary]
- [Title 2] - [One-sentence summary]

Subtopics to Explore:
- [Subtopic 1]
- [Subtopic 2]

Potential Gaps:
- [What's missing from the literature]
```

## Example

**Query:** "prosecutorial discretion"

**Results reveal:**
- Progressive prosecution movement
- Racial disparities in charging
- Plea bargaining dynamics
- Historical development

**Follow-up queries:**
1. "progressive prosecutor reform outcomes"
2. "racial disparity charging decisions"
3. "plea bargaining coercion defendants"

## Tips

- Don't over-filter initially—breadth helps discovery
- Note surprising results—they may reveal connections
- Track document IDs for later retrieval
- Consider both chunks and summaries in auto mode results

---

*Exploratory search maps the research landscape.*
