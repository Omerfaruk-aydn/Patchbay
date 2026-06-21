"use client";

export function Header() {
  return (
    <header
      className="flex h-16 items-center justify-between border-b px-6"
      style={{
        backgroundColor: "#1f2335",
        borderColor: "#2f3549",
      }}
    >
      <div className="flex items-center gap-4">
        <h2 className="text-sm font-medium" style={{ color: "#9aa5ce" }}>
          Dashboard
        </h2>
      </div>

      <div className="flex items-center gap-4">
        <kbd
          className="inline-flex h-6 items-center gap-1 rounded border px-1.5 text-xs"
          style={{
            backgroundColor: "#24283b",
            borderColor: "#3b4261",
            color: "#565f89",
          }}
        >
          ⌘K
        </kbd>
      </div>
    </header>
  );
}
