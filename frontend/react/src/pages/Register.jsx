import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Leaf, UserPlus } from "lucide-react";
import { apiBase, useAuth } from "../AuthContext.jsx";
import "./AuthPages.css";

export default function Register() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setErr("");
    if (password !== confirm) {
      setErr("Passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      const r = await fetch(`${apiBase}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || "Registration failed");

      const loginRes = await fetch(`${apiBase}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const loginData = await loginRes.json();
      if (!loginRes.ok) throw new Error("Registered, but auto-login failed — please log in.");

      login(loginData.token, loginData.username);
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
        <h1>Create an account</h1>
        <p className="auth-sub">Register to run forest analysis and track your alerts.</p>
        <form onSubmit={handleSubmit}>
          <label>Username</label>
          <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} required minLength={3} />
          <label>Password</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={6} />
          <label>Confirm password</label>
          <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required minLength={6} />
          {err && <p className="auth-error">{err}</p>}
          <button type="submit" className="auth-btn" disabled={loading}>
            <UserPlus size={16} />
            {loading ? "Creating…" : "Create account"}
          </button>
        </form>
        <p className="auth-footer">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
        <p className="auth-footer">
          <Link to="/">← Back to home</Link>
        </p>
      </div>
    </div>
  );
}