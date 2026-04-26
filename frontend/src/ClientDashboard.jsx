import { useState, useRef, useEffect } from "react";
import { clientAPI } from "./api";
import { useAuth } from "./AuthContext";
import RadarChart from "./RadarChart";

const ROLES = ["general","sales","executive","interview","coaching"];
const SC = (s) => s>=4.5?"#3ba55c":s>=3.5?"#5865f2":s>=2.5?"#faa61a":"#ed4245";
const GC = {A:"#3ba55c",B:"#5865f2",C:"#faa61a",D:"#ed4245",F:"#ed4245"};

function Sidebar({ tab, setTab, logout, user }) {
  const items = [
    { id:"analyze", icon:"🎙️", label:"Analyze Speech" },
    { id:"reports", icon:"📊", label:"My Reports" },
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
            <div style={{ fontSize:11, color:"var(--text3)" }}>Client Portal</div>
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
              justifyContent:"flex-start", fontSize:14, gap:10, fontWeight:tab===item.id?600:400,
            }}>
            <span>{item.icon}</span>{item.label}
          </button>
        ))}
      </nav>
      <div style={{ padding:"12px 8px", borderTop:"1px solid var(--border)" }}>
        <div style={{ padding:"10px 12px", marginBottom:4 }}>
          <div style={{ fontSize:13, fontWeight:600, color:"var(--text)" }}>{user?.full_name}</div>
          <div style={{ fontSize:11, color:"var(--text3)" }}>{user?.email}</div>
        </div>
        <button onClick={logout} className="btn-secondary"
          style={{ width:"100%", justifyContent:"flex-start", padding:"8px 12px", fontSize:13 }}>
          🚪 Sign Out
        </button>
      </div>
    </div>
  );
}

function WaveBar({ active, idx }) {
  const height = active ? `${30 + Math.sin(idx * 0.8) * 20 + 20}%` : "20%";
  return (
    <div style={{
      width: 3,
      borderRadius: 2,
      background: active ? "var(--accent)" : "var(--border2)",
      height: height,
      transition: active ? "none" : "height 0.3s, background 0.3s",
      animation: active ? `wave ${0.5 + (idx % 5) * 0.1}s ease-in-out infinite alternate` : "none",
    }}/>
  );
}

function Recorder({ onAudioReady }) {
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [tick, setTick] = useState(0);
  const mediaRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const waveRef = useRef(null);

  const fmt = (s) => {
    const h = Math.floor(s/3600).toString().padStart(2,"0");
    const m = Math.floor((s%3600)/60).toString().padStart(2,"0");
    const ss = (s%60).toString().padStart(2,"0");
    return h+":"+m+":"+ss;
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });
      mediaRef.current = mr;
      chunksRef.current = [];
      mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      mr.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const url = URL.createObjectURL(blob);
        const ts = new Date().toISOString().replace(/[:.]/g,"-").slice(0,19);
        const file = new File([blob], "recording-"+ts+".webm", { type: "audio/webm" });
        setAudioBlob(blob);
        setAudioUrl(url);
        onAudioReady(file);
        stream.getTracks().forEach(t => t.stop());
      };
      mr.start(100);
      setRecording(true);
      setSeconds(0);
      setAudioBlob(null);
      setAudioUrl(null);
      timerRef.current = setInterval(() => {
        setSeconds(s => s + 1);
        setTick(t => t + 1);
      }, 1000);
    } catch(e) {
      alert("Microphone access denied. Please allow microphone access in your browser settings.");
    }
  };

  const stopRecording = () => {
    if (mediaRef.current && recording) {
      mediaRef.current.stop();
      setRecording(false);
      clearInterval(timerRef.current);
    }
  };

  useEffect(() => () => clearInterval(timerRef.current), []);

  const bars = Array.from({ length: 24 });

  return (
    <div style={{ background:"var(--bg3)", border:"1px solid var(--border2)",
      borderRadius:12, padding:28, textAlign:"center" }}>
      <div style={{ fontSize:13, color:"var(--text3)", fontWeight:600,
        textTransform:"uppercase", letterSpacing:"0.8px", marginBottom:20 }}>
        Real-Time Recording
      </div>

      <div style={{ display:"flex", alignItems:"center", justifyContent:"center",
        gap:3, height:52, marginBottom:20 }}>
        {bars.map((_,i) => <WaveBar key={i} active={recording} idx={i}/>)}
      </div>

      <div style={{ fontSize:38, fontWeight:700, letterSpacing:3,
        color: recording ? "var(--accent3)" : "var(--text3)",
        marginBottom:24, fontVariantNumeric:"tabular-nums", transition:"color 0.3s" }}>
        {fmt(seconds)}
      </div>

      <div style={{ display:"flex", gap:12, justifyContent:"center" }}>
        {!recording ? (
          <button onClick={startRecording}
            style={{ background:"var(--accent)", color:"white",
              padding:"12px 32px", borderRadius:50, fontSize:14, fontWeight:600,
              boxShadow:"0 0 24px rgba(88,101,242,0.4)", border:"none" }}>
            ● Start Recording
          </button>
        ) : (
          <button onClick={stopRecording}
            style={{ background:"var(--danger)", color:"white",
              padding:"12px 32px", borderRadius:50, fontSize:14, fontWeight:600,
              boxShadow:"0 0 24px rgba(237,66,69,0.4)", border:"none" }}>
            ■ Stop Recording
          </button>
        )}
      </div>

      {audioUrl && !recording && (
        <div style={{ marginTop:20 }}>
          <audio controls src={audioUrl} style={{ width:"100%", marginBottom:8 }}/>
          <div style={{ fontSize:12, color:"var(--success)" }}>
            ✅ Recording ready — {fmt(seconds)} captured. Click Analyze below.
          </div>
        </div>
      )}
    </div>
  );
}

function AnalyzeTab() {
  const [mode, setMode] = useState("record");
  const [audioFile, setAudioFile] = useState(null);
  const [role, setRole] = useState("general");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [drag, setDrag] = useState(false);
  const fileRef = useRef();

  const handleAudioReady = (file) => {
    setAudioFile(file);
    setResult(null);
    setError("");
  };

  const handleFileSelect = (f) => {
    const ok = ["mp3","wav","m4a","ogg","flac","aac","webm"];
    if (!ok.includes(f.name.split(".").pop().toLowerCase())) {
      setError("Unsupported format. Use MP3, WAV, M4A, OGG, FLAC.");
      return;
    }
    setAudioFile(f);
    setResult(null);
    setError("");
  };

  const analyze = async () => {
    if (!audioFile) { setError("Please record audio or upload a file first."); return; }
    setLoading(true); setError(""); setResult(null);
    try {
      const r = await clientAPI.analyze(audioFile, role);
      const jobId = r.data.job_id;
      const rep = await clientAPI.getReport(jobId);
      setResult({ ...rep.data, jobId });
    } catch(e) {
      const msg = e.response?.data?.detail || e.message || "Analysis failed.";
      setError(typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally { setLoading(false); }
  };

  return (
    <div style={{ maxWidth:780, margin:"0 auto" }}>
      <h2 style={{ fontSize:20, fontWeight:700, marginBottom:4 }}>Analyze Speech</h2>
      <p style={{ color:"var(--text3)", fontSize:13, marginBottom:24 }}>
        Record your voice live or upload an audio file for instant AI feedback
      </p>

      <div style={{ display:"flex", gap:8, marginBottom:20 }}>
        {[["record","🎙️ Record Live"],["upload","📂 Upload File"]].map(([m,l])=>(
          <button key={m} onClick={()=>{ setMode(m); setAudioFile(null); setResult(null); setError(""); }}
            style={{ padding:"8px 20px", borderRadius:6, fontSize:13, fontWeight:600,
              background:mode===m?"var(--accent)":"var(--bg4)",
              color:mode===m?"white":"var(--text2)",
              border:mode===m?"none":"1px solid var(--border2)" }}>
            {l}
          </button>
        ))}
      </div>

      {mode==="record" ? (
        <Recorder onAudioReady={handleAudioReady}/>
      ) : (
        <div onClick={()=>fileRef.current.click()}
          onDragOver={(e)=>{ e.preventDefault(); setDrag(true); }}
          onDragLeave={()=>setDrag(false)}
          onDrop={(e)=>{ e.preventDefault(); setDrag(false); if(e.dataTransfer.files[0]) handleFileSelect(e.dataTransfer.files[0]); }}
          style={{ border:"2px dashed "+(drag?"var(--accent)":audioFile?"var(--success)":"var(--border2)"),
            borderRadius:12, padding:"36px 24px", textAlign:"center", cursor:"pointer",
            background:drag?"rgba(88,101,242,0.05)":"var(--bg3)", transition:"all 0.2s" }}>
          <input ref={fileRef} type="file" hidden
            accept=".mp3,.wav,.m4a,.ogg,.flac,.aac"
            onChange={(e)=>e.target.files[0]&&handleFileSelect(e.target.files[0])}/>
          {audioFile ? (
            <>
              <div style={{fontSize:32,marginBottom:8}}>🎵</div>
              <div style={{fontWeight:600,color:"var(--success)"}}>{audioFile.name}</div>
              <div style={{color:"var(--text3)",fontSize:13,marginTop:4}}>
                {(audioFile.size/1048576).toFixed(2)} MB — click to change
              </div>
            </>
          ) : (
            <>
              <div style={{fontSize:32,marginBottom:8}}>📂</div>
              <div style={{fontWeight:600}}>Drop audio file here or click to browse</div>
              <div style={{color:"var(--text3)",fontSize:13,marginTop:4}}>
                MP3 · WAV · M4A · OGG · FLAC — up to 60 minutes
              </div>
            </>
          )}
        </div>
      )}

      <div style={{ marginTop:20, display:"flex", gap:12, alignItems:"flex-end" }}>
        <div style={{ flex:1 }}>
          <label style={{ fontSize:12, color:"var(--text3)", display:"block", marginBottom:6 }}>
            Scoring Profile
          </label>
          <select value={role} onChange={e=>setRole(e.target.value)}>
            {ROLES.map(r=><option key={r} value={r}>{r.charAt(0).toUpperCase()+r.slice(1)}</option>)}
          </select>
        </div>
        <button className="btn-primary" onClick={analyze}
          disabled={!audioFile||loading}
          style={{ padding:"10px 28px", fontSize:14, borderRadius:8, height:42 }}>
          {loading ? "⏳ Analyzing..." : "Analyze →"}
        </button>
      </div>

      {error && (
        <div style={{ marginTop:16, background:"rgba(237,66,69,0.1)",
          border:"1px solid rgba(237,66,69,0.3)", borderRadius:8,
          padding:"12px 16px", fontSize:13, color:"var(--danger)" }}>
          {error}
        </div>
      )}

      {loading && (
        <div style={{ marginTop:28, textAlign:"center", padding:"20px 0" }}>
          <div style={{ width:40, height:40, border:"3px solid var(--border2)",
            borderTop:"3px solid var(--accent)", borderRadius:"50%",
            animation:"spin 1s linear infinite", margin:"0 auto 16px" }}/>
          <div style={{ color:"var(--text2)", fontSize:14, fontWeight:500 }}>
            Analyzing speech across 7 dimensions...
          </div>
          <div style={{ color:"var(--text3)", fontSize:12, marginTop:4 }}>
            This may take 10–30 seconds
          </div>
        </div>
      )}

      {result && <Results result={result}/>}
    </div>
  );
}

function Results({ result }) {
  const { results, dimensions, metadata, transcript, jobId } = result;
  const gc = GC[results?.grade] || "#5865f2";

  return (
    <div className="fade-in" style={{ marginTop:28 }}>
      <div style={{ height:1, background:"var(--border)", marginBottom:24 }}/>
      <h3 style={{ fontSize:16, fontWeight:700, marginBottom:16, color:"var(--text2)" }}>
        Analysis Results
      </h3>

      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16, marginBottom:16 }}>
        <div className="card" style={{ textAlign:"center", padding:24 }}>
          <div style={{ width:100, height:100, borderRadius:"50%", margin:"0 auto 16px",
            background:"conic-gradient("+gc+" "+results.composite_pct+"%, var(--bg3) 0)",
            display:"flex", alignItems:"center", justifyContent:"center" }}>
            <div style={{ width:76, height:76, borderRadius:"50%", background:"var(--bg2)",
              display:"flex", alignItems:"center", justifyContent:"center" }}>
              <span style={{ fontSize:28, fontWeight:800, color:gc }}>{results.grade}</span>
            </div>
          </div>
          <div style={{ fontSize:26, fontWeight:700 }}>{results.composite_score}/5.0</div>
          <div style={{ color:"var(--text3)", fontSize:13, marginTop:2 }}>{results.composite_pct}% overall</div>
          <div style={{ fontSize:12, color:"var(--text3)", marginTop:4 }}>
            {metadata?.filename} · {metadata?.duration_seconds}s · {metadata?.role}
          </div>
          {results.improvement_priorities?.length>0 && (
            <div style={{ marginTop:14, padding:"10px 12px",
              background:"rgba(237,66,69,0.08)", borderRadius:8,
              border:"1px solid rgba(237,66,69,0.2)", textAlign:"left" }}>
              <div style={{ fontSize:11, color:"var(--danger)", fontWeight:700,
                marginBottom:6, textTransform:"uppercase" }}>Focus Area</div>
              {results.improvement_priorities.map((p,i)=>(
                <div key={i} style={{ fontSize:13, color:"var(--text2)" }}>{i+1}. {p}</div>
              ))}
            </div>
          )}
        </div>
        <div className="card" style={{ display:"flex", alignItems:"center", justifyContent:"center" }}>
          <RadarChart dimensions={dimensions} size={260}/>
        </div>
      </div>

      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:10, marginBottom:16 }}>
        {Object.entries(dimensions).map(([k,d])=>(
          <div key={k} style={{ background:"var(--bg3)", borderRadius:8, padding:"14px 16px",
            border:"1px solid var(--border)", borderLeftWidth:3, borderLeftColor:SC(d.score) }}>
            <div style={{ fontSize:11, fontWeight:600, color:"var(--text3)",
              textTransform:"uppercase", letterSpacing:"0.6px", marginBottom:8 }}>{d.name}</div>
            <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:6 }}>
              <span style={{ fontSize:20, fontWeight:700, color:SC(d.score), minWidth:32 }}>{d.score}</span>
              <div style={{ flex:1, background:"var(--bg4)", borderRadius:4, height:6, overflow:"hidden" }}>
                <div style={{ width:((d.score/5)*100)+"%", height:"100%",
                  background:SC(d.score), borderRadius:4, transition:"width 1s ease" }}/>
              </div>
              <span style={{ fontSize:11, color:"var(--text3)" }}>/5</span>
            </div>
            <div style={{ fontSize:12, color:"var(--text3)", lineHeight:1.5 }}>{d.insight}</div>
          </div>
        ))}
      </div>

      <div style={{ background:"rgba(88,101,242,0.06)", border:"1px solid rgba(88,101,242,0.15)",
        borderRadius:8, padding:16, marginBottom:16 }}>
        <div style={{ fontSize:11, fontWeight:700, color:"var(--accent3)",
          textTransform:"uppercase", letterSpacing:"0.6px", marginBottom:8 }}>Summary</div>
        <p style={{ fontSize:13, lineHeight:1.7, color:"var(--text2)" }}>{results.summary}</p>
      </div>

      <div className="card" style={{ marginBottom:16 }}>
        <div style={{ fontSize:11, fontWeight:700, color:"var(--text3)",
          textTransform:"uppercase", letterSpacing:"0.6px", marginBottom:10 }}>Transcript</div>
        <div style={{ fontSize:13, lineHeight:1.8, color:"var(--text2)",
          maxHeight:120, overflowY:"auto" }}>
          {transcript || "No transcript available."}
        </div>
      </div>

      <div style={{ display:"flex", gap:10 }}>
        <a href={clientAPI.getPdfUrl(jobId)} target="_blank" style={{ textDecoration:"none" }}>
          <button className="btn-secondary" style={{ fontSize:13 }}>📥 Download PDF</button>
        </a>
        <a href={clientAPI.getHtmlUrl(jobId)} target="_blank" style={{ textDecoration:"none" }}>
          <button className="btn-secondary" style={{ fontSize:13 }}>🔗 View HTML Report</button>
        </a>
      </div>
    </div>
  );
}

function ReportsTab() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const SC2 = (s) => s>=4?"#3ba55c":s>=3?"#5865f2":s>=2?"#faa61a":"#ed4245";

  useEffect(()=>{
    clientAPI.myReports()
      .then(r=>setReports(r.data))
      .catch(()=>{})
      .finally(()=>setLoading(false));
  },[]);

  if (loading) return <div style={{color:"var(--text3)",padding:40,textAlign:"center"}}>Loading reports...</div>;

  if (reports.length===0) return (
    <div style={{ textAlign:"center", padding:"60px 0" }}>
      <div style={{ fontSize:48, marginBottom:16 }}>📊</div>
      <h3 style={{ fontSize:18, fontWeight:600, marginBottom:8 }}>No Reports Yet</h3>
      <p style={{ color:"var(--text3)", fontSize:14 }}>
        Go to "Analyze Speech" to record or upload your first audio.
      </p>
    </div>
  );

  return (
    <div>
      <h2 style={{ fontSize:20, fontWeight:700, marginBottom:4 }}>My Reports</h2>
      <p style={{ color:"var(--text3)", fontSize:13, marginBottom:24 }}>
        {reports.length} analysis{reports.length!==1?"es":""} completed
      </p>
      <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
        {reports.map(r=>(
          <div key={r.id} className="card"
            style={{ padding:"16px 20px", cursor:"pointer",
              border:selected?.id===r.id?"1px solid var(--accent)":"1px solid var(--border)",
              transition:"border-color 0.15s" }}
            onClick={()=>setSelected(selected?.id===r.id?null:r)}>
            <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between" }}>
              <div>
                <div style={{ fontWeight:600, fontSize:14, marginBottom:2 }}>
                  {r.filename||"Recording"}
                </div>
                <div style={{ fontSize:12, color:"var(--text3)" }}>
                  {new Date(r.recorded_at).toLocaleString()} · {r.role} · {r.duration_seconds?.toFixed(1)}s
                </div>
              </div>
              <div style={{ display:"flex", alignItems:"center", gap:12 }}>
                <div style={{ textAlign:"right" }}>
                  <div style={{ fontSize:22, fontWeight:700, color:SC2(r.composite_score) }}>
                    {r.composite_score}/5
                  </div>
                  <div style={{ fontSize:11, color:"var(--text3)" }}>Grade {r.grade}</div>
                </div>
                <a href={"/api/v1/report/"+r.job_id+"/pdf"} target="_blank"
                  onClick={e=>e.stopPropagation()} style={{ textDecoration:"none" }}>
                  <button className="btn-secondary" style={{ fontSize:12, padding:"6px 12px" }}>PDF</button>
                </a>
              </div>
            </div>
            {selected?.id===r.id && r.dimensions && (
              <div style={{ marginTop:14, paddingTop:14, borderTop:"1px solid var(--border)" }}>
                <div style={{ display:"grid", gridTemplateColumns:"repeat(7,1fr)", gap:6 }}>
                  {Object.entries(r.dimensions).map(([k,d])=>(
                    <div key={k} style={{ textAlign:"center" }}>
                      <div style={{ fontSize:16, fontWeight:700, color:SC2(d.score) }}>{d.score}</div>
                      <div style={{ fontSize:10, color:"var(--text3)", marginTop:2 }}>
                        {d.name.split(" ")[0]}
                      </div>
                    </div>
                  ))}
                </div>
                {r.transcript && (
                  <div style={{ marginTop:12, fontSize:12, color:"var(--text3)",
                    background:"var(--bg3)", padding:10, borderRadius:6, lineHeight:1.6 }}>
                    {r.transcript.slice(0,200)}{r.transcript.length>200?"...":""}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ClientDashboard() {
  const [tab, setTab] = useState("analyze");
  const { logout, user } = useAuth();

  return (
    <div style={{ display:"flex", minHeight:"100vh" }}>
      <Sidebar tab={tab} setTab={setTab} logout={logout} user={user}/>
      <main style={{ flex:1, padding:"32px 32px", overflowY:"auto", background:"var(--bg)" }}>
        {tab==="analyze" && <AnalyzeTab/>}
        {tab==="reports" && <ReportsTab/>}
      </main>
    </div>
  );
}