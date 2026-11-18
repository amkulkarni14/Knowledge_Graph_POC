import { z } from "zod";
import { api } from "./client";

const loginSchema = z.object({
  access_token: z.string().min(1),
  token_type: z.string(),
  user: z.object({ username: z.string() }),
});
export type LoginResult = z.infer<typeof loginSchema>;

export const authApi = {
  // /login returns the token document directly rather than the usual { data } envelope.
  async login(username: string, password: string): Promise<LoginResult> {
    const response = await api.post("/login", { username, password });
    return loginSchema.parse(response.data);
  },
  async me(signal?: AbortSignal): Promise<{ username: string }> {
    return (await api.get<{ data: { username: string } }>("/me", { signal })).data
      .data;
  },
  async logout(): Promise<void> {
    await api.post("/logout");
  },
};
