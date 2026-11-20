import { useState } from "react";
import { Button, Drawer, IconButton, TextField } from "@mui/material";
import { useMutation } from "@tanstack/react-query";
import { Sparkles, X } from "lucide-react";
import { send, sessionPath } from "../../api/client";
import { stageNavigation } from "../../constants/stageNavigation";
import { Feedback } from "../../shared/ui/WorkspaceUi";
import type { Schema } from "../../types/common.types";

const explorerTitles: Record<number, string> = {
  17: "Graph Explorer",
  18: "Path Analysis",
  19: "Graph Metrics",
};

export function StageHelp({ id, stage }: { id: string; stage: number }) {
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const title = stageNavigation[stage]?.title ?? explorerTitles[stage];
  const advice = useMutation({
    mutationFn: (prompt: string) =>
      send<Schema<"StageAdvice">>(
        "POST",
        sessionPath(id, `/stage-advice/${stage}`),
        { question: prompt },
      ),
    gcTime: 0,
  });

  return (
    <>
      <Button
        size="small"
        onClick={() => setOpen(true)}
        aria-label="AI stage help"
        startIcon={<Sparkles size={15} />}
      >
        <span className="hidden sm:inline">AI stage help</span>
      </Button>
      <Drawer
        anchor="right"
        open={open}
        onClose={() => setOpen(false)}
        slotProps={{
          paper: {
            role: "dialog",
            "aria-labelledby": "stage-help-title",
            sx: { width: "min(100vw, 440px)", p: 3 },
          },
        }}
      >
        <div className="flex items-start justify-between gap-3 mb-4">
          <div>
            <h2 id="stage-help-title">AI stage help</h2>
            <p className="muted">{title}</p>
          </div>
          <IconButton
            aria-label="Close AI stage help"
            onClick={() => setOpen(false)}
          >
            <X size={18} />
          </IconButton>
        </div>
        <form
          className="form-stack"
          onSubmit={(event) => {
            event.preventDefault();
            advice.mutate(question.trim());
          }}
        >
          <p className="muted">
            Get suggestions using workflow counts and status. Groq receives
            those summaries and any question you enter. Leave credentials and
            sensitive data out of your question.
          </p>
          <TextField
            label="Question (optional)"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            multiline
            minRows={3}
            slotProps={{ htmlInput: { maxLength: 600 } }}
            placeholder="What should I check before continuing?"
          />
          <Button variant="contained" type="submit" disabled={advice.isPending}>
            Get stage suggestions
          </Button>
          <Feedback pending={advice.isPending} error={advice.error} />
        </form>
        {advice.data && !advice.isPending && !advice.isError && (
          <section className="mt-5" aria-live="polite">
            <h3>
              {advice.data.mode === "ai" ? "AI suggestions" : "Stage checklist"}
            </h3>
            {advice.data.notice && (
              <p className="muted mt-2">{advice.data.notice}</p>
            )}
            <ul className="list-disc pl-5 mt-2 space-y-2">
              {advice.data.suggestions.map((suggestion, index) => (
                <li key={index}>{suggestion}</li>
              ))}
            </ul>
          </section>
        )}
      </Drawer>
    </>
  );
}
