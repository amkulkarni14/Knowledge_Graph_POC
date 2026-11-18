import { describe, it, expect, beforeEach } from "vitest";
import { useGraphStore, useSessionStore } from "../app/store";
describe("session isolation", () => {
  beforeEach(() => {
    useSessionStore.getState().setSession(null);
    useGraphStore.getState().reset();
  });
  it("increments an epoch even when resetting the same session to reject late responses", () => {
    const epoch = useSessionStore.getState().epoch;
    useSessionStore.getState().setSession("first");
    useSessionStore.getState().setSession("second");
    expect(useSessionStore.getState().epoch).toBe(epoch + 2);
    expect(useSessionStore.getState().id).toBe("second");
  });
  it("clears graph selections and layout when reset", () => {
    useGraphStore.getState().select("Customer:1");
    useGraphStore.getState().setLayout("grid");
    useGraphStore.getState().reset();
    expect(useGraphStore.getState().selected).toBeNull();
    expect(useGraphStore.getState().layout).toBe("cose");
  });
});
