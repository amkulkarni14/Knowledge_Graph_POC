import { guidedSources } from "../../features/sources/guidedSources";
import { useData } from "../../shared/hooks/useWorkspace";
import { useWorkflowStages } from "../../shared/hooks/useWorkflowStages";
import { Button } from "@mui/material";
import { useIsMutating } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { useUiStore } from "../store";
import { stageNavigation } from "../../constants/stageNavigation";
import { stageForPath, stageRoutes } from "../../constants/stages.constants";
import type { Schema } from "../../types/common.types";

export function StageContinuation({
  workspace,
}: {
  workspace: Schema<"SessionView">;
}) {
  const { pathname } = useLocation();
  const pending =
    useIsMutating({ mutationKey: ["workspace-mutation", workspace.id] }) > 0;
  const scopeDirty = useUiStore((state) => state.scopeDirty);
  const workflow = useWorkflowStages();
  const stage = stageForPath(pathname);
  const sourceCandidate = useData(
    ["source-candidate"],
    (signal) => guidedSources.candidate(workspace.id, signal),
    stage === 2,
  );
  const pendingSelection = stage === 2 && Boolean(sourceCandidate.data);
  if (!stage || !workflow.enabled(stage)) return null;

  const index = workflow.order.indexOf(stage);
  const next = workflow.order[index + 1];
  const previous = workflow.order[index - 1];
  const complete = workspace.completed_stages.includes(stage);
  const missing =
    next &&
    workflow
      .requires(next)
      .find((required) => !workspace.completed_stages.includes(required));
  const running = ["queued", "running", "cancelling", "publishing"].includes(
    String(workspace.job?.status),
  );
  const unsavedScope = stage === 1 && scopeDirty;
  const disabled =
    pending ||
    running ||
    unsavedScope ||
    pendingSelection ||
    !complete ||
    Boolean(missing);
  const label = next
    ? `Continue to ${stageNavigation[next].title}`
    : "Explore graph";
  const hint =
    pending || running
      ? "Wait for the current operation to finish."
      : pendingSelection
        ? "Confirm or cancel the pending source selection to continue."
        : unsavedScope
          ? "Save your scope changes to continue."
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
      {workflow.validationOnly &&
        previous &&
        (pending || running ? (
          <Button
            className="mr-auto"
            variant="outlined"
            startIcon={<ArrowLeft size={16} />}
            disabled
          >
            Back
          </Button>
        ) : (
          <Button
            className="mr-auto"
            component={Link}
            to={stageRoutes[previous]}
            variant="outlined"
            startIcon={<ArrowLeft size={16} />}
          >
            Back
          </Button>
        ))}
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
