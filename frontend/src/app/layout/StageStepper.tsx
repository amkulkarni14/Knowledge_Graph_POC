import { LinearProgress } from "@mui/material";
import { useLocation } from "react-router-dom";
import type { Stage } from "../../types/common.types";
import { stageForPath, stagePosition } from "../../constants/stages.constants";
import { stageNavigation } from "../../constants/stageNavigation";
export function StageStepper({
  stages,
  completed,
}: {
  stages: Stage[];
  completed: number[];
}) {
  const { pathname } = useLocation();
  const current = stages.find((stage) => stage.no === stageForPath(pathname));
  const count = stages.filter((stage) => completed.includes(stage.no)).length;
  const percent = stages.length ? Math.round((count / stages.length) * 100) : 0;
  return (
    <div className="workflow-bar" aria-label="Workflow progress">
      <div className="flex justify-between gap-3 mb-2">
        <span>
          {current ? (
            <strong>
              Stage {stagePosition(current.no)} ·{" "}
              {stageNavigation[current.no]?.title ?? current.title}
            </strong>
          ) : (
            "Workflow progress"
          )}
        </span>
        <span>
          {count} of {stages.length} stages completed ({percent}%)
        </span>
      </div>
      <LinearProgress
        aria-label="Completed workflow stages"
        variant="determinate"
        value={percent}
      />
    </div>
  );
}
