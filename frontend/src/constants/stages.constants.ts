// Mirrors server PREREQUISITES for advisory action disabling only; the server is authoritative.
export const prerequisites: Record<number, number[]> = {
  1: [],
  2: [],
  3: [2, 1],
  4: [3],
  5: [3, 4],
  6: [5],
  7: [5, 6],
  8: [7],
  9: [8],
  10: [3, 9],
  11: [10],
  12: [11],
  13: [12],
  14: [13],
  15: [14],
  16: [14, 15],
};
export const stageRoutes: Record<number, string> = {
  1: "/scope",
  2: "/sources",
  3: "/metadata",
  4: "/analysis",
  5: "/ontology",
  6: "/suggestions",
  7: "/review",
  8: "/validation",
  9: "/repository",
  10: "/build/10",
  11: "/build/11",
  12: "/build/12",
  13: "/build/13",
  14: "/build/14",
  15: "/build/15",
  16: "/storage",
};
export const graphColors = [
  "#6d9693",
  "#7892aa",
  "#aa8d65",
  "#8c879b",
  "#ad7f83",
  "#728f8e",
];
export function colorForLabel(label: string) {
  return graphColors[
    Array.from(label).reduce(
      (hash, c) => (hash * 31 + c.charCodeAt(0)) >>> 0,
      0,
    ) % graphColors.length
  ];
}

export const stageGroups = [
  { title: "Data & Metadata", numbers: [2, 1, 3, 4] },
  { title: "Ontology Engineering", numbers: [5, 6, 7, 8, 9] },
  { title: "Graph Construction", numbers: [10, 11, 12, 13, 14, 15, 16] },
];

export const stageOrder = stageGroups.flatMap(({ numbers }) => numbers);
export function stagePosition(stage: number) {
  return stageOrder.indexOf(stage) + 1;
}
