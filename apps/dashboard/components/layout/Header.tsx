"use client";

export function Header() {
  return (
    <header
      className="flex h-16 items-center justify-between border-b px-6"
      style={{
        backgroundColor: "var(--bg-elevated-1)",
        borderColor: "var(--border-subtle)",
      }}
    >
      <div className="flex items-center gap-4">
        <h2 className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
          Dashboard
        </h2>
      </div>

      <div className="flex items-center gap-4">
        <kbd
          className="inline-flex h-6 items-center gap-1 rounded border px-1.5 text-xs"
          style={{
            backgroundColor: "var(--bg-elevated-2)",
            borderColor: "var(--border-strong)",
            color: "var(--text-muted)",
          }}
        >
          ⌘K
        </kbd>
      </div>
    </header>
  );
}
