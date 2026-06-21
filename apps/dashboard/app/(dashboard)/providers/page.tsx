"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const providers = [
  { name: "OpenAI", status: "healthy", models: 5 },
  { name: "Anthropic", status: "healthy", models: 4 },
  { name: "Google", status: "healthy", models: 3 },
];

export default function ProvidersPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
          Providers
        </h1>
        <Button>Add Provider</Button>
      </div>

      <div className="space-y-3">
        {providers.map((provider) => (
          <Card key={provider.name}>
            <CardContent className="flex items-center justify-between">
              <div>
                <p className="font-medium" style={{ color: "var(--text-primary)" }}>
                  {provider.name}
                </p>
                <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
                  {provider.models} models
                </p>
              </div>
              <div className="flex items-center gap-2">
                <div
                  className="h-2 w-2 rounded-full"
                  style={{
                    backgroundColor:
                      provider.status === "healthy"
                        ? "var(--accent-green)"
                        : "var(--accent-red)",
                  }}
                />
                <span className="text-sm capitalize" style={{ color: "var(--text-secondary)" }}>
                  {provider.status}
                </span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
