"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
        Settings
      </h1>

      <Card>
        <CardHeader>
          <CardTitle>Project Settings</CardTitle>
        </CardHeader>
        <CardContent>
          <div
            className="flex h-32 items-center justify-center rounded-md"
            style={{ backgroundColor: "var(--bg-elevated-2)" }}
          >
            <p style={{ color: "var(--text-muted)" }}>
              Project configuration, API keys, and billing settings.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
