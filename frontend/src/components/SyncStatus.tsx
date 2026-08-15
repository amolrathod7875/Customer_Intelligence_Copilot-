import { CheckCircle2, Loader2, RefreshCw } from "lucide-react";
import type { SyncSummary } from "@/types";

export function SyncButton({
  onSync,
  loading,
}: {
  onSync: () => void;
  loading: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onSync}
      disabled={loading}
      className="inline-flex items-center gap-2 rounded-xl border border-input bg-background px-4 py-2.5 text-sm font-semibold text-foreground shadow-sm transition-colors hover:bg-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
    >
      {loading ? (
        <Loader2 className="size-4 animate-spin" aria-hidden />
      ) : (
        <RefreshCw className="size-4" aria-hidden />
      )}
      Sync customer corpus
    </button>
  );
}

export function SyncStatusPill({
  summary,
  loading,
  error,
}: {
  summary: SyncSummary | null;
  loading: boolean;
  error: string | null;
}) {
  if (loading) {
    return (
      <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs font-medium text-muted-foreground">
        <Loader2 className="size-3.5 animate-spin" aria-hidden />
        Synchronizing customer corpus…
      </span>
    );
  }

  if (error) {
    return (
      <span className="inline-flex items-center gap-2 rounded-full border border-warning-border bg-warning-muted px-3 py-1 text-xs font-medium text-warning-foreground">
        {error}
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs font-medium text-muted-foreground">
      <CheckCircle2 className="size-3.5 text-accent" aria-hidden />
      Customer corpus ready ·{" "}
      {summary
        ? `Last synced ${new Date(summary.synced_at).toLocaleTimeString()}`
        : "Last synced just now"}
    </span>
  );
}

export function SyncResultCard({ summary }: { summary: SyncSummary }) {
  return (
    <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
      <div className="flex items-center gap-2">
        <CheckCircle2 className="size-4 text-accent" aria-hidden />
        <h3 className="text-sm font-semibold text-foreground">Corpus synchronized</h3>
      </div>
      <p className="mt-2 text-sm text-muted-foreground">
        {summary.created.toLocaleString()} new · {summary.updated.toLocaleString()} updated ·{" "}
        {summary.deleted.toLocaleString()} deleted · {summary.unchanged.toLocaleString()}{" "}
        unchanged
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        {new Date(summary.synced_at).toLocaleString()}
      </p>
    </div>
  );
}
