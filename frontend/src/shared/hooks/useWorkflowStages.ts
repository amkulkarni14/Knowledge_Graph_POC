import { useQuery } from "@tanstack/react-query";
import { sessionsApi } from "../../api/sessionsApi";
import {
  prerequisites,
  stageGroups,
  stageOrder,
} from "../../constants/stages.constants";
import type { Stage } from "../../types/common.types";

export function activeWorkflow(stages: Stage[] = []) {
  const byId = new Map(stages.map((stage) => [stage.no, stage]));
  const order = stageOrder.filter((stage) => byId.has(stage));
  const groups = stageGroups
    .map((group) => ({
      ...group,
      numbers: group.numbers.filter((stage) => byId.has(stage)),
    }))
    .filter(({ numbers }) => numbers.length > 0);
  return {
    order,
    groups,
    enabled: (stage: number) => byId.has(stage),
    requires: (stage: number) =>
      byId.get(stage)?.prerequisites ?? prerequisites[stage] ?? [],
    validationOnly: stages.length > 0 && !byId.has(9),
  };
}

export function useWorkflowStages() {
  const query = useQuery({
    queryKey: ["stages"],
    queryFn: ({ signal }) => sessionsApi.stages(signal),
    staleTime: Infinity,
  });
  return { query, ...activeWorkflow(query.data) };
}
