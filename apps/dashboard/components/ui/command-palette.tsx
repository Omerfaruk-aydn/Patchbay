"use client";

import React, { useEffect, useState } from "react";

interface Command {
  id: string;
  name: string;
  shortcut?: string;
  action: () => void;
}

const commands: Command[] = [
  { id: "overview", name: "Go to Overview", shortcut: "g o", action: () => {} },
  { id: "providers", name: "Go to Providers", shortcut: "g p", action: () => {} },
  { id: "routing", name: "Go to Routing Rules", shortcut: "g r", action: () => {} },
  { id: "mcp", name: "Go to MCP Servers", shortcut: "g m", action: () => {} },
  { id: "playground", name: "Go to Playground", shortcut: "g l", action: () => {} },
  { id: "logs", name: "Go to Logs", shortcut: "g g", action: () => {} },
  { id: "settings", name: "Go to Settings", shortcut: "g s", action: () => {} },
  { id: "new-key", name: "Create New API Key", action: () => {} },
  { id: "connect-mcp", name: "Connect MCP Server", action: () => {} },
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const filtered = commands.filter((c) =>
    c.name.toLowerCase().includes(query.toLowerCase())
  );

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]"
      onClick={() => setOpen(false)}
      style={{ backgroundColor: "rgba(0,0,0,0.5)" }}
    >
      <div
        className="w-full max-w-lg rounded-lg border p-2"
        style={{
          backgroundColor: "#24283b",
          borderColor: "#3b4261",
          boxShadow: "0 0 24px rgba(122, 162, 247, 0.25)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <input
          autoFocus
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Type a command..."
          className="w-full border-none bg-transparent p-3 text-sm outline-none"
          style={{ color: "#c0caf5" }}
        />
        <div className="max-h-64 overflow-y-auto">
          {filtered.map((cmd) => (
            <button
              key={cmd.id}
              className="flex w-full items-center justify-between rounded-md px-3 py-2 text-sm"
              style={{ color: "#9aa5ce" }}
              onClick={() => {
                setOpen(false);
              }}
            >
              <span>{cmd.name}</span>
              {cmd.shortcut && (
                <kbd
                  className="text-xs"
                  style={{ color: "#565f89" }}
                >
                  {cmd.shortcut}
                </kbd>
              )}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
