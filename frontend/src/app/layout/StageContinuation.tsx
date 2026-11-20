import { Button } from "@mui/material";
import { useIsMutating } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { stageNavigation } from "../../constants/stageNavigation";
import {
  prerequisites,
  stageForPath,
  stageOrder,
  stagePosition,
  stageRoutes,
} from "../../constants/stages.constants";
import type { Schema } from "../../types/common.types";

export function StageContinuation({
  workspace,
}: {
  workspace: Schema<"SessionView">;
}) {
  const { pathname } = useLocation();
  const pending =
    useIsMutating({ mutationKey: ["workspace-mutation", workspace.id] }) > 0;
  const stage = stageForPath(pathname);
  if (!stage) return null;

  const next = stageOrder[stagePosition(stage)];
  const complete = workspace.completed_stages.includes(stage);
  const missing =
    next &&
    prerequisites[next].find(
      (required) => !workspace.completed_stages.includes(required),
    );
  const running = ["queued", "running", "cancelling", "publishing"].includes(
    String(workspace.job?.status),
  );
  const disabled = pending || running || !complete || Boolean(missing);
  const label = next
    ? `Continue to ${stageNavigation[next].title}`
    : "Explore graph";
  const hint =
    pending || running
      ? "Wait for the current operation to finish."
      : !complete
        ? `Complete ${stageNavigation[stage].title} to continue.`
        : missing
          ? `Complete ${stageNavigation[missing].title} to continue.`
          : null;

  return (
    <nav
      aria-label="Workflow navigation"
      className="mt-6 flex flex-wrap items-center justify-end gap-3 border-t border-slate-200 pt-4"
    >
      {hint && <p className="muted">{hint}</p>}
      {disabled ? (
        <Button variant="contained" endIcon={<ArrowRight size={16} />} disabled>
          {label}
        </Button>
      ) : (
        <Button
          component={Link}
          to={next ? stageRoutes[next] : "/explorer"}
          variant="contained"
          endIcon={<ArrowRight size={16} />}
        >
          {label}
        </Button>
      )}
    </nav>
  );
}
