export default function Home() {
  return (
    <main className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <h1
          className="text-4xl font-bold"
          style={{ color: "var(--accent-blue)" }}
        >
          Patchbay
        </h1>
        <p className="mt-4 text-lg" style={{ color: "var(--text-secondary)" }}>
          Universal LLM Gateway & Orchestration Platform
        </p>
        <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
          Dashboard will be available at{" "}
          <a href="/overview" className="underline" style={{ color: "var(--accent-cyan)" }}>
            /overview
          </a>
        </p>
      </div>
    </main>
  );
}
