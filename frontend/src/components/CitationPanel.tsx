import { Database, ExternalLink, Globe } from "lucide-react";
import type { Citation } from "@/types";
import { EmptyState } from "./EmptyState";

function domainOf(url: string) {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

function SourceCard({ citation }: { citation: Citation }) {
  const isCustomer = citation.source_type === "customer_record";

  return (
    <article className="rounded-xl border border-border bg-card p-4 shadow-sm">
      <h4 className="text-sm font-semibold text-foreground">{citation.title}</h4>
      <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
        {citation.excerpt}
      </p>
      {citation.meta && citation.meta.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {citation.meta.map((chip) => (
            <span
              key={chip}
              className="rounded-md bg-secondary px-2 py-0.5 text-[11px] font-medium text-secondary-foreground"
            >
              {chip}
            </span>
          ))}
        </div>
      )}
      {!isCustomer && citation.url && (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
          <span className="text-[11px] font-medium text-muted-foreground">
            {domainOf(citation.url)}
          </span>
          <a
            href={citation.url}
            target="_blank"
            rel="noreferrer noopener"
            className="inline-flex items-center gap-1 rounded-md text-xs font-semibold text-accent underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            Open live source
            <ExternalLink className="size-3.5" aria-hidden />
          </a>
        </div>
      )}
    </article>
  );
}

export function CitationPanel({ citations }: { citations: Citation[] }) {
  const customer = citations.filter((c) => c.source_type === "customer_record");
  const live = citations.filter((c) => c.source_type !== "customer_record");

  return (
    <aside className="rounded-2xl border border-border bg-card/60 p-6 shadow-sm">
      <h2 className="text-lg font-semibold tracking-tight text-foreground">Evidence</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Every answer is linked to the records and pages used.
      </p>

      <section className="mt-6">
        <div className="flex items-center gap-2">
          <Database className="size-4 text-primary" aria-hidden />
          <h3 className="text-sm font-semibold text-primary">Customer Evidence</h3>
        </div>
        <div className="mt-3 space-y-3">
          {customer.length > 0 ? (
            customer.map((c) => <SourceCard key={c.id} citation={c} />)
          ) : (
            <EmptyState message="No matching customer records were found." />
          )}
        </div>
      </section>

      <section className="mt-7">
        <div className="flex items-center gap-2">
          <Globe className="size-4 text-accent" aria-hidden />
          <h3 className="text-sm font-semibold text-accent">Live FlytBase Evidence</h3>
        </div>
        <div className="mt-3 space-y-3">
          {live.length > 0 ? (
            live.map((c) => <SourceCard key={c.id} citation={c} />)
          ) : (
            <EmptyState message="No live FlytBase documentation or release-note evidence was found." />
          )}
        </div>
      </section>
    </aside>
  );
}
