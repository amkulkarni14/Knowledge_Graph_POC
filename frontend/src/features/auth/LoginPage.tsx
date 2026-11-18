import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Network, Lock, User } from "lucide-react";
import { useAuthStore } from "../../app/authStore";
import { authApi } from "../../api/authApi";
import { ApiError } from "../../api/client";

export function LoginPage() {
  const setAuth = useAuthStore((s) => s.setAuth);
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (pending) return;
    if (!username.trim() || !password) {
      setError("Enter your username and password.");
      return;
    }
    setPending(true);
    setError(null);
    try {
      const result = await authApi.login(username.trim(), password);
      navigate("/", { replace: true });
      setAuth(result.access_token, result.user);
    } catch (e) {
      setPassword("");
      setPending(false);
      setError(
        e instanceof ApiError
          ? e.status === 401
            ? "Invalid username or password."
            : e.message
          : "Sign in failed. Please try again.",
      );
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={submit} noValidate>
        <div className="login-brand">
          <Network size={30} />
          <div>
            <div className="login-title">Knowledge Graph</div>
            <div className="login-subtitle">ENTERPRISE STUDIO</div>
          </div>
        </div>
        <h1 className="login-heading">Sign in</h1>
        <p className="login-help">Enter your credentials to open the workspace.</p>

        {error && (
          <div className="login-error" role="alert">
            {error}
          </div>
        )}

        <label className="login-field">
          <span>Username</span>
          <div className="login-input">
            <User size={16} aria-hidden="true" />
            <input
              type="text"
              name="username"
              autoComplete="username"
              autoFocus
              required
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                setError(null);
              }}
            />
          </div>
        </label>

        <label className="login-field">
          <span>Password</span>
          <div className="login-input">
            <Lock size={16} aria-hidden="true" />
            <input
              type="password"
              name="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setError(null);
              }}
            />
          </div>
        </label>

        <button type="submit" className="login-submit" disabled={pending}>
          {pending ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}

export default LoginPage;
