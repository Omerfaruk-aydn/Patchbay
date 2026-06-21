"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export default function RoutingRulesPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
        Routing Rules
      </h1>

      <Card>
        <CardHeader>
          <CardTitle>Active Routing Policies</CardTitle>
        </CardHeader>
        <CardContent>
          <div
            className="flex h-32 items-center justify-center rounded-md"
            style={{ backgroundColor: "var(--bg-elevated-2)" }}
          >
            <p style={{ color: "var(--text-muted)" }}>
              Configure routing strategies for cost, latency, and semantic optimization.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
