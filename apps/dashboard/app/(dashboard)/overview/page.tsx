"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { RequestFlowGraph } from "@/components/flow-visualization/RequestFlowGraph";

export default function OverviewPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
        Overview
      </h1>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Total Requests", value: "0", color: "var(--accent-blue)" },
          { label: "Total Cost", value: "$0.00", color: "var(--accent-green)" },
          { label: "Cache Hit Rate", value: "0%", color: "var(--accent-teal)" },
          { label: "Avg Latency", value: "0ms", color: "var(--accent-cyan)" },
        ].map((stat) => (
          <Card key={stat.label}>
            <CardHeader>
              <CardTitle className="text-sm" style={{ color: "var(--text-secondary)" }}>
                {stat.label}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold mono" style={{ color: stat.color }}>
                {stat.value}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Live Request Flow</CardTitle>
        </CardHeader>
        <CardContent>
          <RequestFlowGraph />
        </CardContent>
      </Card>
    </div>
  );
}
