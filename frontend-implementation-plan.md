# Customer Intelligence Copilot — Lovable Frontend Build Specification

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Give Lovable a focused, implementation-ready brief to create a polished responsive frontend for a grounded customer-data + live FlytBase documentation copilot.

**Architecture:** Build a React + TypeScript single-page dashboard. The frontend calls the backend through two endpoints—`POST /api/chat` and `POST /api/corpus/sync`—but must be fully previewable in Lovable using a local mock API mode until the real backend is connected. The UI must visibly separate **Customer Evidence** from **Live FlytBase Evidence**.

**Tech Stack:** Lovable default React/TypeScript app, Tailwind CSS, Lucide icons, shadcn/ui components where useful, native `fetch` through one API client module. Do not create a backend, authentication, database, or Supabase integration.

---

## Important: Use This Section as the Primary Lovable Prompt

Copy the prompt below into Lovable as the first request.

```text
Build a polished responsive SaaS dashboard called “Customer Intelligence Copilot”.

Purpose:
A customer-success or solutions user asks questions across internal synthetic customer records and live FlytBase product documentation/release notes. The interface must make every answer traceable to its sources.

This is FRONTEND ONLY. Do not build authentication, a database, Supabase, server functions, scraping, an LLM, or a backend. Implement a frontend API adapter and use realistic mock data so the app works immediately in preview. Later, it will connect to a FastAPI backend.

Design direction:
- Premium B2B SaaS dashboard, clean and trustworthy—not a generic chatbot.
- Light background: soft off-white / light slate.
- Primary color: deep navy (#0F172A or similar).
- Accent: emerald/teal for verified/live states (#10B981 / #14B8A6).
- Warning/insufficient-evidence state: amber—not red unless it is a real technical failure.
- Rounded cards (12–16px), subtle borders, gentle shadows, spacious layout.
- Use Inter or a similarly clean sans-serif font.
- Use Lucide icons only; no emoji as interface icons.
- Responsive: desktop is a two-column workspace; mobile stacks all sections cleanly.

Build this exact page:

1) Top header
- Left: small teal circular/square icon plus “Customer Intelligence Copilot”.
- Subtitle: “Grounded answers from customer records and live FlytBase sources.”
- Right: outlined “Sync customer corpus” button with a refresh icon.
- Under the header, show a small status pill: “Customer corpus ready · Last synced just now”.

2) Hero / question area (left column, about 60% desktop width)
- Heading: “Ask the knowledge base”.
- Supporting text: “Search customer history, product documentation, and release notes in one place.”
- Large rounded textarea with label “Ask a question”, placeholder: “e.g. Which accounts requested geofencing, and is it currently supported?”
- Primary button: “Ask Copilot” with a send/arrow icon.
- Disable button for blank input.
- During request: button loading state and a short text: “Searching relevant evidence…”.

3) Demo question chips below the input
Use three clickable chips/buttons that insert and submit through the same normal flow:
- “Show open bugs and tasks for a customer”
- “How does FlytBase support mission planning?”
- “Which customers requested a feature that is already available?”

4) Answer card below the question area
Display this mock combined-source answer on initial load so the preview looks complete:

Title/label: “Copilot answer”
Answer:
“Two enterprise accounts requested offline mission synchronization. The capability appears to be available in the current FlytBase product documentation. The recommended next step is for the account owner to validate the workflow with each customer and share the relevant product guide.”

Then show three compact insight pills:
- “2 customer requests found”
- “1 live product source found”
- “Cross-source answer”

The answer card must support these states:
- Loading: skeleton blocks, no fake answer text.
- Success: answer + route/status badge.
- Insufficient evidence: amber panel stating “I could not find enough live FlytBase evidence to confirm this capability.” Do not show fake citations.
- API error: neutral error card with “Try again” button.

5) Evidence panel (right column, about 40% desktop width)
Heading: “Evidence” and subtext: “Every answer is linked to the records and pages used.”

Create two clearly separated sections:

A. “Customer Evidence” with a database icon and dark/slate label
Show two source cards:
- “Feature request FR-018 · SkyGrid Systems”
  Excerpt: “Requested offline mission synchronization for low-connectivity operational environments.”
  Metadata chips: “Feature request” and “Enterprise”
- “Meeting note · SkyGrid Systems”
  Excerpt: “Team asked whether mission updates could continue while a device is temporarily offline.”
  Metadata chips: “Meeting note” and “Mar 2026”

B. “Live FlytBase Evidence” with a globe/external-link icon and teal label
Show one source card:
- “Mission planning and synchronization”
  Excerpt: “Relevant FlytBase documentation describing mission-related workflow support.”
  Label: “Live documentation”
  Visible domain: “docs.flytbase.com”
  CTA link: “Open live source ↗”

Use empty states when a category has no citations:
- Customer: “No matching customer records were found.”
- Live source: “No live FlytBase documentation or release-note evidence was found.”

6) Corpus sync result
When “Sync customer corpus” is clicked, show a compact success toast or status card:
“Corpus synchronized”
“1 new · 2 updated · 0 deleted · 1,814 unchanged”
Include a timestamp.
Use a loading state while sync is running and an error state with retry if it fails.

7) Helpful trust details
At bottom of the page, include a small quiet note:
“Answers are generated only from retrieved customer records and live FlytBase sources. When evidence is missing, Copilot will say so.”

Accessibility requirements:
- All controls have visible labels.
- Proper button/input focus states.
- Source links are keyboard accessible and open in a new tab.
- Maintain readable contrast.

Code organization:
- src/App.tsx: page composition and top-level state.
- src/types.ts: Citation, ChatResponse, SyncSummary types.
- src/api/client.ts: askQuestion and syncCorpus functions.
- src/components/ChatPanel.tsx
- src/components/DemoQuestions.tsx
- src/components/AnswerCard.tsx
- src/components/CitationPanel.tsx
- src/components/SyncStatus.tsx
- src/components/EmptyState.tsx

Create a `USE_MOCK_API` constant in `src/api/client.ts`, set to true initially. When true, return the specified realistic mock combined response after a short simulated delay. When false, call:
- POST /api/chat with JSON { "question": string }
- POST /api/corpus/sync

Do not hard-code answers in components. Mock data must exist only in the API adapter so swapping to the real backend later changes no UI code.
```

---

## API Contract Lovable Must Follow

The backend is not responsible for frontend display decisions. Use these exact TypeScript shapes in `src/types.ts`.

```ts
export type SourceType = "customer_record" | "documentation" | "release_note";
export type QueryRoute = "customer" | "documentation" | "release_note" | "both";

export interface Citation {
  id: string;
  source_type: SourceType;
  title: string;
  excerpt: string;
  url: string | null;
}

export interface ChatResponse {
  answer: string;
  route: QueryRoute;
  insufficiencies: string[];
  citations: Citation[];
}

export interface SyncSummary {
  scanned: number;
  created: number;
  updated: number;
  deleted: number;
  unchanged: number;
  synced_at: string;
}
```

When `USE_MOCK_API` is `false`:

```ts
export async function askQuestion(question: string): Promise<ChatResponse> {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!response.ok) throw new Error("Unable to retrieve an answer right now.");
  return response.json();
}

export async function syncCorpus(): Promise<SyncSummary> {
  const response = await fetch("/api/corpus/sync", { method: "POST" });
  if (!response.ok) throw new Error("Corpus sync failed. Please try again.");
  return response.json();
}
```

## Lovable Delivery Checklist

Ask Lovable to complete these items in order; do not move to backend work.

### Task 1: Build the visual shell and responsive layout

**Files likely to change:**
- `src/App.tsx`
- `src/index.css` or `src/styles.css`

**Acceptance checks:**
- Desktop has a readable left workspace and right evidence column.
- Mobile stacks the sections without horizontal scroll.
- Header, question area, answer card, evidence card, and trust note are all visible.

### Task 2: Add typed API adapter with mock mode

**Files likely to change:**
- `src/types.ts`
- `src/api/client.ts`

**Acceptance checks:**
- Initial preview works without any backend.
- Mock response is returned only from the adapter, never hard-coded inside display components.
- Switching one `USE_MOCK_API` boolean prepares the UI for the actual FastAPI service.

### Task 3: Implement chat interaction states

**Files likely to change:**
- `src/components/ChatPanel.tsx`
- `src/components/AnswerCard.tsx`
- `src/App.tsx`

**Acceptance checks:**
- Blank questions cannot be submitted.
- Submission displays loading state.
- Success, insufficient-evidence, and API-error states are visually distinct.
- Insufficient-evidence state cannot render fake citations.

### Task 4: Implement evidence grouping and external-source cards

**Files likely to change:**
- `src/components/CitationPanel.tsx`
- `src/components/EmptyState.tsx`

**Acceptance checks:**
- Customer records and live sources are visibly separated.
- A `documentation` or `release_note` citation with a URL renders an accessible external link.
- `customer_record` citations never render a made-up web URL.
- Empty states are truthful and readable.

### Task 5: Implement sync interaction

**Files likely to change:**
- `src/components/SyncStatus.tsx`
- `src/App.tsx`

**Acceptance checks:**
- Sync button has loading, success, and retryable error states.
- Success UI shows all four counts: created, updated, deleted, unchanged.
- The UI does not claim the corpus is synced until the API/mock resolves.

### Task 6: Final polish and handoff

**Files likely to change:**
- `README.md` (if Lovable includes one)
- component/style files as needed

**Acceptance checks:**
- No broken links, placeholder “Lorem ipsum,” authentication screens, database setup, or server-function code.
- Desktop and mobile views look intentional.
- All dashboard labels use exact product language: “Customer Evidence,” “Live FlytBase Evidence,” “Sync customer corpus.”
- The answer and evidence display together in the initial mock preview.

---

## What Is Deliberately Out of Scope for Lovable

Do **not** ask Lovable to build any of the following:

- FastAPI routes or Python code
- ChromaDB/vector database
- embeddings, RAG, document parsing, scraping, or live web retrieval
- LLM prompts, API keys, model-provider configuration
- login/authentication/user roles
- Supabase setup, database tables, storage buckets, or edge functions
- saved conversations, user analytics, or long-term chat history
- a customer-account dashboard or contradiction-detection feature

Those belong to the backend or later bonus work. The frontend should demonstrate the mandatory problem-statement requirements clearly, not become a larger product than needed.

## Verification Before Accepting Lovable Output

1. Run the Lovable preview with mock mode enabled.
2. Confirm the initial page shows a **combined-source** answer with two customer citations and one live-doc citation.
3. Click every demo question; ensure it uses the same chat loading/response flow.
4. Test an insufficient-evidence mock response: it must show the amber explanation and no source links.
5. Click **Sync customer corpus** and confirm the counts appear after loading.
6. Set `USE_MOCK_API=false` only after the FastAPI backend is running; check that `/api/chat` and `/api/corpus/sync` responses render without frontend changes.

## Final Definition of Done

- [ ] A polished responsive frontend is visible in Lovable preview.
- [ ] The demo uses mock data through a dedicated API adapter.
- [ ] One toggle prepares the same UI to use the real backend.
- [ ] Customer and live FlytBase evidence are visually and semantically separate.
- [ ] The UI correctly communicates loading, success, missing-evidence, sync, and API-error states.
- [ ] No backend/auth/database functionality was added in Lovable.
