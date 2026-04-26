export default function RadarChart({ dimensions, size = 300 }) {
  const items = Object.entries(dimensions || {});
  const n = items.length;
  if (n === 0) return null;
  const cx = size/2, cy = size/2, rMax = size/2 - 52;
  const ang = (i) => Math.PI/2 + (2*Math.PI*i)/n;
  const pt = (i, r) => [cx + r*Math.cos(ang(i)), cy - r*Math.sin(ang(i))];
  const poly = (pts) => pts.map(([x,y]) => x.toFixed(1)+","+y.toFixed(1)).join(" ");
  const SC = {5:"#3ba55c",4:"#5865f2",3:"#faa61a",2:"#ed4245",1:"#ed4245"};
  const dataPts = items.map(([,d],i) => { const [x,y]=pt(i,(rMax*d.score)/5); return [x,y,d.score]; });
  return (
    <svg viewBox={"0 0 "+size+" "+size} style={{width:"100%",maxWidth:size}}>
      {[1,2,3,4,5].map(lv=>(
        <polygon key={lv} points={poly(items.map((_,i)=>pt(i,(rMax*lv)/5)))}
          fill={lv===5?"rgba(88,101,242,0.04)":"none"}
          stroke={lv===5?"#333":"#222"} strokeWidth={lv===5?"1":"0.5"}/>
      ))}
      {items.map((_,i)=>{ const [x,y]=pt(i,rMax); return(
        <line key={i} x1={cx} y1={cy} x2={x.toFixed(1)} y2={y.toFixed(1)} stroke="#2a2a2a" strokeWidth="1"/>
      );})}
      <polygon points={poly(dataPts.map(([x,y])=>[x,y]))}
        fill="rgba(88,101,242,0.15)" stroke="#5865f2" strokeWidth="2"/>
      {dataPts.map(([x,y,s],i)=>(
        <circle key={i} cx={x.toFixed(1)} cy={y.toFixed(1)} r="4"
          fill={SC[Math.round(s)]||"#5865f2"} stroke="var(--bg2)" strokeWidth="2"/>
      ))}
      {items.map(([,d],i)=>{
        const [lx,ly]=[cx+(rMax+38)*Math.cos(ang(i)),cy-(rMax+38)*Math.sin(ang(i))];
        const anchor=lx<cx-10?"end":lx>cx+10?"start":"middle";
        const nm=d.name.replace(" Quality","").replace(" Words","").replace(" Patterns","").replace(" Use","").replace(" / Demeanor","");
        return(
          <g key={i}>
            <text x={lx.toFixed(1)} y={ly.toFixed(1)} fontSize="10" fill="#72767d" textAnchor={anchor} dominantBaseline="middle">{nm}</text>
            <text x={lx.toFixed(1)} y={(ly+12).toFixed(1)} fontSize="10"
              fill={SC[Math.round(d.score)]||"#5865f2"} textAnchor={anchor} fontWeight="700">{d.score}/5</text>
          </g>
        );
      })}
    </svg>
  );
}