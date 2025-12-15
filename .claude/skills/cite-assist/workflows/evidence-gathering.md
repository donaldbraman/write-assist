# Evidence Gathering Workflow

**Purpose:** Find specific passages that support arguments or claims.

## When to Use

- Need quotable text for a specific claim
- Looking for empirical evidence
- Building support for an argument
- Seeking authoritative statements

## Steps

### 1. Formulate Targeted Query

Be specific about what you need:
- Include the claim or argument direction
- Use key terminology from the field
- Frame as a searchable proposition

**Examples:**
- Good: "prosecutorial discretion reduces racial disparities evidence"
- Too vague: "prosecutors and race"
- Too narrow: "Krasner reduced Black incarceration by 40%"

### 2. Execute Chunks-Mode Search

```json
{
  "query": "your specific claim or topic",
  "output_mode": "chunks",
  "max_results": 10,
  "min_score": 0.4
}
```

Use higher `min_score` (0.4-0.6) for precision.

### 3. Evaluate Results

For each chunk, assess:
- **Relevance:** Does it actually support the claim?
- **Authority:** Is the source credible?
- **Quotability:** Is the passage well-written?
- **Context:** Does the surrounding text change meaning?

### 4. Verify Context

For promising chunks, consider:
- Requesting `both` mode to see document summary
- Reading surrounding chunks (adjust `chunk_index`)
- Checking if quote is author's view or someone they're critiquing

### 5. Format Citations

Use the Academic Bluebook skill to format:
```
See `.claude/skills/academic-bluebook/SKILL.md`
```

Basic pattern:
```
Author, *Title*, Vol. J. Abbr. Page, Pin (Year).
```

### 6. Document Evidence

Create evidence cards:
```
Claim: [What you're supporting]
Source: [Full citation]
Quote: "[Exact text from chunk]"
Page: [Chunk index → approximate page]
Strength: [Direct/Indirect support]
Notes: [Any caveats or context]
```

## Example

**Claim:** Progressive prosecution reduces incarceration without increasing crime

**Query:** "progressive prosecution crime rates incarceration outcomes"

**Result:**
```json
{
  "title": "Progressive Prosecution at Work",
  "chunk_text": "Philadelphia's progressive policies resulted in a 22% reduction in incarceration with no statistically significant change in violent crime rates...",
  "score": 0.78
}
```

**Evidence Card:**
```
Claim: Progressive prosecution reduces incarceration without increasing crime
Source: Smith, *Progressive Prosecution at Work*, 100 Harv. L. Rev. 1, 45 (2023).
Quote: "Philadelphia's progressive policies resulted in a 22% reduction..."
Strength: Direct empirical support
Notes: Philadelphia-specific; may need additional jurisdictions
```

## Tips

- Higher `min_score` = more relevant but fewer results
- Search for counter-arguments too (strengthens your argument)
- Verify quotes exactly—don't paraphrase when citing
- Note chunk_index for locating in original document
- Consider searching related terms if initial results thin

## Common Pitfalls

1. **Confirmation bias:** Don't ignore contrary evidence
2. **Out of context:** Verify chunk meaning in document context
3. **Stale sources:** Check publication year for currency
4. **Misattribution:** Ensure author endorses the view, not just reports it

---

*Evidence gathering builds the foundation for persuasive arguments.*
