import { Loader2, SendHorizontal } from "lucide-react";
import { DemoQuestions } from "./DemoQuestions";

export function ChatPanel({
  question,
  onQuestionChange,
  onSubmit,
  loading,
}: {
  question: string;
  onQuestionChange: (value: string) => void;
  onSubmit: (question: string) => void;
  loading: boolean;
}) {
  const canSubmit = question.trim().length > 0 && !loading;

  return (
    <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
      <h2 className="text-xl font-semibold tracking-tight text-foreground">
        Ask the knowledge base
      </h2>
      <p className="mt-1.5 text-sm text-muted-foreground">
        Search customer history, product documentation, and release notes in one place.
      </p>

      <form
        className="mt-6"
        onSubmit={(event) => {
          event.preventDefault();
          if (canSubmit) onSubmit(question.trim());
        }}
      >
        <label htmlFor="question" className="text-sm font-medium text-foreground">
          Ask a question
        </label>
        <textarea
          id="question"
          value={question}
          onChange={(event) => onQuestionChange(event.target.value)}
          rows={3}
          placeholder="e.g. Which accounts requested geofencing, and is it currently supported?"
          className="mt-2 w-full resize-none rounded-xl border border-input bg-background px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus-visible:border-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
        />

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="submit"
            disabled={!canSubmit}
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground shadow-sm transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="size-4 animate-spin" aria-hidden />
            ) : (
              <SendHorizontal className="size-4" aria-hidden />
            )}
            Ask Copilot
          </button>
          {loading && (
            <span className="text-sm text-muted-foreground" role="status">
              Searching relevant evidence…
            </span>
          )}
        </div>
      </form>

      <div className="mt-6">
        <DemoQuestions
          disabled={loading}
          onSelect={(demo) => {
            onQuestionChange(demo);
            onSubmit(demo);
          }}
        />
      </div>
    </section>
  );
}
