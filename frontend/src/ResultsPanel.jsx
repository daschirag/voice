import RadarChart from "./RadarChart";
import { getPdfUrl, getHtmlUrl } from "./api";
const SC=(s)=>s>=4.5?"#34d399":s>=3.5?"#4f8ef7":s>=2.5?"#fbbf24":"#f87171";
const GC={A:"#34d399",B:"#4f8ef7",C:"#fbbf24",D:"#fb923c",F:"#f87171"};
function Bar({score}){return(
  <div style={{display:"flex",alignItems:"center",gap:10}}>
    <div style={{fontSize:22,fontWeight:700,color:SC(score),minWidth:36}}>{score}</div>
    <div style={{flex:1,background:"var(--bg3)",borderRadius:6,height:8,overflow:"hidden"}}>
      <div style={{width:((score/5)*100)+"%",height:"100%",borderRadius:6,background:SC(score),transition:"width 0.8s ease"}}/>
    </div>
    <div style={{fontSize:12,color:"var(--text2)",minWidth:28}}>/5</div>
  </div>
);}
export default function ResultsPanel({ report, jobId, onReset }) {
  if(!report) return null;
  const {results,dimensions,metadata,transcript}=report;
  const gc=GC[results.grade]||"#94a3b8";
  return (
    <div style={{maxWidth:900,margin:"0 auto"}}>
      <div className="card" style={{marginBottom:20}}>
        <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",flexWrap:"wrap",gap:16}}>
          <div>
            <h2 style={{fontSize:20,fontWeight:700,marginBottom:4}}>Analysis Complete</h2>
            <div style={{color:"var(--text2)",fontSize:13}}>
              {metadata.filename} | {metadata.duration_seconds}s | {metadata.role} | ASR {(metadata.asr_confidence*100).toFixed(0)}%
            </div>
          </div>
          <div style={{display:"flex",gap:10}}>
            <a href={getPdfUrl(jobId)} target="_blank" style={{textDecoration:"none"}}><button className="btn-secondary">PDF Report</button></a>
            <a href={getHtmlUrl(jobId)} target="_blank" style={{textDecoration:"none"}}><button className="btn-secondary">HTML Report</button></a>
            <button className="btn-primary" onClick={onReset}>New Analysis</button>
          </div>
        </div>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:20,marginBottom:20}}>
        <div className="card" style={{textAlign:"center",display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center"}}>
          <div style={{width:110,height:110,borderRadius:"50%",background:"conic-gradient("+gc+" "+results.composite_pct+"%, var(--bg3) 0)",display:"flex",alignItems:"center",justifyContent:"center",marginBottom:16}}>
            <div style={{width:86,height:86,borderRadius:"50%",background:"var(--bg2)",display:"flex",alignItems:"center",justifyContent:"center"}}>
              <div style={{fontSize:32,fontWeight:800,color:gc}}>{results.grade}</div>
            </div>
          </div>
          <div style={{fontSize:28,fontWeight:700}}>{results.composite_score}/5.0</div>
          <div style={{color:"var(--text2)",fontSize:14,marginTop:4}}>{results.composite_pct}% overall</div>
          {results.improvement_priorities?.length>0&&(
            <div style={{marginTop:16,padding:"10px 16px",background:"rgba(248,113,113,0.1)",borderRadius:8,border:"1px solid rgba(248,113,113,0.2)",width:"100%"}}>
              <div style={{fontSize:12,color:"var(--danger)",fontWeight:600,marginBottom:6}}>TOP PRIORITY</div>
              {results.improvement_priorities.map((p,i)=><div key={i} style={{fontSize:13,color:"var(--text2)"}}>{i+1}. {p}</div>)}
            </div>
          )}
        </div>
        <div className="card" style={{display:"flex",alignItems:"center",justifyContent:"center"}}>
          <RadarChart dimensions={dimensions} size={300}/>
        </div>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16,marginBottom:20}}>
        {Object.entries(dimensions).map(([k,d])=>(
          <div key={k} className="card" style={{borderLeft:"3px solid "+SC(d.score),padding:"18px 20px"}}>
            <div style={{fontSize:11,fontWeight:700,color:"var(--text2)",textTransform:"uppercase",letterSpacing:"0.8px",marginBottom:10}}>{d.name}</div>
            <Bar score={d.score}/>
            <div style={{fontSize:13,color:"var(--text2)",marginTop:10,lineHeight:1.6}}>{d.insight}</div>
          </div>
        ))}
      </div>
      <div className="card" style={{marginBottom:20,background:"rgba(79,142,247,0.06)",border:"1px solid rgba(79,142,247,0.2)"}}>
        <div style={{fontSize:13,fontWeight:700,color:"var(--accent)",marginBottom:10,textTransform:"uppercase",letterSpacing:"0.8px"}}>Overall Summary</div>
        <p style={{fontSize:14,lineHeight:1.8}}>{results.summary}</p>
      </div>
      <div className="card">
        <div style={{fontSize:13,fontWeight:700,color:"var(--text2)",marginBottom:12,textTransform:"uppercase",letterSpacing:"0.8px"}}>Transcript</div>
        <div style={{background:"var(--bg3)",borderRadius:8,padding:16,fontSize:14,lineHeight:1.8,maxHeight:180,overflowY:"auto"}}>{transcript||"No transcript available."}</div>
      </div>
    </div>
  );
}