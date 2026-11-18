import { LinearProgress } from "@mui/material";
import { useLocation } from "react-router-dom";
import type { Stage } from "../../types/common.types";
import { stageRoutes } from "../../constants/stages.constants";
export function StageStepper({
  stages,
  completed,
}: {
  stages: Stage[];
  completed: number[];
}) {
  const { pathname } = useLocation();
  const current = stages.find(
    (stage) =>
      stageRoutes[stage.no] === pathname ||
      (pathname === "/build" && stage.no === 10),
  );
  const count = stages.filter((stage) => completed.includes(stage.no)).length;
  return (
    <div className="workflow-bar" aria-label="Workflow progress">
      <div className="flex justify-between gap-3 mb-2">
        <span>
          {current ? <>Viewing: <strong>{current.title}</strong></> : "Workflow progress"}
        </span>
        <span>
          {count} of {stages.length} stages completed
        </span>
      </div>
      <LinearProgress
        aria-label="Completed workflow stages"
        variant="determinate"
        value={stages.length ? (count / stages.length) * 100 : 0}
      />
    </div>
  );
}
