"use client";

import { useCallback, useEffect, useState } from "react";
import { CorpusPanel } from "@/components/CorpusPanel";
import { Header } from "@/components/Header";
import { QueryPanel } from "@/components/QueryPanel";
import { ResultPanel } from "@/components/ResultPanel";
import {
  fetchDocuments,
  fetchHealth,
  fetchIngestStatus,
  type CorpusDocument,
  type IngestStatus,
  type QueryResult,
} from "@/lib/api";

export function Workspace() {
  const [healthy, setHealthy] = useState<boolean | null>(null);
  const [llmProvider, setLlmProvider] = useState<string | undefined>();
  const [status, setStatus] = useState<IngestStatus | null>(null);
  const [documents, setDocuments] = useState<CorpusDocument[]>([]);
  const [result, setResult] = useState<QueryResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ text: string; kind: "ok" | "error" } | null>(
    null,
  );

  const refresh = useCallback(async () => {
    const [nextStatus, nextDocs] = await Promise.all([
      fetchIngestStatus(),
      fetchDocuments(),
    ]);
    setStatus(nextStatus);
    setDocuments(nextDocs);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const health = await fetchHealth();
        if (cancelled) return;
        setHealthy(health.status === "ok");
        setLlmProvider(health.llm_provider);
        await refresh();
      } catch {
        if (!cancelled) {
          setHealthy(false);
          setMessage({
            text: "Backend offline — start FastAPI on :8000",
            kind: "error",
          });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  function onMessage(text: string, kind: "ok" | "error" = "ok") {
    setMessage({ text, kind });
  }

  const hasCorpus = (status?.documents ?? 0) > 0;

  return (
    <div className="min-h-screen bg-[radial-gradient(ellipse_at_top,_#0f2744_0%,_#020617_55%)] text-slate-100">
      <Header healthy={healthy} llmProvider={llmProvider} />
      <main className="mx-auto grid max-w-6xl gap-6 px-4 py-8 sm:px-6 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
        <div className="space-y-6">
          {message ? (
            <p
              className={`rounded-lg px-3 py-2 text-sm ${
                message.kind === "error"
                  ? "border border-rose-900/50 bg-rose-950/40 text-rose-200"
                  : "border border-emerald-900/40 bg-emerald-950/30 text-emerald-200"
              }`}
            >
              {message.text}
            </p>
          ) : null}
          <CorpusPanel
            status={status}
            documents={documents}
            busy={busy}
            onBusy={setBusy}
            onRefresh={refresh}
            onMessage={onMessage}
          />
          <QueryPanel
            busy={busy}
            disabled={!hasCorpus || healthy === false}
            onBusy={setBusy}
            onResult={setResult}
            onMessage={onMessage}
          />
        </div>
        <ResultPanel result={result} />
      </main>
    </div>
  );
}
