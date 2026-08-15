import { AlertTriangle, Database, Globe, Layers, RotateCcw, Sparkles } from "lucide-react";
import type { ChatResponse, QueryRoute } from "@/types";

const routeLabels: Record<QueryRoute, string> = {
  customer: "Customer records",
  documentation: "Live documentation",
  release_note: "Live release notes",
  both: "Cross-source answer",
};

function Pill({
  icon: Icon,
  children,
}: {
  icon: typeof Database;
  children: React.ReactNode;
}) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-secondary px-3 py-1 text-xs font-medium text-secondary-foreground">
      <Icon className="size-3.5" aria-hidden />
      {children}
    </span>
  );
}

export function AnswerCard({
  data,
  loading,
  error,
  onRetry,
}: {
  data: ChatResponse | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}) {
  return (
    <section
      aria-live="polite"
      className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8"
    >
      <div className="flex items-center gap-2">
        <Sparkles className="size-4 text-accent" aria-hidden />
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Copilot answer
        </h2>
      </div>

      {loading && (
        <div className="mt-5 space-y-3">
          <div className="h-4 w-full animate-pulse rounded-md bg-muted" />
          <div className="h-4 w-11/12 animate-pulse rounded-md bg-muted" />
          <div className="h-4 w-8/12 animate-pulse rounded-md bg-muted" />
          <div className="mt-5 flex gap-2">
            <div className="h-6 w-32 animate-pulse rounded-full bg-muted" />
            <div className="h-6 w-28 animate-pulse rounded-full bg-muted" />
          </div>
        </div>
      )}

      {!loading && error && (
        <div className="mt-5 rounded-xl border border-border bg-muted/40 p-5">
          <p className="text-sm font-medium text-foreground">{error}</p>
          <button
            type="button"
            onClick={onRetry}
            className="mt-4 inline-flex items-center gap-2 rounded-lg border border-input bg-background px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            <RotateCcw className="size-4" aria-hidden />
            Try again
          </button>
        </div>
      )}

      {!loading && !error && data && data.insufficiencies.length > 0 && (
        <div className="mt-5 rounded-xl border border-warning-border bg-warning-muted p-5">
          <div className="flex gap-3">
            <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warning" aria-hidden />
            <div className="space-y-1.5">
              {data.insufficiencies.map((item) => (
                <p key={item} className="text-sm font-medium text-warning-foreground">
                  {item}
                </p>
              ))}
            </div>
          </div>
        </div>
      )}

      {!loading && !error && data && data.insufficiencies.length === 0 && (
        <>
          <p className="mt-5 text-base leading-relaxed text-foreground">{data.answer}</p>
          <div className="mt-6 flex flex-wrap gap-2">
            <Pill icon={Database}>
              {data.citations.filter((c) => c.source_type === "customer_record").length}{" "}
              customer requests found
            </Pill>
            <Pill icon={Globe}>
              {data.citations.filter((c) => c.source_type !== "customer_record").length}{" "}
              live product source found
            </Pill>
            <Pill icon={Layers}>{routeLabels[data.route]}</Pill>
          </div>
        </>
      )}

      {!loading && !error && !data && (
        <p className="mt-5 text-sm text-muted-foreground">
          Ask a question to see a grounded answer with its sources.
        </p>
      )}
    </section>
  );
}
