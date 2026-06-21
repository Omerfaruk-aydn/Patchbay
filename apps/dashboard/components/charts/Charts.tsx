"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

interface ChartProps {
  title: string;
  data?: { label: string; value: number }[];
}

export function CostChart({ title, data = [] }: ChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm" style={{ color: "var(--text-secondary)" }}>
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div
          className="flex h-48 items-center justify-center rounded-md"
          style={{ backgroundColor: "var(--bg-elevated-2)" }}
        >
          <p style={{ color: "var(--text-muted)" }}>
            {data.length === 0 ? "No data yet" : `${data.length} data points`}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

export function LatencyChart({ title, data = [] }: ChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm" style={{ color: "var(--text-secondary)" }}>
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div
          className="flex h-48 items-center justify-center rounded-md"
          style={{ backgroundColor: "var(--bg-elevated-2)" }}
        >
          <p style={{ color: "var(--text-muted)" }}>
            {data.length === 0 ? "No data yet" : `${data.length} data points`}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

export function UsageChart({ title, data = [] }: ChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm" style={{ color: "var(--text-secondary)" }}>
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div
          className="flex h-48 items-center justify-center rounded-md"
          style={{ backgroundColor: "var(--bg-elevated-2)" }}
        >
          <p style={{ color: "var(--text-muted)" }}>
            {data.length === 0 ? "No data yet" : `${data.length} data points`}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
