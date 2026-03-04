---
name: web-search
description: Search FIA regulations, formula1.com news, and Wikipedia to verify race incidents, regulations, schedule changes, and post-race decisions. Use only when pitlane CLI data is insufficient.
---

# Web Search for F1 Research

Search trusted F1 and regulatory sources to verify incidents, look up regulations, check schedule changes, and confirm post-race decisions. Web search supplements the pitlane CLI — it does not replace it.

## When to Use Web Search (vs pitlane CLI)

| Question type | Primary tool |
|---|---|
| Lap times, tyre strategy, race results, telemetry | pitlane CLI (f1-analyst skill) |
| Race control messages, flags, safety cars | pitlane CLI (race-control skill) |
| Driver information, codes, nationalities | pitlane CLI (f1-drivers skill) |
| Published schedule dates and session times | pitlane CLI (f1-schedule skill) |
| FIA technical/sporting regulations (rule text) | WebSearch → api.fia.com |
| FIA regulation news and announcements | WebSearch → www.fia.com |
| Race incident verification (multi-driver, same lap) | WebSearch → formula1.com + fia.com |
| Post-race disqualifications and steward decisions | WebSearch → formula1.com + fia.com |
| Schedule changes due to external world events | WebSearch → formula1.com |
| General driver or circuit background | WebSearch → wikipedia.org |

## Domain Constraints

Always include `allowed_domains` on every WebSearch call. Permitted domains:

| Domain | Content |
|---|---|
| `formula1.com`, `www.formula1.com` | Official F1 news: race reports, steward decisions, schedule changes, disqualifications |
| `www.fia.com` | FIA news and announcements about regulations |
| `api.fia.com` | FIA sporting and technical regulation documents (the actual rule text) |
| `wikipedia.org`, `en.wikipedia.org` | Driver bios, circuit histories, regulation context (reference only — not authoritative) |

## Use Case Workflows

### FIA Regulations

Search `api.fia.com` for the regulation document text. Search `www.fia.com` for related news and announcements. Always cite the document name and article number in your response.

Example search: `2024 FIA Formula 1 Sporting Regulations Article 39`

```
allowed_domains: ["api.fia.com", "www.fia.com"]
```

### Race Incident Verification

Use when race-control data shows multiple incidents on the same lap and attribution is ambiguous. Search for the full incident report rather than restricting to a single driver — the news report will describe all involved drivers and the sequence of events. Cross-reference with FIA steward documents for any resulting penalties.

Example search: `2024 Monaco Grand Prix lap 1 incident`

```
allowed_domains: ["formula1.com", "www.formula1.com", "www.fia.com", "api.fia.com"]
```

### Schedule Changes

Use when a published schedule may have been affected by external events (weather, geopolitical situations, cancellations). Search for the season year and circuit name.

Example search: `2024 Azerbaijan Grand Prix schedule change cancelled`

```
allowed_domains: ["formula1.com", "www.formula1.com"]
```

### Post-Race Disqualifications and Steward Decisions

Race results from the pitlane CLI reflect results as-raced. Post-race DSQs and penalties can alter official standings hours or days later. Search formula1.com for initial reports and fia.com for the official steward decision documents.

Example search: `2024 Belgian Grand Prix post-race disqualification`

```
allowed_domains: ["formula1.com", "www.formula1.com", "www.fia.com", "api.fia.com"]
```

## Notes

- Wikipedia is for context only — do not cite it as authoritative for regulations or official decisions.
- Do not search for lap time or telemetry data; use the pitlane CLI.
- Steward decision documents often appear several hours to days after a race — if nothing is found immediately, note that the investigation may still be ongoing.
