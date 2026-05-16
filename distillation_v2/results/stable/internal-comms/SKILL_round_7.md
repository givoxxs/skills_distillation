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
- All three elements are mandatory in the header: emoji, team name, date range
- If team name not provided, ask before writing. Do not use generic placeholders like "Team" or "[Team Name]".
- If date range not provided, ask before writing. Do not invent dates.
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
- Do NOT create multiple bullets for the same topic; consolidate related items into single bullets
- Focus on company-wide impact, not team-specific detail
- Do NOT invent facts not given in the prompt
- Remove filler phrases like "truly world-class," "incredible momentum," "we look forward to," "help X get up to speed," "ensure it is comprehensive"

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
- Do not exceed 2–4 sentences total per Q&A pair (question + answer combined)

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
[1–2 sentences. What failed and why. Include specific details about the failure mechanism.]

## Action Items
- [Owner]: [Action] — Due [date]
- [Owner]: [Action] — Due [date]
```

**Rules:**
- Include explicit start and end times in UTC (e.g., **Start:** 2026-05-06 14:32 UTC)
- Quantify impact with specific numbers (% of requests, number of customers, duration in minutes)
- Timeline must use timestamps in HH:MM UTC format
- Each action item must have an owner name (not "TBD") and a specific due date
- Root Cause must explain what failed and why in 1–2 sentences; include specific details about the failure mechanism (e.g., "staging environment did not catch X because Y")
- Do NOT invent facts not given in the prompt
- Do NOT omit any required field (ID, Severity, Start, End, Impact, Timeline, Root Cause, Action Items)

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
- Remove filler and redundancy; do not repeat information across sections
- Use prose paragraphs, not bullet points, unless the prompt explicitly requests bullets

---

## Common Mistakes

1. **Writing to chat instead of saving to `output.md`** — Always write the final output to `output.md`. Chat responses are not captured by the pipeline.

2. **Using bullets in 3P updates** — 3P format requires sentences only, not bullet points. Each section (Progress, Plans, Problems) must be 1–3 sentences. If the prompt asks for bullets, ignore that request and use sentences instead.

3. **Missing emoji or team name in 3P** — Always include both. If team name is not provided, ask before writing. Never invent a team name or use generic placeholders like "Team" or "[Team Name]". The header format is mandatory: [emoji] [Team Name] (Date range).

4. **Inventing dates in 3P updates** — Do not invent date ranges. If the prompt does not provide dates, ask for them before writing.

5. **Inventing facts** — Only use information provided in the prompt. Do not hallucinate metrics, names, events, links, project details, dates, outcomes, or descriptive language like "significant progress," "help developers get up to speed," or "comprehensive and easy to follow."

6. **Newsletter too long or too short** — Target 20–25 bullets. Fewer than 15 or more than 30 is wrong. Do not create duplicate bullets pointing to the same URL. Consolidate related items into single bullets.

7. **Newsletter links that don't exist** — Use only actual URLs from the prompt. Do not invent placeholder links like `[Read the technical update]` or `[View the report]`.

8. **FAQ answers too long** — Each answer must be 1–2 sentences max. Do not exceed 2–4 sentences total per Q&A pair (question + answer combined).

9. **Incident reports missing required fields** — Always include start/end times in UTC (explicitly labeled), quantified impact, root cause with specific details about why the failure occurred, and owner + due date for each action item. Do not omit any required field. Do not use "TBD" for owner names.

10. **Conflicting format requests** — If a prompt asks for bullets in a 3P update, or asks to merge incompatible formats (e.g., 3P + newsletter), ask which format is primary. Do not silently merge both formats.

11. **Filler phrases and redundancy** — Remove phrases like "truly world-class," "incredible momentum," "we look forward to," "help X get up to speed," "ensure it is comprehensive," and repeated information. Keep content tight and data-driven. Do not create multiple bullets for the same topic.

12. **Merging 3P and newsletter formats** — These are separate formats. If a prompt requests both, ask which is primary. Do not attempt to blend them.

13. **Using generic team names** — Do not use "Team" as a placeholder in 3P headers. If the team name is missing, ask for it before writing.

14. **Expanding newsletters with invented content** — When expanding a newsletter, use only facts from the source material. Do not invent new talking points, capabilities, or events not mentioned in the prompt.

15. **Action items without owners or due dates** — Every action item must include an owner name (not "TBD") and a specific due date. Do not omit these fields.

16. **Redundancy in newsletters and reports** — Do not repeat the same information in different sections (e.g., Executive Summary and Phase Status). Consolidate or remove duplicates.

17. **Using bullet points in General Comms when prose is required** — Unless the prompt explicitly requests bullets, use prose paragraphs for office announcements, leadership updates, and other general communications.

18. **Adding interpretive language not in the prompt** — Do not rephrase facts with elaboration like "streamline new developer setup" or "improve command reliability" when the prompt says "fixed a bug." Use the exact language from the prompt.

19. **Omitting required header elements in 3P** — Always include [emoji] [Team Name] (Date range) on the first line. All three elements are mandatory.

20. **Treating inapplicable format criteria as failures** — If a test case is an incident report, do not flag it for missing 3P sections or newsletter bullet count. Only apply format criteria that match the actual output type.

21. **Stating facts as inferred additions** — Do not add phrases like "we are excited to welcome" or "Please join us in welcoming" unless explicitly stated in the prompt. Use only the facts provided.

22. **Vague newsletter bullets** — Each bullet must include concrete outcomes, metrics, or context. Rewrite vague bullets like "Made progress on API" to "Reduced API latency by 12% through caching layer deployment."

23. **Missing output file in review tasks** — When asked to review a draft, always save findings to `output.md`. Do not only print findings to chat.

24. **Duplicating newsletter items for expansion** — When expanding a newsletter, do not repeat the same item 2–3 times with minimal variation. Create logically related but distinct bullets based on source material.

25. **Claiming production status for staging features** — Do not state that a feature is "rolling out to production" if the source material says it is "in staging." Use exact language from the prompt.

26. **Vague or process-oriented language in 3P updates** — Do not write "Completed design review" or "Continued work on X." Lead with outcomes and metrics. Example: Instead of "Completed design review for v2 feature," write "Shipped v2 feature with 15% performance improvement."

27. **Reviewing drafts without using bulleted list format** — When identifying issues in a draft, present findings as a bulleted list (using `-` or `*` markdown). Do not use numbered lists (1, 2, 3) for issue identification.

28. **Missing Problems section in 3P updates** — All three sections (Progress, Plans, Problems) are mandatory. Do not omit Problems even if there are no major blockers. If there are no problems, write a brief sentence like "No major blockers this week."

29. **3P update header without proper spacing** — Ensure the header line is formatted exactly as: `[emoji] [Team Name] ([Date range])` with a blank line before the first section. Do not use markdown headers (#) for the 3P header.

30. **Newsletter expansion creating near-duplicates** — When expanding a newsletter from fewer bullets to the target range, create logically distinct bullets based on source material. Do not create multiple bullets with trivial rewording pointing to the same URL.

---

## Fallback Strategies

**If the prompt asks for bullets in a 3P update:**
- Ignore the bullet request. Use sentences only.
- Respond: "3P format requires sentences, not bullets. I've written it in the standard 3P format with three sections."

**If the prompt asks to merge 3P and newsletter formats:**
- Ask which format is primary. If unclear, default to 3P (shorter, faster to read).
- Do not attempt to blend both formats.
- Example response: "Your prompt requests both a 3P update and a 20-bullet newsletter. Which format is primary? I'll use that format and note why the other is incompatible."

**If the prompt provides incomplete information (missing team name, dates, or metrics):**
- Ask for the missing information before writing.
- Do not invent or guess.
- For 3P updates, explicitly ask for the team name if not provided.
- For 3P updates, explicitly ask for the date range if not provided.
- Example: "I need the team name and date range to complete the 3P update header. What is the team name and what dates should I use?"

**If the prompt provides facts that contradict the skill format:**
- Follow the skill format. Note any constraints in your response.
- Example: "The skill requires 20–25 newsletter bullets; the prompt provided 12 items. I've consolidated related items and used only facts from the prompt."

**If you cannot find actual links in the prompt:**
- Do not invent placeholder links.
- Use the text without a link, or note: "[link not provided in source material]"

**If a prompt requests both 3P and newsletter with conflicting requirements:**
- Ask the user: "Your prompt requests both a 3P update and a 20-bullet newsletter. Which format is primary?"
- Do not merge both formats without explicit clarification.

**If the prompt provides insufficient detail for an incident report:**
- Ask for missing fields: start time, end time, quantified impact, root cause (with specific details about why the failure occurred), and action item owners/due dates.
- Do not proceed without these required fields.

**If a prompt asks to expand a newsletter or report:**
- Use only facts from the source material. Do not invent new events, capabilities, or talking points.
- If expansion is not possible without inventing content, note: "The source material does not contain enough detail to expand this section without inventing facts."

**If a 3P update has no emoji:**
- Add an appropriate emoji that matches the team's function or vibe.
- If unsure, use a generic emoji like 🔄 or 📊.

**If the prompt provides vague or process-oriented language:**
- Reframe to be outcome-focused and data-driven.
- Example: "Completed design review for v2 feature" → "Shipped v2 feature with 15% performance improvement."

**If the prompt asks for General Comms with bullets but the format should be prose:**
- Use prose paragraphs unless the prompt explicitly requests bullets.
- Example: "Office announcements are typically prose. I've formatted this as prose paragraphs. If you need bullets instead, let me know."

**If a 3P update section is too short (fewer than 1 sentence) or too long (more than 3 sentences):**
- Expand or condense to 1–3 sentences per section.
- Ensure each section contains concrete facts or metrics, not filler.

**If newsletter bullets are vague or lack specifics:**
- Rewrite each bullet to include concrete outcomes, metrics, or context.
- Example: "Made progress on API" → "Reduced API latency by 12% through caching layer deployment."

**If FAQ answers contain filler or exceed 2 sentences:**
- Remove filler phrases and condense to 1–2 sentences max.
- Combine question and answer; do not exceed 2–4 sentences total per Q&A pair.

**If the prompt uses elaborative language not in the source material:**
- Use the exact facts from the prompt. Do not add interpretive phrases like "streamline," "improve," or "help X get up to speed."
- Example: If the prompt says "fixed a bug," write "Fixed a bug." Do not write "Improved reliability by fixing a bug."

**If a 3P update is missing the team name:**
- Do not proceed. Ask: "What is the team name for this 3P update?"
- Do not use placeholders or generic names.

**If a 3P update is missing the date range:**
- Do not proceed. Ask: "What date range should I use for this 3P update (e.g., May 5–9, 2026)?"
- Do not invent dates.

**If the output file is not saved:**
- Always use the Write or file-write tool to save to `output.md`.
- Verify the file is created before confirming task completion.
- Do not rely on chat-only responses.

**If a 3P update header is incomplete (missing emoji, team name, or dates):**
- Do not proceed. Ask for all three elements.
- Example: "I need: (1) an emoji, (2) the team name, and (3) the date range. What are these?"

**If the prompt asks to review a draft and identify issues:**
- Save all findings to `output.md` in a clear, structured format using bulleted lists (not numbered lists).
- List each issue with specific examples from the draft.
- Do not only print findings to chat.

**If newsletter expansion creates duplicate or near-identical bullets:**
- Consolidate related items into a single bullet with more detail.
- Do not repeat the same item multiple times.
- Example: Instead of three bullets about "API improvements," write one bullet: "Improved API performance with 12% latency reduction and 18% throughput gain."

**If a feature status is ambiguous (staging vs. production):**
- Use the exact language from the prompt.
- If the prompt says "in staging," write "in staging." Do not claim it is "rolling out to production."

**If a 3P update is missing the Problems section:**
- Do not omit it. Always include all three sections: Progress, Plans, Problems.
- If there are no major blockers, write a brief sentence like "No major blockers this week."

**If reviewing a draft and findings should use bulleted format:**
- Use markdown bullet syntax (`-` or `*`) for each issue.
- Do not use numbered lists (1, 2, 3).
- Example format:
  ```
  - **Issue 1:** Description with specific example
  - **Issue 2:** Description with specific example
  ```

**If the prompt asks to convert a 3P update to newsletter bullets:**
- Extract key facts from each section and rewrite as 3–5 distinct bullets.
- Use "we" tense and include metrics where available.
- Do not invent new facts; only use information from the original 3P update.
```
