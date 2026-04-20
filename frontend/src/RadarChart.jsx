export default function RadarChart({ dimensions, size = 320 }) {
  const items = Object.entries(dimensions || {});
  const n = items.length;
  if (n === 0) return null;
  const cx = size/2, cy = size/2, rMax = size/2 - 55;
  const ang = (i) => Math.PI/2 + (2*Math.PI*i)/n;
  const pt = (i, r) => [cx + r*Math.cos(ang(i)), cy - r*Math.sin(ang(i))];
  const poly = (pts) => pts.map(([x,y]) => x.toFixed(1)+","+y.toFixed(1)).join(" ");
  const COLORS = {5:"#34d399",4:"#4f8ef7",3:"#fbbf24",2:"#fb923c",1:"#f87171"};
  const dataPts = items.map(([,d],i) => { const [x,y]=pt(i,(rMax*d.score)/5); return [x,y,d.score]; });
  return (
    <svg viewBox={"0 0 "+size+" "+size} style={{width:"100%",maxWidth:size}}>
      {[1,2,3,4,5].map(lv=>(
        <polygon key={lv} points={poly(items.map((_,i)=>pt(i,(rMax*lv)/5)))}
          fill="none" stroke="#2e3250" strokeWidth="1"/>
      ))}
      {items.map((_,i)=>{ const [x,y]=pt(i,rMax); return(
        <line key={i} x1={cx} y1={cy} x2={x.toFixed(1)} y2={y.toFixed(1)} stroke="#2e3250" strokeWidth="1"/>
      );})}
      <polygon points={poly(dataPts.map(([x,y])=>[x,y]))}
        fill="rgba(79,142,247,0.18)" stroke="#4f8ef7" strokeWidth="2.5"/>
      {dataPts.map(([x,y,s],i)=>(
        <circle key={i} cx={x.toFixed(1)} cy={y.toFixed(1)} r="5"
          fill={COLORS[Math.round(s)]||"#4f8ef7"} stroke="#0f1117" strokeWidth="2"/>
      ))}
      {items.map(([,d],i)=>{
        const [lx,ly]=[cx+(rMax+40)*Math.cos(ang(i)), cy-(rMax+40)*Math.sin(ang(i))];
        const anchor = lx<cx-10?"end":lx>cx+10?"start":"middle";
        const nm = d.name.replace(" Quality","").replace(" Words","").replace(" Patterns","").replace(" Use","").replace(" / Demeanor","");
        return(
          <g key={i}>
            <text x={lx.toFixed(1)} y={ly.toFixed(1)} fontSize="11" fill="#94a3b8" textAnchor={anchor} dominantBaseline="middle">{nm}</text>
            <text x={lx.toFixed(1)} y={(ly+13).toFixed(1)} fontSize="10" fill={COLORS[Math.round(d.score)]||"#4f8ef7"} textAnchor={anchor} fontWeight="bold">{d.score}/5</text>
          </g>
        );
      })}
    </svg>
  );
}