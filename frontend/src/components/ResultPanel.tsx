"use client";

import type { QueryResult } from "@/lib/api";

type Props = {
  result: QueryResult | null;
};

export function ResultPanel({ result }: Props) {
  if (!result) {
    return (
      <section className="rounded-xl border border-dashed border-slate-800 bg-slate-900/20 p-5 text-sm text-slate-500">
        Query results and discrepancy alerts will appear here.
      </section>
    );
  }

  const alerts = result.alerts ?? [];

  return (
    <section className="space-y-4">
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-300">
            Answer
          </h2>
          <p className="text-xs text-slate-500">
            intent: <span className="text-sky-300">{result.intent.intent}</span>
            {" · "}
            confidence: {(result.confidence.score * 100).toFixed(0)}%
            {" · "}
            numbers: {result.confidence.numeric_source}
          </p>
        </div>
        <p className="mt-3 whitespace-pre-wrap text-base leading-relaxed text-slate-100">
          {result.answer}
        </p>
        {result.explanation ? (
          <div className="mt-4 border-t border-slate-800 pt-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Explanation</p>
            <p className="mt-2 whitespace-pre-wrap text-sm text-slate-300">
              {result.explanation}
            </p>
          </div>
        ) : null}
      </div>

      if alerts.length > 0 ? (
        <div className="rounded-xl border border-rose-900/60 bg-rose-950/30 p-5">
          <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-rose-300">
            Discrepancy alerts
          </h2>
          {result.facts &&
          typeof result.facts === "object" &&
          result.facts !== null &&
          "review" in result.facts &&
          (result.facts as { review?: { recommendation?: string } }).review?.recommendation ? (
            <p className="mt-2 text-sm font-semibold text-rose-200">
              Recommendation:{" "}
              {
                (result.facts as { review?: { recommendation?: string } }).review
                  ?.recommendation
              }
            </p>
          ) : null}
          <div className="mt-3 overflow-auto">
            <table className="min-w-full text-left text-sm text-rose-50/90">
              <thead className="text-xs text-rose-200/70">
                <tr>
                  <th className="px-2 py-1">SKU</th>
                  <th className="px-2 py-1">Invoice</th>
                  <th className="px-2 py-1 text-right">Billed</th>
                  <th className="px-2 py-1 text-right">Received</th>
                  <th className="px-2 py-1">Period</th>
                </tr>
              </thead>
              <tbody>
                {alerts.map((alert) => (
                  <tr
                    key={`${alert.invoice_id}-${alert.sku}-${alert.report_period}`}
                    className="border-t border-rose-900/50"
                  >
                    <td className="px-2 py-2 font-mono text-xs">{alert.sku}</td>
                    <td className="px-2 py-2">{alert.invoice_id}</td>
                    <td className="px-2 py-2 text-right">{alert.invoice_qty}</td>
                    <td className="px-2 py-2 text-right">{alert.report_received_qty}</td>
                    <td className="px-2 py-2">{alert.report_period}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <ul className="mt-3 space-y-1 text-sm text-rose-100/80">
            {alerts.map((alert) => (
              <li key={`msg-${alert.invoice_id}-${alert.sku}`}>
                {alert.message ||
                  `${alert.invoice_id}: billed ${alert.invoice_qty}, received ${alert.report_received_qty}`}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
        <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-300">
          Sources
        </h2>
        <ul className="mt-3 space-y-2 text-sm text-slate-400">
          {uniqueSources(result).map((src) => (
            <li key={src.file} className="flex flex-wrap gap-2">
              <code className="rounded bg-slate-950 px-1.5 py-0.5 text-xs text-sky-300">
                {src.file}
              </code>
              <span>{src.docType}</span>
              <span className="text-slate-600">{src.channels}</span>
            </li>
          ))}
          {uniqueSources(result).length === 0 ? (
            <li>No retrieved chunks (ledger-only answer).</li>
          ) : null}
        </ul>
      </div>

      <details className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
        <summary className="cursor-pointer text-sm text-slate-400">
          Markdown dashboard
        </summary>
        <pre className="mt-3 overflow-auto whitespace-pre-wrap text-xs text-slate-400">
          {result.markdown}
        </pre>
      </details>
    </section>
  );
}

function uniqueSources(result: QueryResult) {
  const seen = new Set<string>();
  const out: Array<{ file: string; docType: string; channels: string }> = [];
  for (const src of result.sources || []) {
    const file = String(src.metadata?.source_file || src.chunk_id);
    if (seen.has(file)) continue;
    seen.add(file);
    out.push({
      file,
      docType: String(src.metadata?.doc_type || ""),
      channels: (src.channels || []).join(", "),
    });
  }
  return out;
}
