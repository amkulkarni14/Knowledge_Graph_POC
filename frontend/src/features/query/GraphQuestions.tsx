import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Alert, Button, TextField } from "@mui/material";
import { create } from "zustand";
import { api, get, sessionPath } from "../../api/client";
import { DataTable, Feedback } from "../../shared/ui/WorkspaceUi";
import type { GraphSelection, Schema } from "../../types/common.types";
import { Bars } from "./InsightsCharts";

type Answer = Schema<"GraphAnswer">;
type Question = { question: string; previous_question?: string };
const emptyHistory: Question[] = [];
const useQuestionHistory = create<{
  entries: Record<string, Question[]>;
  remember: (key: string, entry: Question) => void;
}>((set) => ({
  entries: {},
  remember: (key, entry) => set(({ entries }) => ({
    entries: Object.fromEntries([
      ...Object.entries(entries).filter(([existing]) => existing !== key),
      [key, [entry, ...(entries[key] ?? []).filter((item) => item.question !== entry.question)].slice(0, 8)],
    ].slice(-12)),
  })),
}));

export default function GraphQuestions({ id, selection, scope, enabled, showGraph }: {
  id: string;
  selection: GraphSelection;
  scope: string;
  enabled: boolean;
  showGraph: (graph: Schema<"GraphView">) => void;
}) {
  const [question, setQuestion] = useState("");
  const [open, setOpen] = useState(false);
  const history = useQuestionHistory((state) => state.entries[scope] ?? emptyHistory);
  const remember = useQuestionHistory((state) => state.remember);
  const suggestions = useQuery({
    queryKey: ["workspace", id, "graph-question-suggestions", scope],
    queryFn: ({ signal }) => get<string[]>(sessionPath(id, "/graphs/questions/suggestions"), selection, signal),
    enabled: enabled && open,
    staleTime: 60000,
    retry: false,
  });
  const availability = useQuery({
    queryKey: ["workspace", id, "graph-question-provider"],
    queryFn: ({ signal }) => get<{provider: string; ready: boolean; message: string | null; fallback: boolean}>(
      sessionPath(id, "/graphs/questions/provider"), undefined, signal,
    ),
    enabled: enabled && open,
    retry: false,
    staleTime: 15000,
  });
  const request = useMutation({
    mutationFn: async (body: Question) => {
      const response = await api.post<{data: Answer}>(
        sessionPath(id, "/graphs/questions"), { ...selection, ...body }, { timeout: 85000 },
      );
      return response.data.data;
    },
    onSuccess: (_result, body) => remember(scope, body),
  });
  const answer = request.data;
  const counts = new Map<string, number>();
  for (const node of answer?.graph.nodes ?? []) {
    const label = String(node.properties.label ?? "Entity");
    counts.set(label, (counts.get(label) ?? 0) + 1);
  }
  return (
    <details className="panel mt-5" onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary className="cursor-pointer font-semibold">Ask Your Knowledge Graph</summary>
      {!enabled ? <p className="muted mt-3">Build a graph or select a saved snapshot to ask questions.</p> : (
        <div className="form-stack mt-4">
          {availability.data && (
            <p className="muted">
              Provider: {availability.data.provider}.
              {availability.data.message && (" " + availability.data.message)}
              {!availability.data.ready && availability.data.fallback && " Predefined questions are available."}
            </p>
          )}
          <form className="form-stack" onSubmit={(event) => {
            event.preventDefault();
            if (question.trim() && !request.isPending) request.mutate({
              question: question.trim(),
              previous_question: history[0]?.question,
            });
          }}>
            <TextField label="Ask a business question" value={question}
              onChange={(event) => setQuestion(event.target.value)} multiline minRows={2}
              slotProps={{ htmlInput: { maxLength: 600 } }} />
            <div><Button type="submit" variant="contained" disabled={!question.trim() || request.isPending}>Ask graph</Button></div>
          </form>
          {(answer?.followups ?? suggestions.data ?? []).length > 0 && (
            <div className="flex flex-wrap gap-2" aria-label="Suggested questions">
              {(answer?.followups ?? suggestions.data ?? []).map((item) => (
                <Button key={item} size="small" onClick={() => setQuestion(item)}>{item}</Button>
              ))}
            </div>
          )}
          <Feedback pending={request.isPending} error={request.error || suggestions.error} />
          {request.isError && <p className="muted">Manual graph exploration remains available below.</p>}
          {answer && (
            <div className="form-stack" aria-live="polite">
              <h2>Query insights</h2>
              <p className="muted">Answered by {answer.provider ?? "groq"}.</p>
              {answer.notice && <Alert severity="info">{answer.notice}</Alert>}
              {answer.plan.operation === "clarify" ? <Alert severity="info">{answer.explanation}</Alert> : <>
                <p>{answer.explanation}</p>
                <p className="muted">{answer.explanation_source === "ai_evidence_selection" ? "AI-selected verified facts" : "Calculated from graph results"}</p>
                {answer.rows.length ? <>
                  {answer.graph.nodes.length > 0 && <Button size="small" onClick={() => showGraph(answer.graph)}>Show evidence in graph</Button>}
                  {counts.size > 1 && <>
                    <h3>Entity types in displayed evidence</h3>
                    <Bars rows={[...counts].map(([label, records]) => ({ label, records }))} />
                  </>}
                  <DataTable rows={answer.rows} />
                  {!["path", "insights"].includes(answer.plan.operation) && answer.count > answer.rows.length &&
                    <p className="muted">Showing the first {answer.rows.length} matches.</p>}
                </> : <Alert severity="info">The query returned no matches.</Alert>}
                <details>
                  <summary>Executed query plan</summary>
                  <pre className="overflow-auto">{JSON.stringify(answer.plan, null, 2)}</pre>
                </details>
              </>}
            </div>
          )}
          {history.length > 0 && <details>
            <summary>Question history</summary>
            <ul>{history.map((item) => <li key={item.question}>
              <Button size="small" disabled={request.isPending} onClick={() => {
                setQuestion(item.question);
                request.mutate(item);
              }}>Rerun {item.question}</Button>
            </li>)}</ul>
          </details>}
        </div>
      )}
    </details>
  );
}
