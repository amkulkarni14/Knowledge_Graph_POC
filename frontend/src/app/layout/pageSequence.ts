import { publishedTools } from "../../constants/publishedTools";
import { stageNavigation } from "../../constants/stageNavigation";
import {
  stageForPath,
  stageOrder,
  stageRoutes,
} from "../../constants/stages.constants";

export type PageStep = {
  label: string;
  pathname: string;
  /** Value of the `view` query parameter, when the step is a sub-view. */
  view?: string;
  stage?: number;
};

/**
 * Every page and sub-view in left-sidebar order. Workflow stages and the
 * Graph Intelligence group only exist while a workspace is open, exactly like
 * the sidebar.
 */
export function buildPageSequence(hasWorkspace: boolean): PageStep[] {
  const steps: PageStep[] = [
    { label: "Home", pathname: "/" },
    { label: "Domains", pathname: "/domains" },
    { label: "Published Graphs", pathname: "/published-graphs" },
    ...publishedTools.map(({ view, label }) => ({
      label,
      pathname: "/published-graphs",
      view,
    })),
  ];
  if (hasWorkspace) {
    steps.push(
      ...stageOrder.map((stage) => ({
        label: stageNavigation[stage].title,
        pathname: stageRoutes[stage],
        stage,
      })),
      { label: "Graph Explorer", pathname: "/explorer" },
      { label: "Path Analysis", pathname: "/explorer", view: "path" },
      { label: "Graph Metrics", pathname: "/explorer", view: "metrics" },
    );
  }
  return steps;
}

/** Index of the step the current URL shows, or -1 when it is not in the sequence. */
export function locateStep(steps: PageStep[], pathname: string, search: string) {
  const view = new URLSearchParams(search).get("view");
  const stage = stageForPath(pathname);
  return steps.findIndex((step) => {
    if (step.stage !== undefined) return step.stage === stage;
    if (step.pathname !== pathname) return false;
    if (pathname === "/published-graphs") {
      // An unknown or missing view renders the default "Published Graphs" page.
      const known = publishedTools.some((tool) => tool.view === view);
      return step.view ? step.view === view : !known;
    }
    if (pathname === "/explorer") {
      return step.view
        ? step.view === view
        : view !== "path" && view !== "metrics";
    }
    return true;
  });
}

/** Link target for a step, keeping the project/version selection the sidebar keeps. */
export function stepHref(step: PageStep, pathname: string, search: string) {
  const params = new URLSearchParams(
    step.pathname === "/published-graphs" && pathname === "/published-graphs"
      ? search
      : "",
  );
  if (step.view) params.set("view", step.view);
  else params.delete("view");
  if (step.view !== "explorer") params.delete("node");
  const query = params.toString();
  return query ? `${step.pathname}?${query}` : step.pathname;
}
