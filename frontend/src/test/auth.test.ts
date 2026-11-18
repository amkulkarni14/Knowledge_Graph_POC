import { describe, it, expect, beforeEach } from "vitest";
import type { AxiosAdapter, InternalAxiosRequestConfig } from "axios";
import { AxiosError } from "axios";
import { api, ApiError } from "../api/client";
import { authApi } from "../api/authApi";
import { useAuthStore } from "../app/authStore";

const ok = (config: InternalAxiosRequestConfig, data: unknown = { data: {} }) => ({
  data,
  status: 200,
  statusText: "OK",
  headers: {},
  config,
});

function unauthorized(config: InternalAxiosRequestConfig, code = "unauthorized") {
  const response = {
    data: { error: { code, message: "nope", details: [] } },
    status: 401,
    statusText: "Unauthorized",
    headers: {},
    config,
  };
  return new AxiosError("401", "ERR_BAD_REQUEST", config, null, response);
}

describe("JWT session", () => {
  beforeEach(() => {
    useAuthStore.getState().logout();
    sessionStorage.clear();
  });

  it("attaches the bearer token to every request once signed in", async () => {
    const seen: unknown[] = [];
    const adapter: AxiosAdapter = async (config) => {
      seen.push(config.headers.get("Authorization"));
      return ok(config);
    };
    await api.get("/stages", { adapter });
    useAuthStore.getState().setAuth("tok123", { username: "admin" });
    await api.get("/stages", { adapter });
    await api.get("/sessions/abc/graphs/data", { adapter });
    expect(seen).toEqual([undefined, "Bearer tok123", "Bearer tok123"]);
  });

  it("persists the token across reloads and clears it on logout", () => {
    useAuthStore.getState().setAuth("tok123", { username: "admin" });
    expect(JSON.parse(sessionStorage.getItem("kg.auth")!)).toEqual({
      token: "tok123",
      user: { username: "admin" },
    });
    useAuthStore.getState().logout();
    expect(sessionStorage.getItem("kg.auth")).toBeNull();
    expect(useAuthStore.getState().token).toBeNull();
  });

  it("clears the session when any request returns 401", async () => {
    useAuthStore.getState().setAuth("expired", { username: "admin" });
    const adapter: AxiosAdapter = async (config) => {
      throw unauthorized(config);
    };
    await expect(api.get("/stages", { adapter })).rejects.toBeInstanceOf(ApiError);
    expect(useAuthStore.getState().token).toBeNull();
  });

  it("does not treat a failed login as an expired session", async () => {
    useAuthStore.getState().setAuth("still-valid", { username: "admin" });
    const adapter: AxiosAdapter = async (config) => {
      throw unauthorized(config, "invalid_credentials");
    };
    await expect(
      api.post("/login", { username: "a", password: "b" }, { adapter }),
    ).rejects.toMatchObject({ status: 401, code: "invalid_credentials" });
    expect(useAuthStore.getState().token).toBe("still-valid");
  });

  it("parses the login response and rejects malformed ones", async () => {
    const body = { access_token: "t", token_type: "bearer", user: { username: "admin" } };
    let reply: unknown = body;
    const adapter: AxiosAdapter = async (config) => ok(config, reply);
    const original = api.defaults.adapter;
    api.defaults.adapter = adapter;
    try {
      await expect(authApi.login("admin", "admin")).resolves.toEqual(body);
      reply = { data: {} };
      await expect(authApi.login("admin", "admin")).rejects.toBeTruthy();
    } finally {
      api.defaults.adapter = original;
    }
  });
});
