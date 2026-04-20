const STAGES=[
  {key:"preprocessing",label:"Pre-processing Audio"},
  {key:"transcription",label:"Transcribing Speech"},
  {key:"vad",label:"Detecting Pauses"},
  {key:"analysis",label:"Analyzing 7 Dimensions"},
  {key:"scoring",label:"Calculating Scores"},
  {key:"reports",label:"Generating Reports"},
];
const ICONS=["🔧","🎙️","📊","🧠","⭐","📄"];
export default function ProgressPanel({ stage, progress, message }) {
  const cur=STAGES.findIndex(s=>s.key===stage);
  return (
    <div className="card" style={{maxWidth:500,margin:"0 auto"}}>
      <div style={{textAlign:"center",marginBottom:28}}>
        <div style={{fontSize:40,marginBottom:10,display:"inline-block",animation:"spin 2s linear infinite"}}>⚙️</div>
        <h3 style={{fontSize:18,fontWeight:700}}>Analyzing your speech...</h3>
        <p style={{color:"var(--text2)",fontSize:14,marginTop:4}}>{message||"Processing..."}</p>
      </div>
      <div style={{marginBottom:24}}>
        <div style={{display:"flex",justifyContent:"space-between",fontSize:13,color:"var(--text2)",marginBottom:8}}>
          <span>Progress</span><span>{progress||0}%</span>
        </div>
        <div style={{background:"var(--bg3)",borderRadius:8,height:10,overflow:"hidden"}}>
          <div style={{height:"100%",borderRadius:8,background:"linear-gradient(90deg,var(--accent),var(--accent2))",width:(progress||0)+"%",transition:"width 0.5s ease"}}/>
        </div>
      </div>
      <div style={{display:"flex",flexDirection:"column",gap:8}}>
        {STAGES.map((s,i)=>{
          const done=i<cur, active=i===cur;
          return(
            <div key={s.key} style={{display:"flex",alignItems:"center",gap:12,padding:"10px 14px",borderRadius:8,background:active?"rgba(79,142,247,0.1)":done?"rgba(52,211,153,0.06)":"transparent",border:active?"1px solid rgba(79,142,247,0.3)":done?"1px solid rgba(52,211,153,0.2)":"1px solid transparent"}}>
              <span style={{fontSize:18,width:24,textAlign:"center"}}>{done?"✅":active?"⏳":ICONS[i]}</span>
              <span style={{fontSize:14,fontWeight:active?600:400,color:active?"var(--accent)":done?"var(--success)":"var(--text2)"}}>{s.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}