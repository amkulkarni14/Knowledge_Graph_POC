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
  const current = stages.find((stage) => stageRoutes[stage.no] === pathname);
  const count = stages.filter((stage) => completed.includes(stage.no)).length;
  return (
    <div className="workflow-bar" aria-label="Workflow progress">
      <div className="flex justify-between gap-3 mb-2">
        <span>
          {current
            ? `Stage ${String(current.no).padStart(2, "0")} · ${current.title}`
            : "Knowledge graph workflow"}
        </span>
        <span>
          {count} of {stages.length} stages complete
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
