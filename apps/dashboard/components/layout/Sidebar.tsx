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
        backgroundColor: "#1f2335",
        borderColor: "#2f3549",
      }}
    >
      <div className="flex h-16 items-center border-b px-6" style={{ borderColor: "#2f3549" }}>
        <Link href="/" className="flex items-center gap-2">
          <div
            className="flex h-8 w-8 items-center justify-center rounded-md text-sm font-bold"
            style={{ backgroundColor: "#7aa2f7", color: "#1a1b26" }}
          >
            P
          </div>
          <span className="text-lg font-semibold" style={{ color: "#c0caf5" }}>
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
                "flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors"
              )}
              style={{
                color: isActive ? "#c0caf5" : "#9aa5ce",
                backgroundColor: isActive ? "#2a2e42" : "transparent",
              }}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t p-4" style={{ borderColor: "#2f3549" }}>
        <p className="text-xs" style={{ color: "#565f89" }}>
          Patchbay v0.1.0
        </p>
      </div>
    </aside>
  );
}
