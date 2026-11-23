import { useMemo, useState } from "react";
import { Button } from "@mui/material";
import { useIsMutating } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import { stageNavigation } from "../../constants/stageNavigation";
import { prerequisites } from "../../constants/stages.constants";
import type { Schema } from "../../types/common.types";
import { useSessionStore } from "../store";
import { buildPageSequence, locateStep, stepHref } from "./pageSequence";
import { pageSave } from "./pageSave";

/**
 * Footer shown on every page: Back goes to the previous sidebar entry, and
 * Save & Next runs the page's registered save (if any) before moving on.
 */
export function PageNavigation({
  workspace,
}: {
  workspace?: Schema<"SessionView">;
}) {
  const id = useSessionStore((s) => s.id);
  const { pathname, search } = useLocation();
  const navigate = useNavigate();
  const [saving, setSaving] = useState(false);
  const mutating =
    useIsMutating({ mutationKey: ["workspace-mutation", id] }) > 0;
  const steps = useMemo(() => buildPageSequence(Boolean(id)), [id]);
  const index = locateStep(steps, pathname, search);
  if (index < 0) return null;

  const previous = steps[index - 1];
  const next = steps[index + 1];
  const running = ["queued", "running", "cancelling", "publishing"].includes(
    String(workspace?.job?.status),
  );
  const busy = saving || mutating || running;
  const missing =
    next?.stage !== undefined
      ? prerequisites[next.stage].find(
          (required) => !workspace?.completed_stages.includes(required),
        )
      : undefined;
  const hint = running || mutating
    ? "Wait for the current operation to finish."
    : missing !== undefined && next
      ? `${next.label} needs ${stageNavigation[missing].title} to be completed first.`
      : null;

  async function saveAndNext() {
    setSaving(true);
    try {
      if (!(await (pageSave.current?.() ?? true))) return;
    } catch {
      // The page reports the failure itself; stay here so nothing is lost.
      return;
    } finally {
      setSaving(false);
    }
    navigate(next ? stepHref(next, pathname, search) : "/");
  }

  return (
    <nav aria-label="Page navigation" className="page-nav">
      <Button
        variant="outlined"
        startIcon={<ArrowLeft size={16} />}
        disabled={!previous || saving}
        onClick={() => previous && navigate(stepHref(previous, pathname, search))}
      >
        Back
      </Button>
      <div className="page-nav-end">
        {hint && <span className="muted">{hint}</span>}
        <Button
          variant="contained"
          endIcon={next ? <ArrowRight size={16} /> : undefined}
          disabled={busy}
          onClick={() => void saveAndNext()}
        >
          {next ? "Save & Next" : "Save & Finish"}
        </Button>
      </div>
    </nav>
  );
}
