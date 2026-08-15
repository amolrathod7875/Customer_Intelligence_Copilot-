# Task: Knowledge Base Over Customer Data

## Problem
Customer data (accounts, issues, feature requests, tasks, meeting notes) lives in one internal
system, while product knowledge (documentation, release notes) lives in a separate, public system.
There is no single place to ask a question that spans both. Answering requires manually checking
multiple systems and stitching results together — a process that does not get faster as data grows.

## Goal
Build a conversational knowledge base agent that can be queried over **customer data** and
**live product documentation** together, grounded in specific records and doc pages.

---

## Must Have
1. Answer questions using the provided customer-data corpus
   (accounts, issues, feature requests, tasks, meeting notes).
2. Answer questions using **live** product documentation and release notes at
   - https://docs.flytbase.com
   - https://releases.flytbase.com
   (queried live, not from a static copy).
3. Combine both sources in a single answer when a question needs it
   (e.g., whether accounts that requested a feature are on a plan where the platform
   already supports it per the docs).
4. Ground every answer in a specific record or doc page; never assert without a citation.
   Clearly state when there is not enough information instead of guessing.
5. Reflect an updated corpus (records added/changed/removed) without a full manual rebuild.

## Bonus Points
- Natural-language querying across categories, time, or industry
  (e.g., most-requested features among accounts in a given industry).
- Flag contradictions between sources
  (e.g., a feature shown as "requested" in customer data but already "shipped" per release notes).
- Surface which questions get asked most often (usage signal).
- Handle ambiguous or multi-part questions by breaking them down.

---

## Constraints & Scope
### Technology
- No required stack, platform, or framework. Build however you choose.

### Data Assumptions
- Synthetic customer-data corpus is provided; every company, person, and record is fabricated.
- docs.flytbase.com and releases.flytbase.com are real and public — query them live,
  do not scrape/copy their content into a private dataset.
- A follow-up corpus update may be issued to test that the system stays current
  without a manual rebuild.
- No real FlytBase customer data may be used at any point.

### Out of Scope (optional bonus)
- Any live connection to FlytBase's actual internal systems.
  The provided corpus is the only customer-data surface allowed.

---

## Demo Requirements (Live)
Demonstrate three grounded answers:
1. A question answerable **only** from the customer-data corpus.
2. A question answerable **only** from product documentation.
3. A question that **requires combining both** sources.

---

## Proposed Build Approach (suggested)
- **Customer data layer:** Parse the 5 Markdown files into a queryable store
  (accounts, issues, feature_requests, tasks, meeting_notes). Support incremental
  re-ingestion so corpus updates are reflected without a full rebuild.
- **Product docs layer:** Retrieve live from docs.flytbase.com and releases.flytbase.com
  at query time (fetch + index on demand / light caching), never a static snapshot.
- **Agent/orchestration:** Route each question to the relevant source(s), retrieve
  cited passages/records, and synthesize a grounded answer with explicit references.
- **Grounding & guardrails:** Attach a source citation (record ID or doc URL) to every claim;
  return "insufficient information" when retrieval is empty.
- **Bonus:** Track query logs for top-question analytics; add a contradiction checker
  that compares feature_request status vs. release-note "shipped" signals.

## Success Criteria
- All three demo question types answered with citations.
- Customer-data updates visible without manual rebuild.
- Docs sourced live, not copied.
- Contradictions and "not enough info" handled explicitly.