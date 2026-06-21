"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export default function LogsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
        Request Logs
      </h1>

      <Card>
        <CardHeader>
          <CardTitle>Recent Requests</CardTitle>
        </CardHeader>
        <CardContent>
          <div
            className="flex h-48 items-center justify-center rounded-md"
            style={{ backgroundColor: "var(--bg-elevated-2)" }}
          >
            <p style={{ color: "var(--text-muted)" }}>
              No requests logged yet. Traffic will appear here in real-time.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
