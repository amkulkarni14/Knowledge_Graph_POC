import { describe, it, expect, vi } from "vitest";
import { api, ApiError } from "../api/client";
import { graphsApi, sourcesApi, snapshotsApi } from "../api/workflowApi";
import { sessionsApi } from "../api/sessionsApi";
import type { AxiosAdapter } from "axios";
describe("HTTP contracts", () => {
  it("serializes reads within one backend session while allowing separate sessions", async () => {
    let active = 0,
      maximum = 0;
    const adapter: AxiosAdapter = async (config) => {
      active++;
      maximum = Math.max(maximum, active);
      await new Promise((resolve) => setTimeout(resolve, 10));
      active--;
      return {
        data: { data: {} },
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      };
    };
    await Promise.all([
      api.get("/sessions/serial/graphs/data", { adapter }),
      api.get("/sessions/serial/graphs/metrics", { adapter }),
    ]);
    expect(maximum).toBe(1);
    maximum = 0;
    await Promise.all([
      api.get("/sessions/first/graphs/data", { adapter }),
      api.get("/sessions/second/graphs/data", { adapter }),
    ]);
    expect(maximum).toBe(2);
  });
  it("serializes repeated label parameters without array brackets", () => {
    expect(
      api.getUri({
        url: "/graphs/data",
        params: { labels: ["Customer", "Order"] },
      }),
    ).toContain("labels=Customer&labels=Order");
  });
  it("uses no body for deletion and accepts 204", async () => {
    const request = vi
      .spyOn(api, "request")
      .mockResolvedValue({ status: 204, data: "" });
    await expect(sessionsApi.remove("sid")).resolves.toBeUndefined();
    expect(request).toHaveBeenCalledWith(
      expect.objectContaining({ method: "DELETE", url: "/sessions/sid" }),
    );
  });
  it("leaves multipart boundaries to the browser", async () => {
    const post = vi
      .spyOn(api, "post")
      .mockResolvedValue({ data: { data: { mode: "csv" } } });
    await sourcesApi.upload("sid", [new File(["id\n1"], "test.csv")], () => {});
    expect(post.mock.calls[0][1]).toBeInstanceOf(FormData);
    expect((post.mock.calls[0][1] as FormData).getAll("files")).toHaveLength(1);
    expect(post.mock.calls[0][2]).not.toHaveProperty("headers");
  });
  it("requests snapshot artifacts as binary using returned identifiers", async () => {
    const blob = new Blob(["data"]);
    const get = vi.spyOn(api, "get").mockResolvedValue({ data: blob });
    expect(
      await snapshotsApi.download(
        "sid",
        "retail",
        "20261117T120000000000Z",
        "graph.json.gz",
      ),
    ).toBe(blob);
    expect(get).toHaveBeenCalledWith(
      expect.stringContaining("/download/graph.json.gz"),
      { params: { ontology_id: "retail" }, responseType: "blob" },
    );
  });
  it("passes cancellation signals to bounded graph requests", async () => {
    const signal = new AbortController().signal;
    const get = vi
      .spyOn(api, "get")
      .mockResolvedValue({ data: { data: { nodes: [], edges: [] } } });
    await graphsApi.data("sid", { limit: 150, edge_limit: 1000 }, signal);
    expect(get).toHaveBeenCalledWith("/sessions/sid/graphs/data", {
      params: { limit: 150, edge_limit: 1000 },
      signal,
    });
  });
  it("retains normalized error status and safe details", () => {
    const error = new ApiError(
      "Complete stage 8 first",
      409,
      "stage_prerequisite",
      [{ missing_stage: 8 }],
    );
    expect(error.status).toBe(409);
    expect(error.details).toEqual([{ missing_stage: 8 }]);
  });
});
