import { useState } from "react";
import { Link } from "react-router-dom";
import { authAPI } from "./api";

export default function Register() {
  const [form, setForm] = useState({ full_name:"", email:"", mobile:"", username:"", password:"" });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const fd = new FormData();
      Object.entries(form).forEach(([k,v]) => fd.append(k, v));
      await authAPI.register(fd);
      setSuccess(true);
    } catch (err) {
      setError(err.response?.data?.detail || "Registration failed.");
    } finally { setLoading(false); }
  };

  if (success) return (
    <div style={{
      minHeight:"100vh", display:"flex", alignItems:"center",
      justifyContent:"center", background:"var(--bg)"
    }}>
      <div className="card" style={{ maxWidth:420, width:"100%", margin:"0 16px", textAlign:"center", padding:40 }}>
        <div style={{ fontSize:48, marginBottom:16 }}>✅</div>
        <h2 style={{ fontSize:20, fontWeight:700, marginBottom:8 }}>Registration Successful!</h2>
        <p style={{ color:"var(--text2)", fontSize:14, marginBottom:24 }}>
          Your account has been created. Please wait for an admin to verify your account before you can log in.
        </p>
        <Link to="/login">
          <button className="btn-primary" style={{ width:"100%", padding:12 }}>
            Go to Login
          </button>
        </Link>
      </div>
    </div>
  );

  return (
    <div style={{
      minHeight:"100vh", display:"flex", alignItems:"center",
      justifyContent:"center", background:"var(--bg)", padding:"20px 16px",
      backgroundImage:"radial-gradient(ellipse at 80% 50%, rgba(88,101,242,0.08) 0%, transparent 60%)"
    }}>
      <div style={{ width:"100%", maxWidth:420 }}>
        <div style={{ textAlign:"center", marginBottom:28 }}>
          <div style={{ fontSize:36, marginBottom:8 }}>🎙️</div>
          <h1 style={{ fontSize:22, fontWeight:700 }}>Create Account</h1>
          <p style={{ color:"var(--text3)", fontSize:13, marginTop:4 }}>
            Join the Speech Analysis System
          </p>
        </div>

        <div className="card" style={{ padding:32 }}>
          <form onSubmit={handleSubmit}>
            {[
              { key:"full_name", label:"Full Name", placeholder:"Your full name", type:"text" },
              { key:"email", label:"Email Address", placeholder:"you@example.com", type:"email" },
              { key:"mobile", label:"Mobile Number", placeholder:"10-digit mobile number", type:"tel" },
              { key:"username", label:"Username", placeholder:"Choose a username", type:"text" },
              { key:"password", label:"Password", placeholder:"Create a password", type:"password" },
            ].map(({ key, label, placeholder, type }) => (
              <div key={key} style={{ marginBottom:16 }}>
                <label style={{ fontSize:13, color:"var(--text2)", fontWeight:500, display:"block", marginBottom:6 }}>
                  {label}
                </label>
                <input type={type} placeholder={placeholder}
                  value={form[key]} onChange={set(key)} required />
              </div>
            ))}

            {error && (
              <div style={{
                background:"rgba(237,66,69,0.1)", border:"1px solid rgba(237,66,69,0.3)",
                borderRadius:6, padding:"10px 14px", marginBottom:16,
                fontSize:13, color:"var(--danger)"
              }}>{error}</div>
            )}

            <button type="submit" className="btn-primary"
              disabled={loading}
              style={{ width:"100%", padding:12, fontSize:14, borderRadius:8, marginTop:4 }}>
              {loading ? "Creating Account..." : "Create Account"}
            </button>
          </form>

          <div style={{ textAlign:"center", marginTop:20, fontSize:13, color:"var(--text3)" }}>
            Already have an account?{" "}
            <Link to="/login" style={{ color:"var(--accent3)", textDecoration:"none", fontWeight:500 }}>
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}