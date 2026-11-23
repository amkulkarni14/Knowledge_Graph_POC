import {
  Activity,
  BookOpen,
  ChartNoAxesCombined,
  Compass,
  HardDrive,
  Shapes,
  Sparkles,
  type LucideIcon,
} from "lucide-react";

// Sub-views of /published-graphs, in left-sidebar order.
export const publishedTools: { view: string; label: string; icon: LucideIcon }[] = [
  { view: "explorer", label: "Published Graph Explorer", icon: Compass },
  { view: "query", label: "Query Workbench", icon: BookOpen },
  { view: "analytics", label: "Graph Analytics", icon: ChartNoAxesCombined },
  { view: "schema", label: "Graph Schema", icon: Shapes },
  { view: "operations", label: "Graph Operations", icon: Activity },
  { view: "intelligence", label: "Graph Intelligence", icon: Sparkles },
  { view: "graphml", label: "GraphML Import", icon: HardDrive },
];
