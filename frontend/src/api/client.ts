import type { ChatResponse, SyncSummary } from "@/types";

export const USE_MOCK_API = import.meta.env.VITE_USE_MOCK_API === "true";

// Base URL of the FastAPI backend. Override with VITE_API_BASE if hosted elsewhere.
export const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export const initialMockAnswer: ChatResponse = {
  answer:
    "Two enterprise accounts requested offline mission synchronization. The capability appears to be available in the current FlytBase product documentation. The recommended next step is for the account owner to validate the workflow with each customer and share the relevant product guide.",
  route: "both",
  insufficiencies: [],
  citations: [
    {
      id: "fr-018",
      source_type: "customer_record",
      title: "Feature request FR-018 Â· SkyGrid Systems",
      excerpt:
        "Requested offline mission synchronization for low-connectivity operational environments.",
      url: null,
      meta: ["Feature request", "Enterprise"],
    },
    {
      id: "note-221",
      source_type: "customer_record",
      title: "Meeting note Â· SkyGrid Systems",
      excerpt:
        "Team asked whether mission updates could continue while a device is temporarily offline.",
      url: null,
      meta: ["Meeting note", "Mar 2026"],
    },
    {
      id: "doc-mission-planning",
      source_type: "documentation",
      title: "Mission planning and synchronization",
      excerpt:
        "Relevant FlytBase documentation describing mission-related workflow support.",
      url: "https://docs.flytbase.com/mission-planning",
      meta: ["Live documentation"],
    },
  ],
};

const insufficientMock: ChatResponse = {
  answer: "",
  route: "documentation",
  insufficiencies: [
    "I could not find enough live FlytBase evidence to confirm this capability.",
  ],
  citations: [],
};

const customerOnlyMock: ChatResponse = {
  answer:
    "Two open items are currently tracked for SkyGrid Systems: a bug affecting mission upload retries and a task to review the offline synchronization workflow with the account owner.",
  route: "customer",
  insufficiencies: [],
  citations: [
    {
      id: "bug-402",
      source_type: "customer_record",
      title: "Bug BUG-402 Â· SkyGrid Systems",
      excerpt:
        "Mission upload retries intermittently fail when the device reconnects after a long outage.",
      url: null,
      meta: ["Bug", "Open"],
    },
    {
      id: "task-119",
      source_type: "customer_record",
      title: "Task TASK-119 Â· SkyGrid Systems",
      excerpt:
        "Review the offline synchronization workflow with the account owner before the next quarterly check-in.",
      url: null,
      meta: ["Task", "In progress"],
    },
  ],
};

const documentationMock: ChatResponse = {
  answer:
    "FlytBase documentation describes mission planning as a guided workflow covering waypoint definition, scheduling, and synchronization of mission updates to connected devices.",
  route: "documentation",
  insufficiencies: [],
  citations: [
    {
      id: "doc-mission-planning-2",
      source_type: "documentation",
      title: "Mission planning and synchronization",
      excerpt:
        "Relevant FlytBase documentation describing mission-related workflow support.",
      url: "https://docs.flytbase.com/mission-planning",
      meta: ["Live documentation"],
    },
    {
      id: "release-2026-03",
      source_type: "release_note",
      title: "Release notes Â· March 2026",
      excerpt:
        "Improvements to mission scheduling and synchronization reliability for intermittent connectivity.",
      url: "https://docs.flytbase.com/release-notes",
      meta: ["Live release note"],
    },
  ],
};

function pickMock(question: string): ChatResponse {
  const q = question.toLowerCase();
  if (q.includes("open bug") || q.includes("task")) return customerOnlyMock;
  if (q.includes("mission planning") || q.includes("documentation"))
    return documentationMock;
  if (q.includes("geofencing") || q.includes("unsupported")) return insufficientMock;
  return initialMockAnswer;
}

export async function askQuestion(question: string): Promise<ChatResponse> {
  if (USE_MOCK_API) {
    await delay(900);
    if (question.toLowerCase().includes("fail")) {
      throw new Error("Unable to retrieve an answer right now.");
    }
    return pickMock(question);
  }

  const response = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!response.ok) throw new Error("Unable to retrieve an answer right now.");
  return response.json();
}

export async function syncCorpus(): Promise<SyncSummary> {
  if (USE_MOCK_API) {
    await delay(1200);
    return {
      scanned: 1817,
      created: 1,
      updated: 2,
      deleted: 0,
      unchanged: 1814,
      synced_at: new Date().toISOString(),
    };
  }

  const response = await fetch(`${API_BASE}/api/corpus/sync`, { method: "POST" });
  if (!response.ok) throw new Error("Corpus sync failed. Please try again.");
  return response.json();
}
