"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const navItems = [
  { href: "/overview", label: "Overview" },
  { href: "/providers", label: "Providers" },
  { href: "/routing-rules", label: "Routing" },
  { href: "/mcp-servers", label: "MCP" },
  { href: "/playground", label: "Playground" },
  { href: "/logs", label: "Logs" },
  { href: "/settings", label: "Settings" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="flex h-screen w-64 flex-col border-r"
      style={{
        backgroundColor: "var(--bg-elevated-1)",
        borderColor: "var(--border-subtle)",
      }}
    >
      <div className="flex h-16 items-center border-b px-6" style={{ borderColor: "var(--border-subtle)" }}>
        <Link href="/" className="flex items-center gap-2">
          <div
            className="flex h-8 w-8 items-center justify-center rounded-md text-sm font-bold"
            style={{ backgroundColor: "var(--accent-blue)", color: "var(--bg-base)" }}
          >
            P
          </div>
          <span className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>
            Patchbay
          </span>
        </Link>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-bg-elevated-3"
                  : "hover:bg-bg-elevated-2"
              )}
              style={{
                color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
              }}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t p-4" style={{ borderColor: "var(--border-subtle)" }}>
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          Patchbay v0.1.0
        </p>
      </div>
    </aside>
  );
}
