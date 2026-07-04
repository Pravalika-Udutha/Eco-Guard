import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Leaf, LogIn } from "lucide-react";
import { apiBase } from "../AuthContext.jsx";
import { useAuth } from "../AuthContext.jsx";
import "./AuthPages.css";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      const r = await fetch(`${apiBase}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || "Login failed");
      login(data.token, data.username);
      navigate("/tool");
    } catch (e2) {
      setErr(e2.message || String(e2));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-brand">
          <Leaf size={24} />
          <span>Eco-Guard Telangana</span>
        </div>
        <h1>Welcome back</h1>
        <p className="auth-sub">Log in to run forest analysis and view your alerts.</p>
        <form onSubmit={handleSubmit}>
          <label>Username</label>
          <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} required />
          <label>Password</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          {err && <p className="auth-error">{err}</p>}
          <button type="submit" className="auth-btn" disabled={loading}>
            <LogIn size={16} />
            {loading ? "Logging in…" : "Log in"}
          </button>
        </form>
        <p className="auth-footer">
          Don't have an account? <Link to="/register">Register</Link>
        </p>
        <p className="auth-footer">
          <Link to="/">← Back to home</Link>
        </p>
      </div>
    </div>
  );
}