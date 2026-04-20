import { useState, useEffect, useRef } from "react";
import UploadPanel from "./UploadPanel";
import ProgressPanel from "./ProgressPanel";
import ResultsPanel from "./ResultsPanel";
import { analyzeAudio, getStatus, getReport } from "./api";

export default function App() {
  const [view,setView]=useState("upload");
  const [jobId,setJobId]=useState(null);
  const [report,setReport]=useState(null);
  const [progress,setProgress]=useState(0);
  const [stage,setStage]=useState("");
  const [message,setMessage]=useState("");
  const [error,setError]=useState(null);
  const poll=useRef(null);

  const stopPoll=()=>{ if(poll.current){clearInterval(poll.current);poll.current=null;} };

  const startPoll=(id)=>{
    stopPoll();
    poll.current=setInterval(async()=>{
      try{
        const {data}=await getStatus(id);
        setStage(data.stage||""); setProgress(data.progress||0); setMessage(data.message||"");
        if(data.status==="completed"){ stopPoll(); const {data:r}=await getReport(id); setReport(r); setView("results"); }
        else if(data.status==="failed"){ stopPoll(); setError(data.error||"Failed"); setView("upload"); }
      }catch(e){ console.error(e); }
    },1500);
  };

  const handleSubmit=async(file,role)=>{
    setError(null); setView("progress"); setProgress(5); setStage("preprocessing"); setMessage("Uploading...");
    try{
      const {data}=await analyzeAudio(file,role);
      setJobId(data.job_id);
      if(data.status==="completed"){ const {data:r}=await getReport(data.job_id); setReport(r); setView("results"); }
      else startPoll(data.job_id);
    }catch(e){ setError(e.response?.data?.detail||e.message||"Upload failed"); setView("upload"); }
  };

  const handleReset=()=>{ stopPoll(); setView("upload"); setJobId(null); setReport(null); setProgress(0); setStage(""); setError(null); };
  useEffect(()=>()=>stopPoll(),[]);

  return (
    <div style={{minHeight:"100vh",padding:"32px 16px"}}>
      <nav style={{maxWidth:900,margin:"0 auto 32px",display:"flex",alignItems:"center",justifyContent:"space-between"}}>
        <div style={{display:"flex",alignItems:"center",gap:10}}>
          <span style={{fontSize:24}}>🎙️</span>
          <span style={{fontWeight:700,fontSize:18}}>SpeechAnalysis</span>
          <span style={{background:"rgba(79,142,247,0.15)",color:"var(--accent)",fontSize:11,padding:"2px 8px",borderRadius:20,fontWeight:600}}>v1.0</span>
        </div>
        <div style={{display:"flex",gap:8}}>
          <a href="http://localhost:8000/docs" target="_blank" style={{textDecoration:"none"}}><button className="btn-secondary" style={{fontSize:12,padding:"8px 14px"}}>API Docs</button></a>
          <a href="http://localhost:8000/api/v1/health" target="_blank" style={{textDecoration:"none"}}><button className="btn-secondary" style={{fontSize:12,padding:"8px 14px"}}>Health</button></a>
        </div>
      </nav>
      {error&&<div style={{maxWidth:540,margin:"0 auto 20px",background:"rgba(248,113,113,0.12)",border:"1px solid rgba(248,113,113,0.3)",borderRadius:10,padding:"12px 16px",color:"var(--danger)",fontSize:14}}>Error: {error}</div>}
      {view==="upload"&&<UploadPanel onSubmit={handleSubmit} loading={false}/>}
      {view==="progress"&&<ProgressPanel stage={stage} progress={progress} message={message}/>}
      {view==="results"&&<ResultsPanel report={report} jobId={jobId} onReset={handleReset}/>}
    </div>
  );
}