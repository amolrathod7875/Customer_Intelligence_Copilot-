export type SourceType = "customer_record" | "documentation" | "release_note";
export type QueryRoute = "customer" | "documentation" | "release_note" | "both";

export interface Citation {
  id: string;
  source_type: SourceType;
  title: string;
  excerpt: string;
  url: string | null;
  meta?: string[];
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
