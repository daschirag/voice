import { useState, useEffect } from "react";
import { adminAPI, clientAPI } from "./api";
import { useAuth } from "./AuthContext";

const SC = (s) => s>=4?"#3ba55c":s>=3?"#5865f2":s>=2?"#faa61a":"#ed4245";

function Sidebar({ tab, setTab, logout, user }) {
  const items = [
    { id:"overview", icon:"📈", label:"Overview" },
    { id:"users", icon:"👥", label:"User Management" },
    { id:"reports", icon:"📄", label:"All Reports" },
  ];
  return (
    <div style={{ width:220, minHeight:"100vh", background:"var(--bg2)",
      borderRight:"1px solid var(--border)", display:"flex",
      flexDirection:"column", flexShrink:0 }}>
      <div style={{ padding:"20px 16px", borderBottom:"1px solid var(--border)" }}>
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <span style={{ fontSize:22 }}>🎙️</span>
          <div>
            <div style={{ fontWeight:700, fontSize:14 }}>SpeechAI</div>
            <div style={{ fontSize:11, color:"var(--accent3)", fontWeight:600 }}>Admin Panel</div>
          </div>
        </div>
      </div>
      <nav style={{ flex:1, padding:"8px 8px" }}>
        {items.map(item=>(
          <button key={item.id} onClick={()=>setTab(item.id)}
            style={{
              width:"100%", padding:"10px 12px", borderRadius:6, marginBottom:2,
              background:tab===item.id?"rgba(88,101,242,0.15)":"transparent",
              color:tab===item.id?"var(--accent3)":"var(--text2)",
              border:tab===item.id?"1px solid rgba(88,101,242,0.2)":"1px solid transparent",
              justifyContent:"flex-start", fontSize:14, gap:10,
              fontWeight:tab===item.id?600:400,
            }}>
            <span>{item.icon}</span>{item.label}
          </button>
        ))}
      </nav>
      <div style={{ padding:"12px 8px", borderTop:"1px solid var(--border)" }}>
        <div style={{ padding:"10px 12px", marginBottom:4 }}>
          <div style={{ fontSize:13, fontWeight:600 }}>{user?.full_name}</div>
          <div style={{ fontSize:11, color:"var(--accent3)", fontWeight:600 }}>Administrator</div>
        </div>
        <button onClick={logout} className="btn-secondary"
          style={{ width:"100%", justifyContent:"flex-start", padding:"8px 12px", fontSize:13 }}>
          🚪 Sign Out
        </button>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, color }) {
  return (
    <div className="card" style={{ textAlign:"center", padding:24 }}>
      <div style={{ fontSize:32, marginBottom:8 }}>{icon}</div>
      <div style={{ fontSize:32, fontWeight:800, color:color||"var(--text)", marginBottom:4 }}>{value}</div>
      <div style={{ fontSize:13, color:"var(--text3)" }}>{label}</div>
    </div>
  );
}

function OverviewTab() {
  const [stats, setStats] = useState(null);
  useEffect(()=>{ adminAPI.getStats().then(r=>setStats(r.data)).catch(()=>{}); },[]);
  if (!stats) return <div style={{color:"var(--text3)",padding:40,textAlign:"center"}}>Loading...</div>;
  return (
    <div>
      <h2 style={{ fontSize:20, fontWeight:700, marginBottom:4 }}>Dashboard Overview</h2>
      <p style={{ color:"var(--text3)", fontSize:13, marginBottom:24 }}>System statistics at a glance</p>
      <div style={{ display:"grid", gridTemplateColumns:"repeat(5,1fr)", gap:16 }}>
        <StatCard icon="👥" label="Total Clients" value={stats.total_users} color="var(--text)"/>
        <StatCard icon="✅" label="Verified" value={stats.verified_users} color="var(--success)"/>
        <StatCard icon="⏳" label="Pending" value={stats.pending_users} color="var(--warning)"/>
        <StatCard icon="📊" label="Analyses" value={stats.total_analyses} color="var(--accent3)"/>
        <StatCard icon="⭐" label="Avg Score" value={stats.avg_composite_score||"—"} color="var(--warning)"/>
      </div>
    </div>
  );
}

function UsersTab() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    adminAPI.getUsers().then(r=>setUsers(r.data)).finally(()=>setLoading(false));
  };
  useEffect(load,[]);

  const verify = async (id, current) => {
    try {
      if (current) await adminAPI.unverifyUser(id);
      else await adminAPI.verifyUser(id);
      load();
    } catch(e) { alert(e.response?.data?.detail||"Error"); }
  };

  const del = async (id, name) => {
    if (!window.confirm(`Delete user "${name}"? This cannot be undone.`)) return;
    try { await adminAPI.deleteUser(id); load(); }
    catch(e) { alert(e.response?.data?.detail||"Error"); }
  };

  if (loading) return <div style={{color:"var(--text3)",padding:40,textAlign:"center"}}>Loading users...</div>;

  const clients = users.filter(u=>u.role==="client");
  const admins = users.filter(u=>u.role==="admin");

  return (
    <div>
      <h2 style={{ fontSize:20, fontWeight:700, marginBottom:4 }}>User Management</h2>
      <p style={{ color:"var(--text3)", fontSize:13, marginBottom:24 }}>
        {clients.length} client{clients.length!==1?"s":""} registered
      </p>

      <div style={{ background:"var(--bg2)", border:"1px solid var(--border)", borderRadius:10, overflow:"hidden" }}>
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr 1fr auto auto",
          padding:"10px 16px", background:"var(--bg3)",
          fontSize:11, fontWeight:700, color:"var(--text3)",
          textTransform:"uppercase", letterSpacing:"0.6px",
          borderBottom:"1px solid var(--border)" }}>
          <div>Name</div><div>Email</div><div>Mobile</div>
          <div>Joined</div><div>Status</div><div>Actions</div>
        </div>
        {clients.map((u,i)=>(
          <div key={u.id} style={{
            display:"grid", gridTemplateColumns:"1fr 1fr 1fr 1fr auto auto",
            padding:"14px 16px", alignItems:"center", gap:8,
            background:i%2===0?"var(--bg2)":"var(--bg3)",
            borderBottom:"1px solid var(--border)",
          }}>
            <div>
              <div style={{ fontWeight:600, fontSize:13 }}>{u.full_name}</div>
              <div style={{ fontSize:11, color:"var(--text3)" }}>@{u.username}</div>
            </div>
            <div style={{ fontSize:13, color:"var(--text2)" }}>{u.email}</div>
            <div style={{ fontSize:13, color:"var(--text2)" }}>{u.mobile||"—"}</div>
            <div style={{ fontSize:12, color:"var(--text3)" }}>
              {new Date(u.created_at).toLocaleDateString()}
            </div>
            <div>
              <span className={`badge ${u.is_verified?"badge-green":"badge-yellow"}`}>
                {u.is_verified?"Verified":"Pending"}
              </span>
            </div>
            <div style={{ display:"flex", gap:6 }}>
              <button onClick={()=>verify(u.id,u.is_verified)}
                className={u.is_verified?"btn-danger":"btn-success"}
                style={{ fontSize:11, padding:"4px 10px" }}>
                {u.is_verified?"Unverify":"Verify"}
              </button>
              <button onClick={()=>del(u.id,u.username)}
                className="btn-danger" style={{ fontSize:11, padding:"4px 10px" }}>
                Del
              </button>
            </div>
          </div>
        ))}
        {clients.length===0 && (
          <div style={{ padding:"40px", textAlign:"center", color:"var(--text3)" }}>
            No clients registered yet.
          </div>
        )}
      </div>

      {admins.length>0 && (
        <div style={{ marginTop:24 }}>
          <div style={{ fontSize:13, fontWeight:600, color:"var(--text3)", marginBottom:12 }}>
            ADMINISTRATORS
          </div>
          {admins.map(u=>(
            <div key={u.id} className="card" style={{ padding:"12px 16px", marginBottom:8,
              display:"flex", justifyContent:"space-between", alignItems:"center" }}>
              <div>
                <span style={{ fontWeight:600, fontSize:13 }}>{u.full_name}</span>
                <span style={{ marginLeft:10, fontSize:12, color:"var(--text3)" }}>@{u.username}</span>
              </div>
              <span className="badge badge-blue">Admin</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ReportsTab() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const load = (q="") => {
    setLoading(true);
    adminAPI.getReports(q?{username:q}:{})
      .then(r=>setReports(r.data))
      .finally(()=>setLoading(false));
  };

  useEffect(()=>load(),[]);

  return (
    <div>
      <h2 style={{ fontSize:20, fontWeight:700, marginBottom:4 }}>All Reports</h2>
      <p style={{ color:"var(--text3)", fontSize:13, marginBottom:20 }}>
        {reports.length} total analyses across all clients
      </p>

      <div style={{ display:"flex", gap:10, marginBottom:20 }}>
        <input placeholder="Search by username..." value={search}
          onChange={e=>setSearch(e.target.value)}
          style={{ maxWidth:280 }}
          onKeyDown={e=>e.key==="Enter"&&load(search)}/>
        <button className="btn-primary" onClick={()=>load(search)}
          style={{ padding:"10px 20px", fontSize:13 }}>
          Search
        </button>
        <button className="btn-secondary" onClick={()=>{setSearch("");load("");}}>
          Clear
        </button>
      </div>

      {loading ? (
        <div style={{color:"var(--text3)",padding:40,textAlign:"center"}}>Loading...</div>
      ) : (
        <div style={{ background:"var(--bg2)", border:"1px solid var(--border)",
          borderRadius:10, overflow:"hidden" }}>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr 120px 80px 80px auto",
            padding:"10px 16px", background:"var(--bg3)",
            fontSize:11, fontWeight:700, color:"var(--text3)",
            textTransform:"uppercase", letterSpacing:"0.6px",
            borderBottom:"1px solid var(--border)" }}>
            <div>Client</div><div>File</div><div>Date & Time</div>
            <div>Role</div><div>Score</div><div>Grade</div><div>PDF</div>
          </div>
          {reports.map((r,i)=>(
            <div key={r.id} style={{
              display:"grid", gridTemplateColumns:"1fr 1fr 1fr 120px 80px 80px auto",
              padding:"13px 16px", alignItems:"center",
              background:i%2===0?"var(--bg2)":"var(--bg3)",
              borderBottom:"1px solid var(--border)", gap:8,
            }}>
              <div>
                <div style={{ fontWeight:600, fontSize:13 }}>{r.username}</div>
                <div style={{ fontSize:11, color:"var(--text3)" }}>{r.email}</div>
              </div>
              <div style={{ fontSize:13, color:"var(--text2)",
                overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
                {r.filename||"recording"}
              </div>
              <div style={{ fontSize:12, color:"var(--text3)" }}>
                {new Date(r.recorded_at).toLocaleString()}
              </div>
              <div>
                <span className="badge badge-blue" style={{ fontSize:11 }}>
                  {r.role}
                </span>
              </div>
              <div style={{ fontWeight:700, color:SC(r.composite_score), fontSize:15 }}>
                {r.composite_score}/5
              </div>
              <div style={{ fontWeight:700, fontSize:15,
                color:SC(r.composite_score) }}>
                {r.grade}
              </div>
              <a href={`/api/v1/report/${r.job_id}/pdf`} target="_blank"
                style={{ textDecoration:"none" }}>
                <button className="btn-secondary" style={{ fontSize:11, padding:"4px 10px" }}>
                  📥 PDF
                </button>
              </a>
            </div>
          ))}
          {reports.length===0 && (
            <div style={{ padding:"40px", textAlign:"center", color:"var(--text3)" }}>
              No reports found.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function AdminDashboard() {
  const [tab, setTab] = useState("overview");
  const { logout, user } = useAuth();

  return (
    <div style={{ display:"flex", minHeight:"100vh" }}>
      <Sidebar tab={tab} setTab={setTab} logout={logout} user={user}/>
      <main style={{ flex:1, padding:"32px 32px", overflowY:"auto", background:"var(--bg)" }}>
        {tab==="overview" && <OverviewTab/>}
        {tab==="users" && <UsersTab/>}
        {tab==="reports" && <ReportsTab/>}
      </main>
    </div>
  );
}