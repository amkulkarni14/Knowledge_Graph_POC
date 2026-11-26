import { useState } from "react";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { restoreBusinessQuestions, suggestedQuestions } from "../constants/businessQuestions";
import { BusinessQuestionsField } from "../features/projects/BusinessQuestionsField";

function mount(saved: string[] = []) {
  const changed = vi.fn();
  function Form() {
    const [questions, setQuestions] = useState(() => restoreBusinessQuestions(saved));
    return <BusinessQuestionsField questions={questions} error={undefined} disabled={false}
      inputRef={null} onBlur={() => undefined} onDraftChange={() => undefined}
      onChange={(next) => { changed(next.map(({ text }) => text)); setQuestions(next); }} />;
  }
  return { ...render(<Form />), changed };
}

const picker = () => screen.getByRole("combobox", { name: "Search and select business questions" });
const selectAll = () => screen.getByRole("option", { name: "Select All" });
const checkbox = () => within(selectAll()).getByRole("checkbox", { name: "Select All" });

it("selects the whole catalog under a search filter and clears only predefined questions", async () => {
  const custom = "How should we audit this project?";
  const user = userEvent.setup();
  const view = mount([custom]);
  expect(screen.getByText("Selected questions: 1")).toBeVisible();
  await user.click(picker());
  await user.paste(suggestedQuestions[0].text);
  expect(screen.getAllByRole("option")[0]).toBe(selectAll());
  expect(checkbox()).not.toBeChecked();
  expect(screen.getAllByRole("option")).toHaveLength(2);
  await user.click(screen.getByRole("option", { name: suggestedQuestions[0].text }));
  expect(screen.getByRole("listbox")).toBeVisible();
  expect(checkbox()).toHaveAttribute("aria-checked", "mixed");
  await user.clear(picker());
  await user.paste("shortest path");
  await user.click(checkbox());
  expect(screen.getByRole("listbox")).toBeVisible();
  expect(checkbox()).toBeChecked();
  const saved = view.changed.mock.lastCall?.[0] as string[];
  expect(saved).toEqual([custom, ...suggestedQuestions.map(({ text }) => text)]);
  expect(screen.getByText(`Selected questions: ${saved.length}`)).toBeVisible();
  view.unmount();

  mount(saved);
  await user.click(picker());
  expect(checkbox()).toBeChecked();
  await user.click(screen.getByRole("option", { name: suggestedQuestions[0].text }));
  expect(checkbox()).toHaveAttribute("aria-checked", "mixed");
  await user.click(screen.getByRole("option", { name: suggestedQuestions[0].text }));
  expect(checkbox()).toBeChecked();
  await user.click(checkbox());
  expect(screen.getByRole("listbox")).toBeVisible();
  expect(checkbox()).not.toBeChecked();
  expect(screen.getByText("Selected questions: 1")).toBeVisible();
  expect(screen.getByText(custom)).toBeVisible();
}, 30000);

it("starts unselected and does not duplicate equivalent custom text", async () => {
  const user = userEvent.setup();
  const fresh = mount();
  expect(screen.getByText("Selected questions: 0")).toBeVisible();
  fresh.unmount();
  const custom = suggestedQuestions[0].text.toUpperCase();
  const view = mount([custom]);
  await user.click(picker());
  await user.click(selectAll());
  expect(view.changed.mock.lastCall?.[0]).toEqual([custom, ...suggestedQuestions.slice(1).map(({ text }) => text)]);
  await user.click(selectAll());
  expect(view.changed.mock.lastCall?.[0]).toEqual([custom]);
}, 20000);
