import { useState, useRef } from "react";
const ROLES = ["general","sales","executive","interview","coaching"];
const LABELS = {general:"General",sales:"Sales",executive:"Executive",interview:"Interview",coaching:"Coaching"};
const DESC = {general:"Balanced scoring",sales:"Delivery + tone",executive:"Clarity + language",interview:"Clarity + delivery",coaching:"Full feedback"};
export default function UploadPanel({ onSubmit, loading }) {
  const [file,setFile]=useState(null);
  const [role,setRole]=useState("general");
  const [drag,setDrag]=useState(false);
  const ref=useRef();
  const pick=(f)=>{ const ok=["mp3","wav","m4a","ogg","flac","aac"]; if(!ok.includes(f.name.split(".").pop().toLowerCase())){alert("Use MP3 WAV M4A OGG FLAC");return;} setFile(f); };
  return (
    <div className="card" style={{maxWidth:540,margin:"0 auto"}}>
      <div style={{textAlign:"center",marginBottom:28}}>
        <div style={{fontSize:44,marginBottom:8}}>🎙️</div>
        <h2 style={{fontSize:22,fontWeight:700,marginBottom:6}}>Speech Analysis System</h2>
        <p style={{color:"var(--text2)",fontSize:14}}>Upload audio — evaluate 7 communication dimensions</p>
      </div>
      <div onClick={()=>ref.current.click()}
        onDragOver={(e)=>{e.preventDefault();setDrag(true);}}
        onDragLeave={()=>setDrag(false)}
        onDrop={(e)=>{e.preventDefault();setDrag(false);if(e.dataTransfer.files[0])pick(e.dataTransfer.files[0]);}}
        style={{border:"2px dashed "+(drag?"var(--accent)":file?"var(--success)":"var(--border)"),borderRadius:10,padding:"32px 20px",textAlign:"center",cursor:"pointer",transition:"all 0.2s",marginBottom:20,background:drag?"rgba(79,142,247,0.06)":"var(--bg3)"}}>
        <input ref={ref} type="file" hidden accept=".mp3,.wav,.m4a,.ogg,.flac,.aac" onChange={(e)=>e.target.files[0]&&pick(e.target.files[0])}/>
        {file
          ? <div><div style={{fontSize:32,marginBottom:8}}>🎵</div><div style={{fontWeight:600,color:"var(--success)"}}>{file.name}</div><div style={{color:"var(--text2)",fontSize:13,marginTop:4}}>{(file.size/1048576).toFixed(2)} MB — click to change</div></div>
          : <div><div style={{fontSize:32,marginBottom:8}}>📂</div><div style={{fontWeight:600}}>Drop audio file or click to browse</div><div style={{color:"var(--text2)",fontSize:13,marginTop:4}}>MP3 WAV M4A OGG FLAC — up to 60 min</div></div>
        }
      </div>
      <div style={{marginBottom:20}}>
        <div style={{fontSize:13,color:"var(--text2)",marginBottom:8}}>Scoring Profile</div>
        <div style={{display:"grid",gridTemplateColumns:"repeat(5,1fr)",gap:8}}>
          {ROLES.map(r=>(
            <button key={r} onClick={()=>setRole(r)} title={DESC[r]}
              style={{padding:"10px 4px",fontSize:12,borderRadius:8,background:role===r?"linear-gradient(135deg,var(--accent),var(--accent2))":"var(--bg3)",color:role===r?"white":"var(--text2)",border:role===r?"none":"1px solid var(--border)",fontWeight:role===r?700:400}}>
              {LABELS[r]}
            </button>
          ))}
        </div>
        <div style={{color:"var(--text2)",fontSize:12,marginTop:6}}>{DESC[role]}</div>
      </div>
      <button className="btn-primary" onClick={()=>file&&onSubmit(file,role)} disabled={!file||loading}
        style={{width:"100%",padding:"14px",fontSize:15,opacity:(!file||loading)?0.5:1}}>
        {loading?"Analyzing...":"Analyze Speech"}
      </button>
    </div>
  );
}