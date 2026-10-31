# Templates

Starting skeletons for each planning doc. Replace every `<…>` placeholder. Remove any line that doesn't apply instead of leaving a placeholder in.

Every doc ends with these two sections:

```markdown
## Open questions
- [ ] research: <question>: <why it's open> (Blocker | Minor)
- [ ] deferred: <question>: accepted as open by <user> on <date> (Minor only)

## Decisions log
| Item | Decision | Date | Sources |
|------|----------|------|---------|
```

## PRD.md

```markdown
# PRD: <product name>

> Vibe: <one sentence>

## Vision
<1–2 sentences: what it is, what problem it solves>

## Users
### <Persona name>: <role>
- Context: <where/when they use it>
- Frustration: <what is broken for them today>
- Needs: <what success looks like for them>

## Features
### Must-Have
- <feature>: <one-line why>
### Should-Have
- …
### Nice-to-Have
- …

## Constraints
- Stack: <…>
- Hard limits: <…>
- Non-goals: <things we will explicitly NOT build>

## Design Standards
See `design-standard.md`.

## Success Criteria
- [ ] <measurable, verifiable statement>
```

## content-model.md

```markdown
# Content Model

## <Section name>
- <field>: <constraint: length / format / purpose>
```

## site-contract.md

```markdown
# Site Contract

## Page Structure (DOM order)
1. <Section>: <one-sentence purpose>

## Content Inventory
### <Section>
- <field>: <length, format, tone>

## Behavior
### Navigation
- <state → trigger → result>
### Scroll
- <…>
### Interactive states
| Element | Hover | Focus | Active | Transition |
|---------|-------|-------|--------|------------|
### Breakpoints
| Viewport | Layout changes |
|----------|----------------|
| < 768px | <…> |
| < 1024px | <…> |
### Loading / empty / error (apps)
- <…>
```

## design-standard.md

```markdown
# Design Standard

## Color
| Token | Value | Use |
|-------|-------|-----|
| --color-bg | #… | page background |
| --color-text | #… | body text |
| --color-border | #… | dividers |
| --color-accent | #… | CTAs, links |

## Typography
| Token | Family | Weight | Size | Line height | Letter spacing |
|-------|--------|--------|------|-------------|----------------|

## Spacing
- Base unit: <8px>
- Scale: <4, 8, 16, 24, 32, 48, 64>
- Container: <max-width, padding>

## Texture & Atmosphere
- <grain / gradient / blur / shadow with exact values>

## Motion
- Default transition: <property duration easing>
```

## CLAUDE.md

```markdown
# <Project>

<2–3 sentences: what it is + vibe sentence>

## Constraints
- Stack: <…>
- Forbidden without approval: <new dependencies, CDNs, frameworks, …>

## Docs (load only when relevant)
| Doc | Load when |
|-----|-----------|
| PRD.md | product / scope decisions |
| content-model.md | page structure |
| site-contract.md | layout & interactions |
| design-standard.md | UI & styling |
```
