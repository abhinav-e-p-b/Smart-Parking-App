import { useState, useEffect, useCallback } from "react";

/* ─── Google Fonts ─────────────────────────────────────────────────────── */
const FONTS = `@import url('https://fonts.googleapis.com/css2?family=Russo+One&family=IBM+Plex+Mono:wght@300;400;500;600&family=IBM+Plex+Sans+Condensed:wght@300;400;600;700&display=swap');`;

/* ─── CSS ──────────────────────────────────────────────────────────────── */
const CSS = `
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;background:#07090b}

:root{
  --ink0:#07090b; --ink1:#0b0f12; --ink2:#0f1519; --ink3:#141d24;
  --ink4:#1c2830; --ink5:#243340;
  --wire:#1e2d3a; --wire2:#263b4a; --wire3:#2f4a5e;
  --amber:#f5a623; --amber2:#ffbe4a; --amberdim:rgba(245,166,35,.12);
  --cyan:#00d4ff; --cyandim:rgba(0,212,255,.1);
  --green:#39ff88; --greendim:rgba(57,255,136,.1);
  --red:#ff3952; --reddim:rgba(255,57,82,.1);
  --fog:#4a6478; --fog2:#6a8ba0; --fog3:#94afc3;
  --mono:'IBM Plex Mono',monospace;
  --cond:'IBM Plex Sans Condensed',sans-serif;
  --russo:'Russo One',sans-serif;
}

/* Scanlines */
.scanlines{pointer-events:none;position:fixed;inset:0;z-index:9998;
  background:repeating-linear-gradient(0deg,rgba(0,0,0,0) 0,rgba(0,0,0,0) 1px,rgba(0,0,0,.06) 1px,rgba(0,0,0,.06) 2px);
  mix-blend-mode:multiply}
/* Vignette */
.vignette{pointer-events:none;position:fixed;inset:0;z-index:9997;
  background:radial-gradient(ellipse at center,transparent 55%,rgba(0,0,0,.65) 100%)}

/* ── Layout ── */
.shell{display:flex;height:100vh;overflow:hidden;font-family:var(--cond)}
.sidebar{width:64px;flex-shrink:0;background:var(--ink1);border-right:1px solid var(--wire);
  display:flex;flex-direction:column;align-items:center;padding:16px 0;gap:6px;z-index:10}
.logo-block{width:44px;height:44px;background:var(--amber);display:flex;align-items:center;
  justify-content:center;margin-bottom:20px;flex-shrink:0;
  clip-path:polygon(10% 0%,90% 0%,100% 10%,100% 90%,90% 100%,10% 100%,0% 90%,0% 10%)}
.logo-letter{font-family:var(--russo);font-size:22px;color:var(--ink0);line-height:1}
.nav-btn{width:44px;height:44px;display:flex;align-items:center;justify-content:center;
  cursor:pointer;border:1px solid transparent;color:var(--fog);transition:all .15s;position:relative}
.nav-btn:hover{color:var(--fog3);border-color:var(--wire2);background:var(--ink2)}
.nav-btn.active{color:var(--amber);border-color:var(--amber);background:var(--amberdim)}
.nav-btn .tooltip{position:absolute;left:54px;background:var(--ink4);border:1px solid var(--wire2);
  color:var(--fog3);font-family:var(--mono);font-size:10px;letter-spacing:1.5px;text-transform:uppercase;
  padding:4px 10px;white-space:nowrap;pointer-events:none;opacity:0;transition:opacity .15s;z-index:20}
.nav-btn:hover .tooltip{opacity:1}

.body{flex:1;display:flex;flex-direction:column;overflow:hidden}

/* ── Topbar ── */
.topbar{height:52px;flex-shrink:0;background:var(--ink1);border-bottom:1px solid var(--wire);
  display:flex;align-items:stretch;padding:0}
.topbar-left{display:flex;align-items:center;padding:0 24px;gap:16px;border-right:1px solid var(--wire)}
.page-title{font-family:var(--russo);font-size:15px;letter-spacing:2px;color:var(--fog3);text-transform:uppercase}
.live-badge{display:flex;align-items:center;gap:6px;font-family:var(--mono);font-size:10px;
  letter-spacing:2px;text-transform:uppercase;color:var(--green);padding:4px 10px;
  background:var(--greendim);border:1px solid rgba(57,255,136,.2)}
.pulse{width:6px;height:6px;border-radius:50%;background:var(--green);
  animation:pulse 2s ease-in-out infinite}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(57,255,136,.5)}60%{box-shadow:0 0 0 5px rgba(57,255,136,0)}}
.topbar-right{margin-left:auto;display:flex;align-items:center;gap:0}
.topbar-seg{display:flex;flex-direction:column;justify-content:center;padding:0 20px;
  border-left:1px solid var(--wire)}
.seg-label{font-family:var(--mono);font-size:9px;letter-spacing:2px;color:var(--fog);text-transform:uppercase}
.seg-val{font-family:var(--mono);font-size:13px;font-weight:500;color:var(--fog3);margin-top:1px}
.seg-val.amber{color:var(--amber)}
.seg-val.green{color:var(--green)}
.clock-val{font-family:var(--russo);font-size:15px;color:var(--fog3)}

/* ── Content ── */
.content{flex:1;overflow-y:auto;padding:20px 24px}
.content::-webkit-scrollbar{width:3px}
.content::-webkit-scrollbar-track{background:var(--ink1)}
.content::-webkit-scrollbar-thumb{background:var(--wire3)}

/* ── KPI row ── */
.kpi-row{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}
.kpi{background:var(--ink2);border:1px solid var(--wire);padding:16px 18px;position:relative;overflow:hidden}
.kpi::after{content:'';position:absolute;top:0;left:0;right:0;height:2px}
.kpi.c::after{background:var(--cyan)}
.kpi.g::after{background:var(--green)}
.kpi.a::after{background:var(--amber)}
.kpi.r::after{background:var(--red)}
.kpi-label{font-family:var(--mono);font-size:9px;letter-spacing:2.5px;text-transform:uppercase;
  color:var(--fog);margin-bottom:10px}
.kpi-val{font-family:var(--russo);line-height:1;color:var(--fog3)}
.kpi-val.xl{font-size:42px}
.kpi-val.lg{font-size:36px}
.kpi-val.c{color:var(--cyan)}
.kpi-val.g{color:var(--green)}
.kpi-val.a{color:var(--amber)}
.kpi-val.r{color:var(--red)}
.kpi-sub{font-family:var(--mono);font-size:10px;color:var(--fog);margin-top:6px}
.kpi-bg-glyph{position:absolute;bottom:-8px;right:10px;font-family:var(--russo);
  font-size:72px;color:var(--wire);line-height:1;pointer-events:none;user-select:none}

/* ── Section header ── */
.sh{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}
.sh-title{font-family:var(--mono);font-size:10px;letter-spacing:3px;text-transform:uppercase;
  color:var(--fog2);display:flex;align-items:center;gap:10px}
.sh-title::before{content:'';display:block;width:20px;height:1px;background:var(--wire3)}
.sh-actions{display:flex;gap:8px}

/* ── Occupancy bar ── */
.occ-wrap{background:var(--ink2);border:1px solid var(--wire);padding:18px 22px;margin-bottom:20px}
.occ-meta{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:14px}
.occ-pct{font-family:var(--russo);font-size:44px;color:var(--green);line-height:1}
.occ-detail{text-align:right}
.occ-frac{font-family:var(--mono);font-size:13px;color:var(--fog3)}
.occ-desc{font-family:var(--mono);font-size:10px;color:var(--fog);margin-top:4px;letter-spacing:1px}
.occ-track{height:8px;background:var(--ink4);position:relative}
.occ-fill{height:100%;background:linear-gradient(90deg,var(--green),var(--cyan));transition:width .8s ease;
  position:relative}
.occ-fill::after{content:'';position:absolute;right:0;top:-3px;width:2px;height:14px;background:#fff;opacity:.6}
.occ-segments{display:flex;gap:2px;margin-top:4px}
.occ-seg{flex:1;height:2px;background:var(--wire)}
.occ-seg.filled{background:var(--green);opacity:.5}

/* ── Table ── */
.tbl{background:var(--ink2);border:1px solid var(--wire);margin-bottom:20px}
.tbl-head{display:grid;background:var(--ink3);border-bottom:1px solid var(--wire);
  padding:9px 18px;font-family:var(--mono);font-size:9px;letter-spacing:2.5px;
  text-transform:uppercase;color:var(--fog)}
.tbl-row{display:grid;padding:11px 18px;border-bottom:1px solid var(--wire);
  align-items:center;transition:background .1s;cursor:default}
.tbl-row:last-child{border-bottom:none}
.tbl-row:hover{background:rgba(0,212,255,.025)}
.tbl-row.new{animation:row-in .4s ease}
@keyframes row-in{from{background:rgba(57,255,136,.12)}to{background:transparent}}

/* Grid templates */
.g-dash{grid-template-columns:130px 1fr 110px 90px 80px;gap:14px}
.g-log {grid-template-columns:36px 130px 78px 1fr 1fr 100px;gap:12px}
.g-adm {grid-template-columns:130px 1fr 90px 110px 100px;gap:12px}

/* Cells */
.plate{font-family:var(--mono);font-size:12px;font-weight:500;letter-spacing:2.5px;
  color:var(--amber);background:var(--amberdim);border:1px solid rgba(245,166,35,.25);
  padding:3px 9px;display:inline-flex;align-items:center;gap:6px}
.plate.dim{color:var(--fog2);background:transparent;border-color:var(--wire)}
.t-time{font-family:var(--mono);font-size:11px;color:var(--fog2)}
.t-dur{font-family:var(--mono);font-size:12px;color:var(--fog3)}
.t-sm{font-size:12px;color:var(--fog2)}
.row-n{font-family:var(--mono);font-size:11px;color:var(--fog)}
.conf{font-family:var(--mono);font-size:11px}
.conf.hi{color:var(--green)}
.conf.mid{color:var(--amber)}
.conf.lo{color:var(--red)}

/* Tags */
.tag{font-family:var(--mono);font-size:9px;letter-spacing:1.5px;text-transform:uppercase;
  padding:2px 7px;border:1px solid}
.tag.entry{background:var(--greendim);color:var(--green);border-color:rgba(57,255,136,.3)}
.tag.exit {background:var(--amberdim);color:var(--amber);border-color:rgba(245,166,35,.3)}
.tag.inside{background:var(--cyandim);color:var(--cyan);border-color:rgba(0,212,255,.3)}
.tag.offline{background:var(--reddim);color:var(--red);border-color:rgba(255,57,82,.3)}
.tag.online{background:var(--greendim);color:var(--green);border-color:rgba(57,255,136,.3)}
.tag.low{background:var(--reddim);color:var(--red);border-color:rgba(255,57,82,.3);font-size:9px}

/* Buttons */
.btn{font-family:var(--mono);font-size:10px;letter-spacing:1.5px;text-transform:uppercase;
  padding:7px 14px;cursor:pointer;border:1px solid;background:transparent;transition:all .15s}
.btn-a{color:var(--amber);border-color:var(--amber)}
.btn-a:hover{background:var(--amberdim)}
.btn-c{color:var(--cyan);border-color:var(--cyan)}
.btn-c:hover{background:var(--cyandim)}
.btn-g{color:var(--green);border-color:var(--green)}
.btn-g:hover{background:var(--greendim)}
.btn-r{color:var(--red);border-color:var(--red)}
.btn-r:hover{background:var(--reddim)}
.btn-ghost{color:var(--fog);border-color:var(--wire2)}
.btn-ghost:hover{color:var(--fog3);border-color:var(--wire3)}
.btn.sm{padding:4px 9px;font-size:9px}
.btn.active-filter{background:var(--cyandim);color:var(--cyan);border-color:var(--cyan)}

/* Admin form */
.adm-panel{background:var(--ink2);border:1px solid var(--wire);padding:20px 22px;margin-bottom:16px}
.field-row{display:flex;gap:10px;align-items:flex-end}
.field{display:flex;flex-direction:column;gap:5px;flex:1}
.field-label{font-family:var(--mono);font-size:9px;letter-spacing:2px;text-transform:uppercase;color:var(--fog)}
.field-input{background:var(--ink4);border:1px solid var(--wire2);color:var(--amber2);
  font-family:var(--mono);font-size:13px;letter-spacing:3px;text-transform:uppercase;
  padding:9px 14px;outline:none;transition:border-color .15s}
.field-input:focus{border-color:var(--amber)}
.field-input::placeholder{color:var(--fog);letter-spacing:2px}
.field-hint{font-family:var(--mono);font-size:9px;color:var(--fog);letter-spacing:1px;margin-top:10px;
  border-left:2px solid var(--wire3);padding-left:10px;line-height:1.7}
.export-btns{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
.export-meta{font-family:var(--mono);font-size:10px;color:var(--fog);letter-spacing:1px}

/* Two-col */
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px}

/* Bar chart */
.bar-chart{display:flex;align-items:flex-end;gap:4px;height:72px}
.b-col{flex:1;display:flex;flex-direction:column;align-items:center;gap:3px}
.b-bar{width:100%;background:rgba(0,212,255,.12);border:1px solid rgba(0,212,255,.18);
  transition:background .15s;cursor:default}
.b-bar:hover{background:rgba(0,212,255,.28)}
.b-bar.pk{background:rgba(0,212,255,.3);border-color:var(--cyan)}
.b-lbl{font-family:var(--mono);font-size:8px;color:var(--fog)}

/* Toast */
.toast{position:fixed;bottom:20px;right:24px;z-index:9999;
  background:var(--ink4);border:1px solid var(--green);
  font-family:var(--mono);font-size:11px;color:var(--green);letter-spacing:1px;
  padding:10px 18px;animation:toast-in .2s ease}
.toast.err{border-color:var(--red);color:var(--red)}
@keyframes toast-in{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}

/* Config table */
.cfg-row{display:grid;grid-template-columns:200px 100px 1fr;gap:16px;
  padding:9px 18px;border-bottom:1px solid var(--wire);align-items:center}
.cfg-row:last-child{border-bottom:none}
.cfg-key{font-family:var(--mono);font-size:11px;color:var(--cyan)}
.cfg-val{font-family:var(--mono);font-size:11px;color:var(--amber)}
.cfg-desc{font-size:11px;color:var(--fog2)}

/* Conn indicator */
.conn-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.conn-dot.on{background:var(--green);box-shadow:0 0 6px var(--green)}
.conn-dot.off{background:var(--red)}
`;

/* ─── Static data ──────────────────────────────────────────────────────── */
const ACTIVE = [
  { plate:"MH12AB1234", entry:"09:14:22", dur:"2h 41m", conf:0.94 },
  { plate:"KA05CD5678", entry:"10:02:07", dur:"1h 53m", conf:0.88 },
  { plate:"DL01EF9012", entry:"10:47:55", dur:"1h 07m", conf:0.91 },
  { plate:"TN09GH3456", entry:"11:22:33", dur:"0h 32m", conf:0.79 },
  { plate:"MH14IJ7890", entry:"11:44:01", dur:"0h 11m", conf:0.95 },
];
const LOG_DATA = [
  { id:47, plate:"MH12AB1234", type:"ENTRY", time:"09:14:22", dur:"—",     conf:0.94, flag:"" },
  { id:46, plate:"GJ03KL2345", type:"EXIT",  time:"09:08:11", dur:"1h 22m",conf:0.87, flag:"" },
  { id:45, plate:"KA05CD5678", type:"ENTRY", time:"10:02:07", dur:"—",     conf:0.88, flag:"" },
  { id:44, plate:"UP16MN6789", type:"EXIT",  time:"10:30:45", dur:"3h 04m",conf:0.92, flag:"" },
  { id:43, plate:"DL01EF9012", type:"ENTRY", time:"10:47:55", dur:"—",     conf:0.91, flag:"" },
  { id:42, plate:"RJ14OP0123", type:"EXIT",  time:"10:55:22", dur:"0h 47m",conf:0.83, flag:"" },
  { id:41, plate:"TN09GH3456", type:"ENTRY", time:"11:22:33", dur:"—",     conf:0.79, flag:"" },
  { id:40, plate:"HR26QR4567", type:"EXIT",  time:"11:35:09", dur:"2h 11m",conf:0.96, flag:"" },
  { id:39, plate:"MH14IJ7890", type:"ENTRY", time:"11:44:01", dur:"—",     conf:0.95, flag:"" },
  { id:38, plate:"WB09ST8901", type:"EXIT",  time:"11:58:30", dur:"0h 58m",conf:0.72, flag:"LOW CONF" },
  { id:37, plate:"AP28UV1122", type:"ENTRY", time:"08:22:10", dur:"—",     conf:0.89, flag:"" },
  { id:36, plate:"MH12AB1234", type:"EXIT",  time:"08:18:44", dur:"0h 44m",conf:0.93, flag:"" },
];
const HOURS = [
  {h:"06",v:8},{h:"07",v:22},{h:"08",v:58},{h:"09",v:82},
  {h:"10",v:74},{h:"11",v:61},{h:"12",v:45},{h:"13",v:38},
  {h:"14",v:42},{h:"15",v:63},{h:"16",v:71},{h:"17",v:44},
  {h:"18",v:20},{h:"19",v:12},
];
const maxH = Math.max(...HOURS.map(h=>h.v));

/* ─── Helpers ──────────────────────────────────────────────────────────── */
function confClass(c){ return c>=0.85?"hi":c>=0.75?"mid":"lo" }

function Icon({d,size=16}){
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d={d}/>
    </svg>
  );
}

function Clock(){
  const [t,setT] = useState(new Date());
  useEffect(()=>{const id=setInterval(()=>setT(new Date()),1000);return()=>clearInterval(id)},[]);
  const p=n=>String(n).padStart(2,"0");
  return <span className="clock-val">{p(t.getHours())}:{p(t.getMinutes())}:{p(t.getSeconds())}</span>;
}

/* ─── Dashboard ────────────────────────────────────────────────────────── */
function Dashboard({setToast}){
  const [active,setActive] = useState(ACTIVE);
  const occ = Math.round((active.length/20)*100);

  const forceExit = (plate) => {
    setActive(a=>a.filter(v=>v.plate!==plate));
    setToast({msg:`Exit recorded: ${plate}`,err:false});
    setTimeout(()=>setToast(null),3000);
  };

  return (
    <>
      <div className="kpi-row">
        <div className="kpi c">
          <div className="kpi-label">Inside Now</div>
          <div className={`kpi-val xl c`}>{active.length}</div>
          <div className="kpi-sub">of 20 spaces</div>
          <div className="kpi-bg-glyph">{active.length}</div>
        </div>
        <div className="kpi g">
          <div className="kpi-label">Entries Today</div>
          <div className="kpi-val xl g">47</div>
          <div className="kpi-sub">+12% vs yesterday</div>
          <div className="kpi-bg-glyph">47</div>
        </div>
        <div className="kpi a">
          <div className="kpi-label">Avg Duration</div>
          <div className="kpi-val lg a">1h 38m</div>
          <div className="kpi-sub">43 completed exits</div>
        </div>
        <div className="kpi r">
          <div className="kpi-label">Low Confidence</div>
          <div className="kpi-val xl r">2</div>
          <div className="kpi-sub">readings &lt; 0.80</div>
          <div className="kpi-bg-glyph">!</div>
        </div>
      </div>

      {/* Occupancy */}
      <div className="occ-wrap">
        <div className="sh" style={{marginBottom:14}}>
          <div className="sh-title">Lot Occupancy</div>
        </div>
        <div className="occ-meta">
          <div>
            <div className="occ-pct">{occ}%</div>
            <div className="occ-desc" style={{marginTop:6}}>Real-time · updates on detection</div>
          </div>
          <div className="occ-detail">
            <div className="occ-frac">{active.length} / 20</div>
            <div className="occ-desc">{20-active.length} spaces free</div>
          </div>
        </div>
        <div className="occ-track">
          <div className="occ-fill" style={{width:`${occ}%`}}/>
        </div>
        <div className="occ-segments" style={{marginTop:6}}>
          {Array.from({length:20},(_,i)=>(
            <div key={i} className={`occ-seg ${i<active.length?"filled":""}`}/>
          ))}
        </div>
      </div>

      {/* Active vehicles table */}
      <div className="sh">
        <div className="sh-title">Active Vehicles</div>
        <div style={{display:"flex",alignItems:"center",gap:8}}>
          <div className="pulse"/>
          <span style={{fontFamily:"var(--mono)",fontSize:9,letterSpacing:2,color:"var(--green)"}}>LIVE FEED</span>
        </div>
      </div>
      <div className="tbl">
        <div className="tbl-head g-dash">
          <span>Plate</span><span>Entry Time</span><span>Duration</span><span>Confidence</span><span>Action</span>
        </div>
        {active.length === 0 && (
          <div style={{padding:"24px 18px",fontFamily:"var(--mono)",fontSize:11,color:"var(--fog)",letterSpacing:1}}>
            — No vehicles currently inside —
          </div>
        )}
        {active.map((v,i)=>(
          <div key={v.plate} className="tbl-row g-dash">
            <span className="plate">{v.plate}</span>
            <span className="t-time">{v.entry}</span>
            <span className="t-dur">{v.dur}</span>
            <span className={`conf ${confClass(v.conf)}`}>{Math.round(v.conf*100)}%</span>
            <button className="btn sm btn-r" onClick={()=>forceExit(v.plate)}>EXIT</button>
          </div>
        ))}
      </div>

      {/* Hourly chart */}
      <div className="sh">
        <div className="sh-title">Entries by Hour — Today</div>
      </div>
      <div className="tbl" style={{padding:"18px 20px"}}>
        <div className="bar-chart">
          {HOURS.map((h,i)=>(
            <div key={i} className="b-col">
              <div className={`b-bar ${h.v===maxH?"pk":""}`}
                style={{height:`${(h.v/maxH)*68}px`}} title={`${h.h}:00 — ${h.v}`}/>
              <div className="b-lbl">{h.h}</div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

/* ─── Event Log ────────────────────────────────────────────────────────── */
function EventLog(){
  const [filter,setFilter] = useState("ALL");
  const rows = filter==="ALL" ? LOG_DATA : LOG_DATA.filter(r=>r.type===filter);
  return (
    <>
      <div className="sh">
        <div className="sh-title">Entry / Exit Events — Today</div>
        <div className="sh-actions">
          {["ALL","ENTRY","EXIT"].map(f=>(
            <button key={f} className={`btn sm ${filter===f?"active-filter":"btn-ghost"}`}
              onClick={()=>setFilter(f)}>{f}</button>
          ))}
        </div>
      </div>

      {/* Summary pills */}
      <div style={{display:"flex",gap:12,marginBottom:16}}>
        {[
          {label:"Total Events", val:LOG_DATA.length, col:"var(--fog3)"},
          {label:"Entries",      val:LOG_DATA.filter(r=>r.type==="ENTRY").length, col:"var(--green)"},
          {label:"Exits",        val:LOG_DATA.filter(r=>r.type==="EXIT").length,  col:"var(--amber)"},
          {label:"Flagged",      val:LOG_DATA.filter(r=>r.flag).length,           col:"var(--red)"},
        ].map(({label,val,col})=>(
          <div key={label} style={{background:"var(--ink2)",border:"1px solid var(--wire)",
            padding:"8px 16px",display:"flex",alignItems:"center",gap:12}}>
            <span style={{fontFamily:"var(--mono)",fontSize:9,letterSpacing:2,
              textTransform:"uppercase",color:"var(--fog)"}}>{label}</span>
            <span style={{fontFamily:"var(--russo)",fontSize:20,color:col}}>{val}</span>
          </div>
        ))}
      </div>

      <div className="tbl">
        <div className="tbl-head g-log">
          <span>#</span><span>Plate</span><span>Type</span><span>Timestamp</span><span>Duration</span><span>Conf / Flag</span>
        </div>
        {rows.map((r,i)=>(
          <div key={r.id} className="tbl-row g-log">
            <span className="row-n">{r.id}</span>
            <span className="plate">{r.plate}</span>
            <span><span className={`tag ${r.type.toLowerCase()}`}>{r.type}</span></span>
            <span className="t-time">{r.time}</span>
            <span className="t-dur">{r.dur}</span>
            <div style={{display:"flex",alignItems:"center",gap:8}}>
              <span className={`conf ${confClass(r.conf)}`}>{Math.round(r.conf*100)}%</span>
              {r.flag && <span className="tag low">{r.flag}</span>}
            </div>
          </div>
        ))}
      </div>

      {/* Pagination stub */}
      <div style={{display:"flex",justifyContent:"flex-end",gap:8,marginTop:8}}>
        <button className="btn sm btn-ghost">← Prev</button>
        <button className="btn sm btn-ghost" style={{borderColor:"var(--wire3)",color:"var(--fog3)"}}>1</button>
        <button className="btn sm btn-ghost">Next →</button>
      </div>
    </>
  );
}

/* ─── Admin ─────────────────────────────────────────────────────────────── */
function Admin({setToast}){
  const [plate,setPlate] = useState("");

  const doManualExit = ()=>{
    if(!plate.trim()){setToast({msg:"Enter a plate number",err:true});setTimeout(()=>setToast(null),3000);return;}
    setToast({msg:`Manual exit recorded: ${plate.toUpperCase()}`,err:false});
    setPlate("");
    setTimeout(()=>setToast(null),3000);
  };
  const doExport = (label)=>{
    setToast({msg:`Export started: ${label}`,err:false});
    setTimeout(()=>setToast(null),3000);
  };

  return (
    <>
      <div className="two-col">
        {/* Manual exit */}
        <div>
          <div className="sh"><div className="sh-title">Manual Exit Override</div></div>
          <div className="adm-panel">
            <div className="field-row">
              <div className="field">
                <div className="field-label">License Plate Number</div>
                <input className="field-input" placeholder="MH12AB1234"
                  value={plate} onChange={e=>setPlate(e.target.value)} maxLength={10}/>
              </div>
              <button className="btn btn-r" onClick={doManualExit}>Force Exit</button>
            </div>
            <div className="field-hint">
              USE WHEN: Camera outage on exit · Barrier forced open<br/>
              System restarted during active session<br/>
              Vehicle exited without detection
            </div>
          </div>
        </div>

        {/* Export */}
        <div>
          <div className="sh"><div className="sh-title">Export Log</div></div>
          <div className="adm-panel">
            <div className="export-btns">
              <button className="btn btn-c" onClick={()=>doExport("parking_log.csv")}>Full CSV</button>
              <button className="btn btn-ghost" onClick={()=>doExport("today.csv")}>Today</button>
              <button className="btn btn-ghost" onClick={()=>doExport("week.csv")}>This Week</button>
            </div>
            <div className="export-meta">Last export: 2026-02-23 · 11:00 UTC · 1,204 records</div>
            <div className="field-hint" style={{marginTop:10}}>
              Columns: plate_number · entry_time · exit_time · duration_sec<br/>
              Incomplete exits export with empty exit_time field
            </div>
          </div>
        </div>
      </div>

      {/* Camera status */}
      <div className="sh"><div className="sh-title">Camera Status</div></div>
      <div className="tbl" style={{marginBottom:16}}>
        <div className="tbl-head" style={{display:"grid",gridTemplateColumns:"180px 1fr 90px 90px 110px",gap:12}}>
          <span>Camera</span><span>Source</span><span>Status</span><span>FPS</span><span>Avg Conf</span>
        </div>
        {[
          {name:"Entry Gate · CAM-01", src:"Webcam :0",          on:true,  fps:24, conf:"0.89"},
          {name:"Exit Gate  · CAM-02", src:"RTSP 192.168.1.101", on:true,  fps:22, conf:"0.84"},
          {name:"Overflow   · CAM-03", src:"RTSP 192.168.1.102", on:false, fps:0,  conf:"—"},
        ].map((c,i)=>(
          <div key={i} className="tbl-row" style={{display:"grid",gridTemplateColumns:"180px 1fr 90px 90px 110px",gap:12,alignItems:"center"}}>
            <div style={{display:"flex",alignItems:"center",gap:8}}>
              <div className={`conn-dot ${c.on?"on":"off"}`}/>
              <span style={{fontFamily:"var(--mono)",fontSize:11,color:"var(--fog3)"}}>{c.name}</span>
            </div>
            <span style={{fontFamily:"var(--mono)",fontSize:10,color:"var(--fog)"}}>{c.src}</span>
            <span><span className={`tag ${c.on?"online":"offline"}`}>{c.on?"ONLINE":"OFFLINE"}</span></span>
            <span style={{fontFamily:"var(--mono)",fontSize:11,color:c.on?"var(--fog3)":"var(--fog)"}}>{c.fps>0?`${c.fps} fps`:"—"}</span>
            <span style={{fontFamily:"var(--mono)",fontSize:11,color:c.on?"var(--green)":"var(--fog)"}}>{c.conf}</span>
          </div>
        ))}
      </div>

      {/* Config */}
      <div className="sh"><div className="sh-title">Active Configuration</div></div>
      <div className="tbl">
        {[
          ["CONFIDENCE_THRESHOLD","0.60","Minimum OCR confidence to accept a reading"],
          ["DEBOUNCE_SECONDS","10","Ignore same plate within this window (seconds)"],
          ["DB_PATH","parking.db","SQLite database file path"],
          ["LOG_LEVEL","INFO","Logging verbosity"],
          ["USE_GPU","true","CUDA GPU acceleration for YOLO + EasyOCR"],
          ["PLATE_FORMAT","10-char IND","State(2) + District(2) + Series(2) + Number(4)"],
        ].map(([k,v,d])=>(
          <div key={k} className="cfg-row">
            <span className="cfg-key">{k}</span>
            <span className="cfg-val">{v}</span>
            <span className="cfg-desc">{d}</span>
          </div>
        ))}
      </div>
    </>
  );
}

/* ─── App Shell ────────────────────────────────────────────────────────── */
const NAV = [
  { key:"dashboard", label:"Dashboard", d:"M3 3h8v8H3zM13 3h8v8h-8zM3 13h8v8H3zM13 13h8v8h-8z" },
  { key:"log",       label:"Event Log", d:"M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8zM14 2v6h6M16 13H8M16 17H8M10 9H8" },
  { key:"admin",     label:"Admin",     d:"M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" },
];
const TITLES = { dashboard:"Live Dashboard", log:"Event Log", admin:"System Admin" };

export default function App(){
  const [page,setPage] = useState("dashboard");
  const [toast,setToast] = useState(null);

  return (
    <>
      <style>{FONTS}{CSS}</style>
      <div className="scanlines"/>
      <div className="vignette"/>

      <div className="shell">
        {/* Sidebar */}
        <aside className="sidebar">
          <div className="logo-block"><span className="logo-letter">P</span></div>
          {NAV.map(n=>(
            <div key={n.key} className={`nav-btn ${page===n.key?"active":""}`} onClick={()=>setPage(n.key)}>
              <Icon d={n.d} size={17}/>
              <span className="tooltip">{n.label}</span>
            </div>
          ))}
        </aside>

        <div className="body">
          {/* Topbar */}
          <div className="topbar">
            <div className="topbar-left">
              <span className="page-title">{TITLES[page]}</span>
              <div className="live-badge"><div className="pulse"/>System Active</div>
            </div>
            <div className="topbar-right">
              <div className="topbar-seg">
                <span className="seg-label">Inside</span>
                <span className="seg-val cyan">5 / 20</span>
              </div>
              <div className="topbar-seg">
                <span className="seg-label">Entries Today</span>
                <span className="seg-val green">47</span>
              </div>
              <div className="topbar-seg">
                <span className="seg-label">UTC</span>
                <Clock/>
              </div>
            </div>
          </div>

          {/* Content */}
          <div className="content">
            {page==="dashboard" && <Dashboard setToast={setToast}/>}
            {page==="log"       && <EventLog/>}
            {page==="admin"     && <Admin setToast={setToast}/>}
          </div>
        </div>
      </div>

      {toast && <div className={`toast ${toast.err?"err":""}`}>{toast.err?"✗":"✓"} {toast.msg}</div>}
    </>
  );
}
