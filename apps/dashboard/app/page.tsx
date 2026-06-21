export default function Home() {
  return (
    <main
      className="flex min-h-screen items-center justify-center"
      style={{ backgroundColor: "#1a1b26", color: "#c0caf5" }}
    >
      <div className="text-center">
        <h1 className="text-4xl font-bold" style={{ color: "#7aa2f7" }}>
          Patchbay
        </h1>
        <p className="mt-4 text-lg" style={{ color: "#9aa5ce" }}>
          Universal LLM Gateway & Orchestration Platform
        </p>
        <p className="mt-2 text-sm" style={{ color: "#565f89" }}>
          Dashboard will be available at{" "}
          <a href="/overview" className="underline" style={{ color: "#7dcfff" }}>
            /overview
          </a>
        </p>
      </div>
    </main>
  );
}
