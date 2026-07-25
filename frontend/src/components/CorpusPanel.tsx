"use client";

import { useRef, useState } from "react";
import type { CorpusDocument, IngestStatus, IngestSummary } from "@/lib/api";
import { loadFixtures, uploadDocuments } from "@/lib/api";

type Props = {
  status: IngestStatus | null;
  documents: CorpusDocument[];
  busy: boolean;
  onBusy: (value: boolean) => void;
  onRefresh: () => Promise<void>;
  onMessage: (message: string, kind?: "ok" | "error") => void;
};

export function CorpusPanel({
  status,
  documents,
  busy,
  onBusy,
  onRefresh,
  onMessage,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [lastSummary, setLastSummary] = useState<IngestSummary | null>(null);

  async function handleLoadFixtures(force: boolean) {
    onBusy(true);
    try {
      const summary = await loadFixtures(force);
      setLastSummary(summary);
      await onRefresh();
      onMessage(
        `Fixtures: ingested ${summary.ingested}, skipped ${summary.skipped}, errors ${summary.errors}`,
        summary.errors ? "error" : "ok",
      );
    } catch (err) {
      onMessage(err instanceof Error ? err.message : "Ingest failed", "error");
    } finally {
      onBusy(false);
    }
  }

  async function handleUpload(files: FileList | null) {
    if (!files?.length) return;
    onBusy(true);
    try {
      const summary = await uploadDocuments(files, false);
      setLastSummary(summary);
      await onRefresh();
      onMessage(
        `Upload: ingested ${summary.ingested}, skipped ${summary.skipped}, errors ${summary.errors}`,
        summary.errors ? "error" : "ok",
      );
    } catch (err) {
      onMessage(err instanceof Error ? err.message : "Upload failed", "error");
    } finally {
      onBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-300">
            Corpus
          </h2>
          <p className="mt-1 text-sm text-slate-400">
            Load demo fixtures or upload PDF / XLSX / DOCX.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={() => handleLoadFixtures(false)}
            className="rounded-md bg-sky-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-sky-500 disabled:opacity-50"
          >
            Load fixtures
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => handleLoadFixtures(true)}
            className="rounded-md border border-slate-600 px-3 py-1.5 text-sm text-slate-200 hover:border-slate-400 disabled:opacity-50"
          >
            Force re-ingest
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => inputRef.current?.click()}
            className="rounded-md border border-slate-600 px-3 py-1.5 text-sm text-slate-200 hover:border-slate-400 disabled:opacity-50"
          >
            Upload files
          </button>
          <input
            ref={inputRef}
            type="file"
            className="hidden"
            multiple
            accept=".pdf,.xlsx,.xls,.docx"
            onChange={(e) => handleUpload(e.target.files)}
          />
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Documents" value={status?.documents ?? 0} />
        <Stat label="Line items" value={status?.line_items ?? 0} />
        <Stat label="Invoices" value={status?.by_type?.invoice ?? 0} />
        <Stat label="Reports" value={status?.by_type?.report ?? 0} />
      </div>

      {lastSummary ? (
        <p className="mt-3 text-xs text-slate-500">
          Last run — ingested {lastSummary.ingested}, skipped {lastSummary.skipped},
          errors {lastSummary.errors}
          {lastSummary.uploaded?.length
            ? ` · uploaded ${lastSummary.uploaded.join(", ")}`
            : ""}
        </p>
      ) : null}

      <div className="mt-4 max-h-48 overflow-auto rounded-lg border border-slate-800">
        <table className="min-w-full text-left text-xs text-slate-300">
          <thead className="sticky top-0 bg-slate-900 text-slate-400">
            <tr>
              <th className="px-3 py-2 font-medium">File</th>
              <th className="px-3 py-2 font-medium">Type</th>
              <th className="px-3 py-2 font-medium">Vendor / ID</th>
              <th className="px-3 py-2 font-medium">Amount / period</th>
            </tr>
          </thead>
          <tbody>
            {documents.length === 0 ? (
              <tr>
                <td className="px-3 py-3 text-slate-500" colSpan={4}>
                  No documents yet — load fixtures to start the demo.
                </td>
              </tr>
            ) : (
              documents.map((doc) => (
                <tr key={doc.id} className="border-t border-slate-800/80">
                  <td className="px-3 py-2 font-mono text-[11px]">{doc.source_file}</td>
                  <td className="px-3 py-2">{doc.doc_type}</td>
                  <td className="px-3 py-2">
                    {doc.vendor || "—"}
                    {doc.invoice_id ? ` · ${doc.invoice_id}` : ""}
                  </td>
                  <td className="px-3 py-2">
                    {doc.total_amount != null
                      ? `${doc.total_amount} ${doc.currency || ""}`
                      : doc.period || doc.payment_terms || "—"}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/50 px-3 py-2">
      <p className="text-[11px] uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-xl font-semibold text-slate-100">{value}</p>
    </div>
  );
}
