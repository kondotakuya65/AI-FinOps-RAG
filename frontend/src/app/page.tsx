import Image from "next/image";

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center gap-8 px-6 py-16">
        <div className="flex items-center gap-4">
          <Image
            src="/fav.png"
            alt="AI-FinOps-RAG"
            width={56}
            height={56}
            className="rounded-lg"
            priority
          />
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-sky-400/80">
              Portfolio sample
            </p>
            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
              AI-FinOps-RAG
            </h1>
          </div>
        </div>

        <p className="max-w-xl text-lg text-slate-300">
          Table-aware RAG for vendor invoices and product reports. Numbers come
          from a SQL ledger; the LLM explains discrepancies — it does not invent
          the math.
        </p>

        <ul className="space-y-2 text-sm text-slate-400">
          <li>Upload / query UI and discrepancy dashboard — next UI commits</li>
          <li>
            Backend health:{" "}
            <code className="rounded bg-slate-900 px-1.5 py-0.5 text-sky-300">
              http://localhost:8000/api/health
            </code>
          </li>
          <li>
            Docs:{" "}
            <code className="rounded bg-slate-900 px-1.5 py-0.5 text-sky-300">
              /docs
            </code>{" "}
            in the repo root
          </li>
        </ul>
      </div>
    </main>
  );
}
