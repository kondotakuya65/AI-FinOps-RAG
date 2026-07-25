"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import { DEMO_QUESTIONS, askQuestion, type QueryResult } from "@/lib/api";

type Props = {
  busy: boolean;
  disabled: boolean;
  onBusy: (value: boolean) => void;
  onResult: (result: QueryResult) => void;
  onMessage: (message: string, kind?: "ok" | "error") => void;
};

export function QueryPanel({ busy, disabled, onBusy, onResult, onMessage }: Props) {
  const [question, setQuestion] = useState<string>(DEMO_QUESTIONS[1]);
  const [useLlm, setUseLlm] = useState(false);

  async function run(q: string) {
    const trimmed = q.trim();
    if (trimmed.length < 3) {
      onMessage("Enter a question (at least 3 characters).", "error");
      return;
    }
    onBusy(true);
    try {
      const result = await askQuestion(trimmed, useLlm);
      onResult(result);
      onMessage("Query complete.", "ok");
    } catch (err) {
      onMessage(err instanceof Error ? err.message : "Query failed", "error");
    } finally {
      onBusy(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void run(question);
  }

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
      <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-300">
        Ask FinOps
      </h2>
      <p className="mt-1 text-sm text-slate-400">
        Totals and qty checks come from the SQL ledger; the LLM only explains.
      </p>

      <form onSubmit={onSubmit} className="mt-4 space-y-3">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={3}
          disabled={busy || disabled}
          className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none ring-sky-500/40 placeholder:text-slate-600 focus:ring-2 disabled:opacity-50"
          placeholder="How much did we spend on Vendor Alpha in Q3?"
        />
        <div className="flex flex-wrap items-center justify-between gap-3">
          <label className="flex items-center gap-2 text-sm text-slate-400">
            <input
              type="checkbox"
              checked={useLlm}
              onChange={(e) => setUseLlm(e.target.checked)}
              className="rounded border-slate-600"
            />
            Use LLM explanation
            <span className="text-slate-600">(optional — ledger answers work without it)</span>
          </label>
          <button
            type="submit"
            disabled={busy || disabled}
            className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
          >
            {busy ? "Running…" : "Run query"}
          </button>
        </div>
      </form>

      <div className="mt-4 flex flex-wrap gap-2">
        {DEMO_QUESTIONS.map((demo) => (
          <button
            key={demo}
            type="button"
            disabled={busy || disabled}
            onClick={() => {
              setQuestion(demo);
              void run(demo);
            }}
            className="rounded-full border border-slate-700 px-3 py-1 text-left text-xs text-slate-300 hover:border-sky-500/60 hover:text-sky-200 disabled:opacity-50"
          >
            {demo}
          </button>
        ))}
      </div>
      {disabled ? (
        <p className="mt-3 text-xs text-amber-400/90">
          Load fixtures (or upload docs) before querying.
        </p>
      ) : null}
    </section>
  );
}
