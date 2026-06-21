"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function PlaygroundPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
        Playground
      </h1>

      <Card>
        <CardHeader>
          <CardTitle>Test Your Models</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-4">
            <Input placeholder="Model (e.g. claude-opus-4-7, auto)" className="flex-1" />
            <Button>Send</Button>
          </div>
          <div
            className="min-h-[200px] rounded-md p-4"
            style={{ backgroundColor: "var(--bg-elevated-2)" }}
          >
            <p style={{ color: "var(--text-muted)" }}>
              Response will appear here...
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
