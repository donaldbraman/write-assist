# Literature Review Workflow

**Purpose:** Map the scholarly landscape on a topic by analyzing document-level coverage.

## When to Use

- Writing a literature review section
- Understanding scholarly debate structure
- Identifying gaps in the literature
- Finding seminal works on a topic

## Steps

### 1. Define Review Scope

Determine:
- **Topic boundaries:** What's in/out of scope?
- **Time period:** Recent only or historical development?
- **Methodological focus:** Empirical, theoretical, doctrinal?

### 2. Execute Summaries-Mode Search

```json
{
  "query": "your topic area",
  "output_mode": "summaries",
  "max_results": 20,
  "min_score": 0.3,
  "weights": {"chunk": 0.2, "summary": 0.8}
}
```

Shift weights toward summaries for document-level matching.

### 3. Categorize Results

Group documents by:
- **Approach:** Empirical vs. theoretical vs. doctrinal
- **Position:** Supporting vs. critiquing vs. neutral
- **Focus:** Specific subtopics addressed
- **Era:** Historical development

### 4. Identify Scholarly Conversation

Map the debate:
```
Topic: [Your Topic]

Position A: [Description]
- [Author 1] argues...
- [Author 2] extends...

Position B: [Description]
- [Author 3] counters...
- [Author 4] proposes...

Emerging Synthesis:
- [Author 5] reconciles...
```

### 5. Find Gaps

Look for:
- Unanswered questions in summaries
- Missing methodological approaches
- Underexplored contexts or populations
- Opportunities for your contribution

### 6. Deep Dive Key Sources

For seminal works, use `both` mode:
```json
{
  "query": "specific document topic",
  "output_mode": "both",
  "max_results": 5
}
```

Get both summary context and specific passages.

## Example

**Topic:** Prosecutorial discretion and racial equity

**Search:**
```json
{
  "query": "prosecutorial discretion racial disparities criminal justice",
  "output_mode": "summaries",
  "max_results": 25,
  "weights": {"chunk": 0.2, "summary": 0.8}
}
```

**Categorization:**

| Category | Works |
|----------|-------|
| Empirical studies | Davis (2007), Rehavi & Starr (2014) |
| Theoretical frameworks | Barkow (2019), Pfaff (2017) |
| Reform proposals | Sklansky (2018), Bellin (2019) |
| Critical perspectives | Butler (2017), Alexander (2010) |

**Scholarly Conversation:**
```
Traditional view: Discretion is necessary for individualized justice
Critique: Discretion enables racial bias (Davis, Butler)
Reform: Progressive prosecution movement (Sklansky)
Skepticism: Structural limits on reform (Pfaff)
```

**Gap Identified:** Limited empirical study of progressive prosecution outcomes

## Output Format

Structure your literature review:

```markdown
## Literature Review

### The Discretion Debate
The scholarly conversation on prosecutorial discretion...

### Empirical Evidence
Studies examining outcomes show...

### Reform Movements
Recent scholarship proposes...

### Gaps and This Article's Contribution
The literature has not adequately addressed...
```

## Tips

- Start broad, then narrow based on findings
- Track which documents you've fully reviewed vs. skimmed
- Note relationships between authors (responses, extensions)
- Consider publication venue (law review prestige, interdisciplinary)
- Update your map as you learn more

## Integration with Writing

Feed findings to the drafter agent:
- Key sources with summaries
- Scholarly positions mapped
- Gaps identified for framing contribution

---

*Literature review situates your work in scholarly conversation.*
