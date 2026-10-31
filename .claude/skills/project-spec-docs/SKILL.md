---
name: project-spec-docs
description: Walks the user, one step at a time, through writing a new frontend project's planning docs before any code — PRD.md, content-model.md, site-contract.md, design-standard.md and a one-page CLAUDE.md anchor — looping each doc through the spec-clarity-checker agent and asking the user one question at a time until every statement is deterministic, then running a Director's Review before moving on. Items the user is unsure about are researched by the spec-researcher agent, which returns options with a recommendation. Then hands off to the spec-auditor agent to verify built code against the docs. Use when starting a new site or app, when the user has only a "vibe sentence" or rough idea, when an agent keeps inventing structure, behavior or styling, when CLAUDE.md has grown past a page, or when the user says "set up the project", "plan before we build" or "write the PRD".
---

# Project Spec Docs

**Plan → Build → Verify.** An agent builds well from a clear, specific picture and invents things when the picture is vague. Changing structure after features exist is the most expensive rework there is. This skill produces the picture.

## How to guide the user

You are guiding the user through this, so:
- **Do one document at a time,** in the order below. Don't draft the next one until the current one passes its review and the user approves it.
- **Ask one question at a time.** Wait for the answer.
- **Draft, clarify, then review.** Write the draft, run the clarification loop below until it passes, then go through the Director's Review with the user.
- **Push back on vague wording.** "Clean", "modern", "fast", "generous" and "intuitive" fail. Ask for a number, a hex code or a testable statement.
- **Write no application code** during this skill. If the user asks to start building, list which docs are still missing and confirm they want to skip them.
- **Keep the user oriented.** After each step, show the progress list (✅ done, ▶ current, ○ next).

## The clarification loop (run on every doc)

After drafting or editing a doc:

1. Run the **`spec-clarity-checker`** agent on that doc, plus earlier approved docs so it can catch contradictions.
2. If the verdict is `DETERMINISTIC`, go on to the Director's Review.
3. Otherwise, take the findings **one at a time** in the order returned, Blockers first:
   - Show the vague text and ask the agent's question. Offer its suggested replacement as the default ("accept", or give your own value).
   - If the user answers "you decide", use the suggested replacement and mark it in the doc with `<!-- default: chosen by agent, confirm later -->`.
   - If the user answers "not sure", "need to research" or "later", add it to `## Open questions` as `- [ ] research: <question>`. Don't press for an answer now.
   - Write the answer into the doc right away. Each value lives in exactly one place.
4. Run the checker again and repeat until it returns `DETERMINISTIC`.
5. The user may defer **Minor** findings, never Blockers. Record deferred items in a `## Open questions` section at the end of that doc.

Show the progress after each answer, e.g. "design-standard.md: 3 of 7 resolved".

## Resolving open items (research)

Run this when a doc has `research:` items before its Director's Review, or at the latest before Step 7. Also run it whenever the user asks.

1. Run the **`spec-researcher`** agent on the open items. It reads the PRD for context and returns options, a recommendation, a confidence rating and sources for each item.
2. Present the items **one at a time**. Show the options and the recommendation, then ask the user to pick A, B or C, give their own answer, or keep the item open.
3. Write the chosen value into the doc where it belongs, and remove the item from `## Open questions`.
4. If a choice opens a follow-up question, add the follow-up as a new item.
5. Run `spec-clarity-checker` again on the changed doc, because new text has to be deterministic too.
6. Record the researcher's sources in a `## Decisions log` at the end of the doc: item, choice, date, source URLs.

**Blockers must be resolved before Step 7.** A Minor item may stay open if the user explicitly accepts it.

## Step 0: Resume, don't restart

Check which of `PRD.md`, `content-model.md`, `site-contract.md`, `design-standard.md` and `CLAUDE.md` already exist. Start at the first missing or failing one. If they keep the docs elsewhere (e.g. `docs/`), use that location and record it in `CLAUDE.md`.

## Step 1: Vibe sentence

Ask for one sentence describing the product and how it should feel. Every later document traces back to it.

## Step 2: `PRD.md`, *what is it and who is it for?*

Sections, using the template in `references/templates.md`:
1. **Vision:** 1–2 sentences: the product and the problem it solves.
2. **Users:** 2–3 personas, each with a real context and frustration.
3. **Features:** Must-Have / Should-Have / Nice-to-Have.
4. **Constraints:** stack, hard limits, and explicit **non-goals**, which keep the agent from over-engineering. Scope it for a solo developer working with AI unless told otherwise.
5. **Design standards:** a pointer to `design-standard.md`, not the details.
6. **Success criteria:** each one measurable. ❌ "User enjoys it." ✅ "A first-time visitor can say what the product does within 10 seconds and reach any section in one click."

Director's Review:
- [ ] The vision matches what the user wants to build. Read it back and ask.
- [ ] Personas have real frustrations, not demographics.
- [ ] Must-Have is short. A short list shows focus.
- [ ] Every success criterion can be checked objectively in an audit.

## Step 3: `content-model.md`, *what exists on the page?*

Sections (Hero, Work, About, Contact, …), and the fields inside each, with constraints on every field. It contains no design and no behavior.

```
## Hero
- headline: max 8 words; captures the emotional core of the vibe sentence
- sub-headline: exactly 1 sentence; expands the headline without repeating its words
- primary CTA: action verb label; links to #contact
```

Director's Review:
- [ ] Every PRD Must-Have appears in some section.
- [ ] Nothing redundant or "just in case" remains.
- [ ] Every field has explicit constraints: length, format and purpose.

This is practice for data modeling: the same habit later produces a database ERD.

## Step 4: `site-contract.md`, *how does it behave?*

Three pillars:
1. **Page structure:** every section in DOM order, each with one sentence of purpose.
2. **Content inventory:** the fields from the content model, with tone added. ❌ "Project cards with title and description." ✅ "Title: max 6 words, describes what was built, not the tech. Description: exactly 2 sentences on the problem solved."
3. **Behavior spec:**
   - Navigation states, e.g. "sticky header, transparent over hero, solid after 80px scroll".
   - Scroll behavior.
   - Hover and focus states with timing.
   - Layout per breakpoint, e.g. `<768px` and `<1024px`.
   - Loading, empty and error states, for apps.

For a static frontend this file plays the role of an API contract. In multi-agent work, a gap in it causes integration failures.

Director's Review:
- [ ] Every PRD Must-Have is represented.
- [ ] The inventory is precise enough to build without asking a question.
- [ ] Every interactive element has defined states, and every breakpoint has a defined layout.

## Step 5: `design-standard.md`, *how does it look?*

Four dimensions: **color** (hex for background, text, border, accent), **typography** (families, weights, scale, line height, letter spacing), **spacing** (base unit, container padding, gaps) and **texture** (grain, gradients, blur, elevation).

**The CSS value test:** every rule must translate into one specific CSS value.

| ❌ Fails | ✅ Passes |
|---------|-----------|
| "Dark background" | `background-color: #0d1117` |
| "Generous spacing" | `padding: 64px 24px; gap: 32px` (8px base) |
| "Smooth transitions" | `transition: opacity 250ms ease-out` |

Director's Review:
- [ ] Every line passes the CSS value test.
- [ ] Tokens are named so they can become CSS custom properties directly.

## Step 6: `CLAUDE.md`, the anchor (under one page)

`CLAUDE.md` points to documents and doesn't contain their details. It holds only:
1. **What this is:** 2–3 sentences, including the vibe sentence.
2. **Constraints:** stack, hard limits and forbidden actions (e.g. "no new dependencies without approval").
3. **Where everything is:** a load-on-demand table:

| Doc | Load when |
|-----|-----------|
| `PRD.md` | making product or scope decisions |
| `content-model.md` | building or reviewing page structure |
| `site-contract.md` | implementing layout or interactions |
| `design-standard.md` | any UI or styling work |

**One-page test:** if it's longer than a page, delete every sentence that repeats a supporting doc. Lean context gives precise output, and bloated context dilutes it.

## Step 7: Build and verify

Hand off to building in small slices. After each slice, run the **`spec-auditor`** agent against the docs and the changed code. Fix Critical and High findings before the next slice. To build the Must-Haves as a sequence of specced features, add `specs/roadmap.md` and continue with `sdd-feature-loop`, which uses `PRD.md` as its mission and tech stack.

## The three standards (apply at every step and in every review)

1. **Does it scale?** Would this decision hold up at 10× the size?
2. **Is it secure?** Is that verified, or assumed?
3. **Do I know exactly how it works?** Code you can't explain is code you don't own.

## Verification

- [ ] All five files exist, and the user approved each one's Director's Review.
- [ ] `spec-clarity-checker` returns `DETERMINISTIC` on all five docs together, with no Blockers and no cross-doc contradictions.
- [ ] Every `<!-- default: … -->` marker has been confirmed by the user or is listed under Open questions.
- [ ] No `research:` item tied to a Blocker remains open. Each resolved item has an entry in the Decisions log.
- [ ] `CLAUDE.md` fits on one page and links to every supporting doc.
- [ ] Every PRD Must-Have can be traced to the content model and the site contract.

## Sources

- See `SOURCES.md` → "ZTM Claude Code Tutorial: AI-Assisted Development & Planning" (provided notes).
