export type IngestStatus = {
  documents: number;
  line_items: number;
  by_type: Record<string, number>;
};

export type CorpusDocument = {
  id: number;
  source_file: string;
  doc_type: string;
  vendor: string | null;
  invoice_id: string | null;
  total_amount: number | null;
  currency: string | null;
  period: string | null;
  invoice_date: string | null;
  payment_terms: string | null;
  chunk_count: number;
  line_item_count: number;
};

export type IngestSummary = {
  ingested: number;
  skipped: number;
  errors: number;
  results?: Array<{
    source_file: string;
    status: string;
    detail?: string | null;
  }>;
  uploaded?: string[];
  rejected?: Array<{ file: string; reason: string }>;
};

export type DiscrepancyAlert = {
  severity: string;
  sku: string;
  invoice_id: string;
  invoice_qty: number;
  report_received_qty: number;
  report_period: string;
  vendor?: string | null;
  delta?: number;
  message?: string;
};

export type QueryResult = {
  question: string;
  answer: string;
  explanation?: string | null;
  markdown: string;
  intent: {
    intent: string;
    vendor?: string | null;
    sku?: string | null;
    invoice_id?: string | null;
    period?: string | null;
    min_total?: number | null;
  };
  facts: Record<string, unknown>;
  alerts: DiscrepancyAlert[];
  sources: Array<{
    chunk_id: string;
    text: string;
    metadata: Record<string, unknown>;
    channels: string[];
  }>;
  confidence: {
    score: number;
    numeric_source: string;
    llm_role: string;
    llm_status: string;
  };
  query_run_id?: number;
};

async function readError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data?.detail === "string") return data.detail;
    return JSON.stringify(data);
  } catch {
    return res.statusText || `HTTP ${res.status}`;
  }
}

export async function fetchHealth(): Promise<{ status: string; llm_provider?: string }> {
  const res = await fetch("/api/health", { cache: "no-store" });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchIngestStatus(): Promise<IngestStatus> {
  const res = await fetch("/api/ingest/status", { cache: "no-store" });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchDocuments(): Promise<CorpusDocument[]> {
  const res = await fetch("/api/ingest/documents", { cache: "no-store" });
  if (!res.ok) throw new Error(await readError(res));
  const data = await res.json();
  return data.documents ?? [];
}

export async function loadFixtures(force = false): Promise<IngestSummary> {
  const res = await fetch("/api/ingest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ load_fixtures: true, force }),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function uploadDocuments(files: FileList | File[], force = false): Promise<IngestSummary> {
  const form = new FormData();
  Array.from(files).forEach((file) => form.append("files", file));
  const url = force ? "/api/ingest/upload?force=true" : "/api/ingest/upload";
  const res = await fetch(url, { method: "POST", body: form });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function askQuestion(question: string, useLlm = true): Promise<QueryResult> {
  const res = await fetch("/api/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, use_llm: useLlm }),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export const DEMO_QUESTIONS = [
  "How much did we spend on Vendor Alpha in Q3?",
  "Are there quantity mismatches between invoices and product reports for SKU-1001?",
  "Which invoices are over $5,000?",
  "What are the payment terms for Alpha Supplies?",
  "Did we receive everything billed on INV-201?",
  "Are there quantity mismatches between invoices and product reports?",
  "Should we accept INV-104 against the Alpha contract and PO-4452?",
] as const;
