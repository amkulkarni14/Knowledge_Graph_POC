import { useEffect, useRef } from "react";
import cytoscape, { type Core } from "cytoscape";
import type { Schema, JsonObject } from "../../types/common.types";
import { colorForLabel } from "../../constants/stages.constants";
export default function GraphCanvas({
  graph,
  layout,
  onSelect,
  onEdge,
  fitKey,
}: {
  graph: Schema<"GraphView">;
  layout: string;
  onSelect: (id: string) => void;
  onEdge: (edge: JsonObject) => void;
  fitKey: number;
}) {
  const container = useRef<HTMLDivElement>(null);
  const instance = useRef<Core | null>(null);
  useEffect(() => {
    if (!container.current) return;
    const cy = cytoscape({
      container: container.current,
      elements: [
        ...graph.nodes.map((n) => ({
          data: {
            ...n.properties,
            id: n.id,
            title: n.id,
            color: colorForLabel(String(n.properties.label ?? "Entity")),
          },
        })),
        ...graph.edges.map((e, i) => ({
          data: {
            ...e.properties,
            id: `edge-${i}`,
            source: e.source,
            target: e.target,
            title: String(e.properties.type ?? e.properties.label ?? e.key),
            properties: e.properties,
            key: e.key,
          },
        })),
      ],
      style: [
        {
          selector: "node",
          style: {
            "background-color": "data(color)",
            label: "data(title)",
            "font-size": 9,
            color: "#33455d",
            "text-valign": "bottom",
            "text-margin-y": 6,
            width: 23,
            height: 23,
            "border-width": 2,
            "border-color": "#fff",
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.3,
            "line-color": "#a8b9cc",
            "target-arrow-color": "#a8b9cc",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(title)",
            "font-size": 7,
            color: "#617087",
            "text-background-color": "#fafcfe",
            "text-background-opacity": 0.85,
          },
        },
        {
          selector: ":selected",
          style: {
            "border-width": 4,
            "border-color": "#e3ad42",
            "line-color": "#d99b24",
            "target-arrow-color": "#d99b24",
          },
        },
      ],
      layout: { name: "preset" },
    });
    instance.current = cy;
    const arrangement = cy.layout({
      name: layout,
      animate: false,
    } as cytoscape.LayoutOptions);
    arrangement.run();
    cy.on("tap", "node", (e) => onSelect(e.target.id()));
    cy.on("tap", "edge", (e) => onEdge(e.target.data() as JsonObject));
    const observer = new ResizeObserver(() => {
      if (cy.destroyed()) return;
      cy.resize();
      cy.fit(undefined, 35);
    });
    observer.observe(container.current);
    return () => {
      observer.disconnect();
      arrangement.stop();
      cy.stop();
      cy.removeAllListeners();
      cy.destroy();
      instance.current = null;
    };
  }, [graph, layout, onSelect, onEdge]);
  useEffect(() => {
    instance.current?.fit(undefined, 35);
  }, [fitKey]);
  return (
    <div
      ref={container}
      className="h-full w-full"
      role="img"
      aria-label={`Knowledge graph with ${graph.nodes.length} visible nodes and ${graph.edges.length} visible relationships. Use the node table for keyboard inspection.`}
    />
  );
}
