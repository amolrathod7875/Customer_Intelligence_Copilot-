import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Radar } from "lucide-react";
import { askQuestion, initialMockAnswer, syncCorpus } from "@/api/client";
import { AnswerCard } from "@/components/AnswerCard";
import { ChatPanel } from "@/components/ChatPanel";
import { CitationPanel } from "@/components/CitationPanel";
import { SyncButton, SyncResultCard, SyncStatusPill } from "@/components/SyncStatus";
import type { ChatResponse, SyncSummary } from "@/types";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Customer Intelligence Copilot — Grounded Answers" },
      {
        name: "description",
        content:
          "Ask across customer records and live FlytBase documentation, with every answer traced to its sources.",
      },
      { property: "og:title", content: "Customer Intelligence Copilot" },
      {
        property: "og:description",
        content:
          "Grounded answers from customer records and live FlytBase sources, with linked evidence.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Index,
});

function Index() {
  const [question, setQuestion] = useState("");
  const [lastAsked, setLastAsked] = useState<string | null>(null);
  const [answer, setAnswer] = useState<ChatResponse | null>(initialMockAnswer);
  const [asking, setAsking] = useState(false);
  const [askError, setAskError] = useState<string | null>(null);

  const [syncing, setSyncing] = useState(false);
  const [syncSummary, setSyncSummary] = useState<SyncSummary | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);

  async function handleAsk(value: string) {
    setLastAsked(value);
    setAsking(true);
    setAskError(null);
    try {
      const response = await askQuestion(value);
      setAnswer(response);
    } catch (error) {
      setAnswer(null);
      setAskError(
        error instanceof Error ? error.message : "Unable to retrieve an answer right now.",
      );
    } finally {
      setAsking(false);
    }
  }

  async function handleSync() {
    setSyncing(true);
    setSyncError(null);
    try {
      setSyncSummary(await syncCorpus());
    } catch (error) {
      setSyncError(
        error instanceof Error ? error.message : "Corpus sync failed. Please try again.",
      );
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/70 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-5 py-6 sm:px-8 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-start gap-3">
            <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-accent/15 text-accent">
              <Radar className="size-5" aria-hidden />
            </span>
            <div>
              <h1 className="text-lg font-semibold tracking-tight text-foreground">
                Customer Intelligence Copilot
              </h1>
              <p className="mt-0.5 text-sm text-muted-foreground">
                Grounded answers from customer records and live FlytBase sources.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <SyncStatusPill summary={syncSummary} loading={syncing} error={syncError} />
            <SyncButton onSync={handleSync} loading={syncing} />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-5 py-8 sm:px-8 sm:py-10">
        <div className="grid gap-6 lg:grid-cols-5">
          <div className="space-y-6 lg:col-span-3">
            <ChatPanel
              question={question}
              onQuestionChange={setQuestion}
              onSubmit={handleAsk}
              loading={asking}
            />
            <AnswerCard
              data={answer}
              loading={asking}
              error={askError}
              onRetry={() => handleAsk(lastAsked ?? question.trim())}
            />
            {syncSummary && !syncing && !syncError && (
              <SyncResultCard summary={syncSummary} />
            )}
          </div>

          <div className="lg:col-span-2">
            <CitationPanel citations={asking || askError ? [] : (answer?.citations ?? [])} />
          </div>
        </div>

        <p className="mx-auto mt-10 max-w-3xl text-center text-xs leading-relaxed text-muted-foreground">
          Answers are generated only from retrieved customer records and live FlytBase
          sources. When evidence is missing, Copilot will say so.
        </p>
      </main>
    </div>
  );
}
