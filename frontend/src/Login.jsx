import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "./AuthContext";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const data = await login(username, password);
      navigate(data.role === "admin" ? "/admin" : "/client");
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed. Check your credentials.");
    } finally { setLoading(false); }
  };

  return (
    <div style={{
      minHeight: "100vh", display: "flex", alignItems: "center",
      justifyContent: "center", background: "var(--bg)",
      backgroundImage: "radial-gradient(ellipse at 20% 50%, rgba(88,101,242,0.08) 0%, transparent 60%)"
    }}>
      <div style={{ width: "100%", maxWidth: 400, padding: "0 16px" }}>

        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div style={{ fontSize: 40, marginBottom: 8 }}>🎙️</div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text)" }}>
            Speech Analysis System
          </h1>
          <p style={{ color: "var(--text3)", fontSize: 13, marginTop: 4 }}>
            Sign in to your account
          </p>
        </div>

        {/* Card */}
        <div className="card" style={{ padding: 32 }}>
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 13, color: "var(--text2)", fontWeight: 500, display: "block", marginBottom: 6 }}>
                Username
              </label>
              <input
                type="text" placeholder="Enter username"
                value={username} onChange={e => setUsername(e.target.value)}
                required autoFocus
              />
            </div>

            <div style={{ marginBottom: 24 }}>
              <label style={{ fontSize: 13, color: "var(--text2)", fontWeight: 500, display: "block", marginBottom: 6 }}>
                Password
              </label>
              <input
                type="password" placeholder="Enter password"
                value={password} onChange={e => setPassword(e.target.value)}
                required
              />
            </div>

            {error && (
              <div style={{
                background: "rgba(237,66,69,0.1)", border: "1px solid rgba(237,66,69,0.3)",
                borderRadius: 6, padding: "10px 14px", marginBottom: 16,
                fontSize: 13, color: "var(--danger)"
              }}>
                {error}
              </div>
            )}

            <button type="submit" className="btn-primary"
              disabled={loading}
              style={{ width: "100%", padding: "12px", fontSize: 14, borderRadius: 8 }}>
              {loading ? "Signing in..." : "Sign In"}
            </button>
          </form>

          <div style={{ textAlign: "center", marginTop: 20, fontSize: 13, color: "var(--text3)" }}>
            Don't have an account?{" "}
            <Link to="/register" style={{ color: "var(--accent3)", textDecoration: "none", fontWeight: 500 }}>
              Register here
            </Link>
          </div>
        </div>

        <p style={{ textAlign: "center", marginTop: 16, fontSize: 12, color: "var(--text3)" }}>
          Audix Technologies · Speech Analysis System v2.0
        </p>
      </div>
    </div>
  );
}