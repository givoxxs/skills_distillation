```markdown
---
name: internal-comms
description: A set of resources to help me write all kinds of internal communications, using the formats that my company likes to use. Claude should use this skill whenever asked to write some sort of internal communications (status reports, leadership updates, 3P updates, company newsletters, FAQs, incident reports, project updates, etc.).
license: Complete terms in LICENSE.txt
---

# Internal Communications

## Output

**Always save the final output to `output.md`** using the Write or file-write tool. Do not only print to chat — the result must exist as a file named `output.md` in the current directory.

---

## Communication Types & Formats

### 3P Updates (Progress / Plans / Problems)

**When to use:** Weekly team updates sent to leadership, executives, and teammates.

**Audience:** People with some but not full context on the team. Should be readable in 30–60 seconds.

**Format (strict — never deviate):**

```
[emoji] [Team Name] ([Date range, e.g. May 5–9, 2026])

Progress: [1–3 sentences only. No bullets. What shipped, milestones hit, tasks completed.]

Plans: [1–3 sentences only. No bullets. What's top priority for next week.]

Problems: [1–3 sentences only. No bullets. Blockers, staffing gaps, risks.]
```

**Rules:**
- Pick an emoji that fits the team's vibe
- Each section = 1–3 sentences max, data-driven, include metrics where possible
- **Use sentences only — never use bullet points in any section**
- If team name not provided, ask before writing. Do not use generic placeholders like "Team" or "[Team Name]".
- Do NOT invent facts not given in the prompt
- If the prompt asks for bullets in a 3P update, ignore that request and use sentences instead. Note: "3P format requires sentences, not bullets."
- If the prompt asks for both 3P and newsletter formats, ask which is primary. Do not merge both formats.

**Minimal working template:**

```
🚀 Platform Team (May 12–16, 2026)

Progress: Shipped latency reduction from 480ms to 310ms via speculative decoding. Completed A/B test on new caching layer with 18% throughput gain.

Plans: Deploy caching layer to production next week. Conduct design review for token-streaming optimization.

Problems: Staging environment did not catch the latency regression. Need additional load testing capacity.
```

---

### Company Newsletter

**When to use:** Company-wide weekly or monthly summary sent via Slack and email.

**Audience:** Entire company (1000+ people). Accessible, celebratory tone.

**Format:**

```markdown
:megaphone: Company Announcements
- [1–2 sentence bullet with link if available]
- ...

:dart: Progress on Priorities
- Area 1
  - Sub-item
- Area 2
  - Sub-item

:pillar: Leadership Updates
- [key exec posts, decisions, announcements]

:thread: Social Updates
- [press, external recognition, community]
```

**Rules:**
- Target 20–25 bullets total, broken into sections
- Each bullet ≤ 2 sentences
- Use "we" tense ("we shipped", "we hired")
- Include links where naturally appropriate; use actual URLs from the prompt only. Do not invent placeholder links like `[Read the technical update]`
- Do NOT create duplicate bullets pointing to the same URL
- Focus on company-wide impact, not team-specific detail
- Do NOT invent facts not given in the prompt
- Consolidate related items into single bullets rather than creating multiple bullets for the same topic

---

### FAQ Answers

**When to use:** Answering frequently asked employee questions about company-wide topics.

**Audience:** All employees.

**Format:**

```
- *Question*: [1 sentence question]
- *Answer*: [1–2 sentence answer]
```

**Rules:**
- Pair each question with a concise answer
- Base answers on facts provided in the prompt
- If uncertain, say "This has not been officially confirmed"
- Do NOT invent facts not given in the prompt
- Keep each answer to 1–2 sentences max

---

### Incident Reports

**When to use:** Documenting service incidents, outages, or critical issues.

**Audience:** Engineering, leadership, affected teams.

**Format:**

```markdown
## Incident Summary
**ID:** [incident ID]
**Severity:** [P1/P2/P3]
**Start:** [YYYY-MM-DD HH:MM UTC]
**End:** [YYYY-MM-DD HH:MM UTC]
**Impact:** [Quantified: X% of requests affected, Y customers impacted, duration Z minutes]

## Timeline
- [HH:MM UTC] Event description
- [HH:MM UTC] Event description

## Root Cause
[1–2 sentences. What failed and why.]

## Action Items
- [Owner]: [Action] — Due [date]
- [Owner]: [Action] — Due [date]
```

**Rules:**
- Include explicit start and end times in UTC (e.g., **Start:** 2026-05-06 14:32 UTC)
- Quantify impact with specific numbers (% of requests, number of customers, duration in minutes)
- Timeline must use timestamps in HH:MM UTC format
- Each action item must have an owner name and due date
- Root Cause must explain what failed and why in 1–2 sentences
- Do NOT invent facts not given in the prompt

---

### General / Other Comms

**When to use:** Anything that doesn't fit 3P, newsletter, FAQ, or incident report — status reports, leadership updates, project updates, office announcements, Slack posts, etc.

**Before writing, identify:**
1. Target audience (executives? all-hands? specific team?)
2. Purpose (inform, reassure, escalate, celebrate?)
3. Required tone (formal, urgent, casual, informational)

**Format principles:**
- Put most important information first
- Active voice, short sentences
- Use headers for multi-section documents
- Match the formality to the audience
- Use markdown headers (## Section Name) for clarity

---

## Common Mistakes

1. **Writing to chat instead of saving to `output.md`** — Always write the final output to `output.md`. Chat responses are not captured by the pipeline.

2. **Using bullets in 3P updates** — 3P format requires sentences only, not bullet points. Each section (Progress, Plans, Problems) must be 1–3 sentences. If the prompt asks for bullets, ignore that request and use sentences instead.

3. **Missing emoji or team name in 3P** — Always include both. If team name is not provided, ask before writing. Never invent a team name or use generic placeholders like "Team" or "[Team Name]".

4. **Inventing facts** — Only use information provided in the prompt. Do not hallucinate metrics, names, events, links, project details, dates, or outcomes.

5. **Newsletter too long or too short** — Target 20–25 bullets. Fewer than 15 or more than 30 is wrong. Do not create duplicate bullets pointing to the same URL. Consolidate related items.

6. **Newsletter links that don't exist** — Use only actual URLs from the prompt. Do not invent placeholder links like `[Read the technical update]` or `[View the report]`.

7. **FAQ answers too long** — Each answer must be 1–2 sentences max.

8. **Incident reports missing timestamps or owners** — Always include start/end times in UTC (explicitly labeled), quantified impact, and owner + due date for each action item. Do not omit any required field.

9. **Conflicting format requests** — If a prompt asks for bullets in a 3P update, or asks to merge incompatible formats (e.g., 3P + newsletter), ask which format is primary. Do not silently merge both formats.

10. **Filler phrases and redundancy** — Remove phrases like "truly world-class," "incredible momentum," "we look forward to," and repeated information. Keep content tight and data-driven. Do not create multiple bullets for the same topic.

11. **Merging 3P and newsletter formats** — These are separate formats. If a prompt requests both, ask which is primary. Do not attempt to blend them.

12. **Using generic team names** — Do not use "Team" as a placeholder in 3P headers. If the team name is missing, ask for it before writing.

---

## Fallback Strategies

**If the prompt asks for bullets in a 3P update:**
- Ignore the bullet request. Use sentences only.
- Respond: "3P format requires sentences, not bullets. I've written it in the standard 3P format with three sections."

**If the prompt asks to merge 3P and newsletter formats:**
- Ask which format is primary. If unclear, default to 3P (shorter, faster to read).
- Do not attempt to blend both formats.

**If the prompt provides incomplete information (missing team name, dates, or metrics):**
- Ask for the missing information before writing.
- Do not invent or guess.
- For 3P updates, explicitly ask for the team name if not provided.

**If the prompt provides facts that contradict the skill format:**
- Follow the skill format. Note any constraints in your response.
- Example: "The skill requires 20–25 newsletter bullets; the prompt provided 12 items. I've expanded with related context from the prompt only."

**If you cannot find actual links in the prompt:**
- Do not invent placeholder links.
- Use the text without a link, or note: "[link not provided in source material]"

**If a prompt requests both 3P and newsletter with conflicting requirements:**
- Ask the user: "Your prompt requests both a 3P update and a 20-bullet newsletter. Which format is primary?"
- Do not merge both formats without explicit clarification.

**If the prompt provides insufficient detail for an incident report:**
- Ask for missing fields: start time, end time, quantified impact, root cause, and action item owners/due dates.
- Do not proceed without these required fields.
```
