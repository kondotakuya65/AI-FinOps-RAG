"use client";

import Image from "next/image";

type Props = {
  healthy: boolean | null;
  llmProvider?: string;
};

export function Header({ healthy, llmProvider }: Props) {
  return (
    <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <div className="flex items-center gap-3">
          <Image
            src="/fav.png"
            alt="AI-FinOps-RAG"
            width={40}
            height={40}
            className="rounded-md"
            priority
          />
          <div>
            <p className="text-[11px] uppercase tracking-[0.22em] text-sky-400/80">
              Portfolio sample
            </p>
            <h1 className="text-lg font-semibold tracking-tight text-slate-50 sm:text-xl">
              AI-FinOps-RAG
            </h1>
          </div>
        </div>
        <div className="text-right text-xs text-slate-400">
          <p>
            API{" "}
            <span
              className={
                healthy === null
                  ? "text-slate-500"
                  : healthy
                    ? "text-emerald-400"
                    : "text-rose-400"
              }
            >
              {healthy === null ? "…" : healthy ? "online" : "offline"}
            </span>
          </p>
          {llmProvider ? <p className="mt-0.5">LLM: {llmProvider}</p> : null}
        </div>
      </div>
    </header>
  );
}
