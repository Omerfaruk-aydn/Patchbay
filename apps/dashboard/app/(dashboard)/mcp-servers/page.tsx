"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function MCPServersPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
          MCP Servers
        </h1>
        <Button>Connect Server</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Connected Servers</CardTitle>
        </CardHeader>
        <CardContent>
          <div
            className="flex h-32 items-center justify-center rounded-md"
            style={{ backgroundColor: "var(--bg-elevated-2)" }}
          >
            <p style={{ color: "var(--text-muted)" }}>
              No MCP servers connected yet. Connect Blender, GitHub, or your custom MCP server.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
