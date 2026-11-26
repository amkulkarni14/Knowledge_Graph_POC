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
  path,
  focus,
}: {
  graph: Schema<"GraphView">;
  layout: string;
  onSelect: (id: string) => void;
  onEdge: (edge: JsonObject) => void;
  fitKey: number;
  path?: string[];
  focus?: string;
}) {
  const container = useRef<HTMLDivElement>(null);
  const instance = useRef<Core | null>(null);
  useEffect(() => {
    if (!container.current) return;
    const cy = cytoscape({
      container: container.current,
      elements: [
        ...graph.nodes.map((n) => ({
          classes: n.id === focus ? "entity-focus" : "",
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
            color: "#344054",
            "text-valign": "bottom",
            "text-margin-y": 6,
            width: 23,
            height: 23,
            "border-width": 2,
            "border-color": "#ffffff",
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.3,
            "line-color": "#c2cbd5",
            "target-arrow-color": "#c2cbd5",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(title)",
            "font-size": 7,
            color: "#667085",
            "text-background-color": "#fbfcfd",
            "text-background-opacity": 0.85,
          },
        },
        {
          selector: ".shortest-path",
          style: { "background-color": "#426e94", "line-color": "#426e94", "width": 4 },
        },
        {
          selector: ".entity-focus",
          style: { width: 34, height: 34, "border-width": 4, "border-color": "#426e94" },
        },
        {
          selector: ":selected",
          style: {
            "border-width": 4,
            "border-color": "#9a7b43",
            "line-color": "#9a7b43",
            "target-arrow-color": "#9a7b43",
          },
        },
      ],
      layout: { name: "preset" },
    });
    instance.current = cy;
    const arrangement = cy.layout({
      name: layout === "label-grid" ? "grid" : layout,
      animate: false,
      ...(focus && layout === "concentric" ? {
        concentric: (node: cytoscape.NodeSingular) => node.id() === focus ? 2 : 1,
        levelWidth: () => 1,
      } : {}),
      ...(layout === "label-grid" ? {
        sort: (left: cytoscape.NodeSingular, right: cytoscape.NodeSingular) =>
          String(left.data("label")).localeCompare(String(right.data("label"))) || left.id().localeCompare(right.id()),
      } : {}),
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
  }, [graph, layout, onSelect, onEdge, focus]);
  useEffect(() => {
    instance.current?.fit(undefined, 35);
  }, [fitKey]);
  useEffect(() => {
    const graphInstance = instance.current;
    if (!graphInstance) return;
    const vertices = new Set(path ?? []);
    const pairs = new Set(path?.slice(1).flatMap((node, index) => [
      JSON.stringify([path[index], node]), JSON.stringify([node, path[index]]),
    ]) ?? []);
    graphInstance.elements().removeClass("shortest-path");
    graphInstance.nodes().filter((node) => vertices.has(node.id())).addClass("shortest-path");
    graphInstance.edges().filter((edge) =>
      pairs.has(JSON.stringify([edge.source().id(), edge.target().id()])),
    ).addClass("shortest-path");
  }, [graph, layout, path]);
  return (
    <div
      ref={container}
      className="h-full w-full"
      role="img"
      aria-label={`Knowledge graph with ${graph.nodes.length} visible nodes and ${graph.edges.length} visible relationships. Use the node table for keyboard inspection.`}
    />
  );
}
