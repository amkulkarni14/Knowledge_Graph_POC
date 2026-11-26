import { BookOpen, ChartNoAxesCombined, Compass, Shapes } from "lucide-react";

export const publishedGraphViews = [
  { view: "explorer", label: "Published Graph Explorer", icon: Compass },
  { view: "query", label: "Query Workbench", icon: BookOpen },
  { view: "analytics", label: "Graph Analytics", icon: ChartNoAxesCombined },
  { view: "schema", label: "Graph Schema", icon: Shapes },
] as const;
