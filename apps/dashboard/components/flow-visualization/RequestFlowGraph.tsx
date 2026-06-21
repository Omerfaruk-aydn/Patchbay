"use client";

import { useEffect, useRef } from "react";
import * as d3 from "d3";

interface FlowNode {
  id: string;
  label: string;
  x: number;
  y: number;
}

interface FlowLink {
  source: string;
  target: string;
}

const nodes: FlowNode[] = [
  { id: "client", label: "Client", x: 100, y: 200 },
  { id: "gateway", label: "Gateway", x: 300, y: 200 },
  { id: "routing", label: "Routing", x: 500, y: 200 },
  { id: "openai", label: "OpenAI", x: 700, y: 100 },
  { id: "anthropic", label: "Anthropic", x: 700, y: 200 },
  { id: "google", label: "Google", x: 700, y: 300 },
  { id: "mcp", label: "MCP Server", x: 500, y: 350 },
];

const links: FlowLink[] = [
  { source: "client", target: "gateway" },
  { source: "gateway", target: "routing" },
  { source: "routing", target: "openai" },
  { source: "routing", target: "anthropic" },
  { source: "routing", target: "google" },
  { source: "gateway", target: "mcp" },
];

export function RequestFlowGraph() {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const width = 800;
    const height = 450;

    // Links
    const linkGroup = svg.append("g");
    links.forEach((link) => {
      const source = nodes.find((n) => n.id === link.source)!;
      const target = nodes.find((n) => n.id === link.target)!;
      linkGroup
        .append("line")
        .attr("x1", source.x)
        .attr("y1", source.y)
        .attr("x2", target.x)
        .attr("y2", target.y)
        .attr("stroke", "#2f3549")
        .attr("stroke-width", 2);
    });

    // Nodes
    const nodeGroup = svg.append("g");
    nodes.forEach((node) => {
      const g = nodeGroup.append("g").attr("transform", `translate(${node.x},${node.y})`);

      g.append("circle")
        .attr("r", 24)
        .attr("fill", "#1f2335")
        .attr("stroke", "#7aa2f7")
        .attr("stroke-width", 2);

      g.append("text")
        .text(node.label)
        .attr("text-anchor", "middle")
        .attr("dy", "0.35em")
        .attr("fill", "#c0caf5")
        .attr("font-size", "10px")
        .attr("font-family", "Inter, sans-serif");
    });

    // Animate a particle
    function animateParticle() {
      const path = [
        nodes.find((n) => n.id === "client")!,
        nodes.find((n) => n.id === "gateway")!,
        nodes.find((n) => n.id === "routing")!,
        nodes[Math.floor(Math.random() * 3) + 3], // random provider
      ];

      const particle = svg
        .append("circle")
        .attr("r", 4)
        .attr("fill", "#7aa2f7")
        .attr("cx", path[0].x)
        .attr("cy", path[0].y);

      let i = 0;
      function step() {
        if (i >= path.length - 1) {
          particle.remove();
          return;
        }
        particle
          .transition()
          .duration(400)
          .attr("cx", path[i + 1].x)
          .attr("cy", path[i + 1].y)
          .on("end", () => {
            i++;
            step();
          });
      }
      step();
    }

    const interval = setInterval(animateParticle, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <svg
      ref={svgRef}
      viewBox="0 0 800 450"
      className="w-full rounded-lg"
      style={{ backgroundColor: "var(--bg-elevated-2)" }}
    />
  );
}
