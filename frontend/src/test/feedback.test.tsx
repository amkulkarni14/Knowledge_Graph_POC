import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Report, Feedback, DataTable } from "../shared/ui/WorkspaceUi";
import { Providers } from "../app/providers";
describe("validation and accessible feedback", () => {
  it("shows blocking findings even when HTTP succeeded", () => {
    render(
      <Providers>
        <Report value={{ ok: false, errors: ["Missing key column"] }} />
      </Providers>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("blocking");
    expect(screen.getByText("Inspect 1 items")).toBeInTheDocument();
  });
  it("renders safe error messages", () => {
    render(
      <Providers>
        <Feedback error={new Error("Session has expired")} />
      </Providers>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Session has expired");
  });
  it("offers a semantic table alternative for graph properties", () => {
    render(
      <Providers>
        <DataTable rows={[{ id: "Customer:1", label: "Customer" }]} />
      </Providers>,
    );
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("Customer:1")).toBeInTheDocument();
  });
});
