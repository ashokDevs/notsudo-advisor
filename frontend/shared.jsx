// shared.jsx — Logo, Pipeline animation, atoms, fake advisory data
// Exported to window for both Landing and Dashboard pages.

const { useState, useEffect, useRef, useMemo, useCallback, Fragment } = React;

// F = Fragment-replacement that accepts data-om-id and other arbitrary attrs
// without React warnings. Renders as display:contents so children flow through.
function F({ children, style, ...rest }) {
  return <div style={{ display:"contents", ...(style||{}) }} {...rest}>{children}</div>;
}

// ─────────────────────────────────────────────────────────────
// LOGO  —  mixed-case wordmark with a geometric "denied" glyph
// (a hollow square with a diagonal slash, suggesting "not sudo")
// ─────────────────────────────────────────────────────────────
function Logo({ size = 22, color = "currentColor" }) {
  const s = size;
  return (
    <span style={{ display:"inline-flex", alignItems:"center", gap:9, color }}>
      <svg width={s} height={s} viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <rect x="3.5" y="3.5" width="17" height="17" rx="3"
              stroke={color} strokeWidth="1.6" />
        <line x1="6.5" y1="17.5" x2="17.5" y2="6.5"
              stroke={color} strokeWidth="1.6" strokeLinecap="round" />
        <circle cx="12" cy="12" r="1.7" fill={color} />
      </svg>
      <span style={{
        fontFamily:"var(--font-mono)",
        fontWeight:600,
        fontSize: Math.round(size * 0.78),
        letterSpacing:"-0.01em",
        color,
      }}>
        <span style={{opacity:0.95}}>Not</span><span>Sudo</span>
      </span>
    </span>
  );
}

// ─────────────────────────────────────────────────────────────
// FAKE ADVISORY DATA  —  used by hero pipeline + dashboard table
// ─────────────────────────────────────────────────────────────
const ADVISORIES = [
  {
    id: "GHSA-7w7v-r4w8-x5p3",
    pkg: "lodash",
    range: "<4.17.21",
    current: "4.17.20",
    fix: "4.17.21",
    cvss: 7.4,
    severity: "high",
    title: "Prototype pollution in lodash.merge",
    function: "lodash.merge()",
    callsites: 0,
    verdict: "safe",
    confidence: 0.94,
    cost: 0.12,
    elapsed: 38,
    reasoning: "lodash.merge is imported but only used in /scripts/build-stats.js, a Node script that runs at build time outside the web request lifecycle. No path from src/server/** reaches a merge() call.",
    quote: "Versions of lodash prior to 4.17.21 are vulnerable to Prototype Pollution via the merge, mergeWith, and defaultsDeep functions when an attacker controls the source object.",
    quoteSource: "GHSA-7w7v-r4w8-x5p3 § Details",
    entrypoints: ["src/server/app.ts", "src/api/*.ts"],
    nodes: ["triage", "reach", "evidence", "verdict"],
  },
  {
    id: "GHSA-xvch-5gv4-984h",
    pkg: "minimist",
    range: "<1.2.6",
    current: "1.2.5",
    fix: "1.2.6",
    cvss: 9.1,
    severity: "critical",
    title: "Prototype pollution in argument parser",
    function: "minimist(argv)",
    callsites: 3,
    verdict: "exposed",
    confidence: 0.88,
    cost: 0.21,
    elapsed: 51,
    reasoning: "minimist is called from src/cli/serve.ts which IS the production entry point (referenced by Dockerfile CMD). User-controlled flags can pollute Object.prototype before the HTTP server starts.",
    quote: "minimist before 1.2.6 is vulnerable to Prototype Pollution via file index.js, function setKey(), because of an incomplete fix for CVE-2020-7598.",
    quoteSource: "GHSA-xvch-5gv4-984h § Details",
    entrypoints: ["src/cli/serve.ts", "Dockerfile:14"],
    nodes: ["triage", "reach", "evidence", "verdict"],
  },
  {
    id: "GHSA-c2qf-rxjj-qqgw",
    pkg: "semver",
    range: ">=7.0.0 <7.5.2",
    current: "7.5.1",
    fix: "7.5.2",
    cvss: 5.3,
    severity: "moderate",
    title: "ReDoS in semver range parsing",
    function: "new Range()",
    callsites: 1,
    verdict: "unsure",
    confidence: 0.58,
    cost: 0.18,
    elapsed: 47,
    reasoning: "Reaches src/lib/version-check.ts which validates a user-supplied version string. Reachable, but inputs are constrained to ^\\d+\\.\\d+\\.\\d+$ upstream — couldn't prove the malicious pattern can land. Flagging for human review.",
    quote: "Versions of the package semver before 7.5.2 are vulnerable to Regular Expression Denial of Service via the function new Range, when untrusted user data is provided as a range.",
    quoteSource: "GHSA-c2qf-rxjj-qqgw § Details",
    entrypoints: ["src/lib/version-check.ts"],
    nodes: ["triage", "reach", "evidence", "verdict"],
  },
  {
    id: "GHSA-9wv6-86v2-598j",
    pkg: "path-parse",
    range: "<1.0.7",
    current: "1.0.6",
    fix: "1.0.7",
    cvss: 5.3,
    severity: "moderate",
    title: "ReDoS in splitDeviceRe",
    function: "path.parse()",
    callsites: 0,
    verdict: "safe",
    confidence: 0.97,
    cost: 0.09,
    elapsed: 22,
    reasoning: "Transitive dep of @babel/core — present only in devDependencies. No runtime entry point reaches it. Killed at triage by the cheap classifier.",
    quote: "path-parse before 1.0.7 is vulnerable to Regular Expression Denial of Service.",
    quoteSource: "GHSA-9wv6-86v2-598j § Details",
    entrypoints: ["(none — devDependency only)"],
    nodes: ["triage"],
  },
  {
    id: "GHSA-rv95-896h-c2vc",
    pkg: "express",
    range: "<4.19.2",
    current: "4.18.0",
    fix: "4.19.2",
    cvss: 6.1,
    severity: "moderate",
    title: "Open redirect via malformed URLs",
    function: "res.redirect()",
    callsites: 4,
    verdict: "exposed",
    confidence: 0.81,
    cost: 0.24,
    elapsed: 62,
    reasoning: "Four call sites to res.redirect() take values derived from req.query.next without an allow-list. Reachable from POST /auth/callback in src/server/routes/auth.ts.",
    quote: "Versions of Express prior to 4.19.2 do not perform encoding on the redirect URL allowing for the possibility of open redirect.",
    quoteSource: "GHSA-rv95-896h-c2vc § Details",
    entrypoints: ["src/server/routes/auth.ts:42"],
    nodes: ["triage", "reach", "evidence", "verdict"],
  },
  {
    id: "GHSA-3xgq-45jj-v275",
    pkg: "tar",
    range: "<6.2.1",
    current: "6.2.0",
    fix: "6.2.1",
    cvss: 8.2,
    severity: "high",
    title: "Symlink overwrite during extraction",
    function: "tar.extract()",
    callsites: 0,
    verdict: "safe",
    confidence: 0.92,
    cost: 0.11,
    elapsed: 29,
    reasoning: "tar is pulled in by node-gyp as a build-time transitive. It is never imported from any file under src/.",
    quote: "Versions of tar before 6.2.1 are vulnerable to a symbolic link overwrite vulnerability during archive extraction.",
    quoteSource: "GHSA-3xgq-45jj-v275 § Details",
    entrypoints: ["(none — build-time only)"],
    nodes: ["triage", "reach"],
  },
];

// ─────────────────────────────────────────────────────────────
// PIPELINE NODES  —  metadata for the 4 stages
// ─────────────────────────────────────────────────────────────
const NODES = [
  { id: "triage",   label: "Triage",       sub: "cheap classifier",   color: "var(--node-1)",  glyph: "01" },
  { id: "reach",    label: "Reachability", sub: "call-graph trace",   color: "var(--node-2)",  glyph: "02" },
  { id: "evidence", label: "Evidence",     sub: "quote validator",    color: "var(--node-3)",  glyph: "03" },
  { id: "verdict",  label: "Verdict",      sub: "frontier reasoner",  color: "var(--node-4)",  glyph: "04" },
];

// ─────────────────────────────────────────────────────────────
// PIPELINE  —  live animated 4-node trace
// Driven by an external `tick` (0..total) so it can be played
// continuously on the landing hero, or scrubbed in the dashboard.
// ─────────────────────────────────────────────────────────────
const STAGE_DURATION_MS = 1700;     // per node
const TICK_MS = 60;

function usePipelineRunner(advisories) {
  const [advIdx, setAdvIdx] = useState(0);
  const [stage, setStage] = useState(-1);   // -1 = idle/intro, 0..3 nodes, 4 = done
  const [stageProgress, setStageProgress] = useState(0); // 0..1 within stage
  const advisory = advisories[advIdx];
  const maxStage = advisory.nodes.length - 1;

  useEffect(() => {
    let t0 = performance.now();
    let raf;
    let curStage = -1;
    const introMs = 700;
    const holdMs = 1500;

    function frame(now) {
      const dt = now - t0;
      if (curStage === -1) {
        if (dt >= introMs) { curStage = 0; t0 = now; setStage(0); setStageProgress(0); }
        else { setStage(-1); setStageProgress(dt / introMs); }
      } else if (curStage <= maxStage) {
        const p = Math.min(1, dt / STAGE_DURATION_MS);
        setStageProgress(p);
        setStage(curStage);
        if (p >= 1) {
          if (curStage === maxStage) {
            curStage = maxStage + 1;
            t0 = now;
            setStage(maxStage + 1);
          } else {
            curStage += 1;
            t0 = now;
            setStageProgress(0);
          }
        }
      } else {
        // hold then advance to next advisory
        if (dt >= holdMs) {
          setAdvIdx(i => (i + 1) % advisories.length);
          curStage = -1;
          t0 = now;
          setStage(-1);
          setStageProgress(0);
        }
      }
      raf = requestAnimationFrame(frame);
    }
    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, [advIdx, maxStage, advisories.length]);

  return { advisory, advIdx, stage, stageProgress, maxStage };
}

// Pipeline visual. Compact + dense.
function Pipeline({ advisory, stage, stageProgress, maxStage }) {
  // stage: -1 intro, 0..maxStage active, maxStage+1 done
  const isDone = stage > maxStage;
  const verdictPill = isDone ? advisory.verdict : null;

  return (
    <div style={{
      background: "var(--surface)",
      border: "1px solid var(--border)",
      borderRadius: "var(--r-xl)",
      overflow: "hidden",
      fontFamily:"var(--font-mono)",
      fontSize: 12,
      color: "var(--text-2)",
      boxShadow: "0 30px 80px -30px rgba(0,0,0,0.6)",
    }}>
      {/* terminal header */}
      <div style={{
        display:"flex", alignItems:"center", justifyContent:"space-between",
        padding:"10px 14px", borderBottom:"1px solid var(--border)",
        background:"var(--surface-2)",
      }}>
        <div style={{display:"flex", alignItems:"center", gap:10, color:"var(--text-3)", fontSize:11}}>
          <span style={{display:"inline-flex", gap:5}}>
            <span style={{width:9,height:9,borderRadius:"50%",background:"#3a4356"}}></span>
            <span style={{width:9,height:9,borderRadius:"50%",background:"#3a4356"}}></span>
            <span style={{width:9,height:9,borderRadius:"50%",background:"#3a4356"}}></span>
          </span>
          <span style={{letterSpacing:"0.04em"}}>notsudo · advisor.live</span>
        </div>
        <div style={{display:"flex", alignItems:"center", gap:8, fontSize:10, color:"var(--text-muted)"}}>
          <span style={{
            width:7, height:7, borderRadius:"50%",
            background:"var(--safe-2)", boxShadow:"0 0 8px var(--safe-2)",
            animation:"pulse-dot 1.6s ease-in-out infinite",
          }}></span>
          <span style={{textTransform:"uppercase", letterSpacing:"0.12em"}}>streaming</span>
        </div>
      </div>

      {/* input row */}
      <div style={{
        padding:"14px 18px 10px",
        borderBottom:"1px dashed var(--border)",
        display:"flex", alignItems:"baseline", gap:10, flexWrap:"wrap",
        whiteSpace:"nowrap",
      }}>
        <span style={{color:"var(--text-muted)"}}>$</span>
        <span style={{color:"var(--text-3)"}}>advisor</span>
        <span style={{color:"var(--node-2)"}}>{advisory.id}</span>
        <span style={{color:"var(--text-faint)"}}>——›</span>
        <span style={{color:"var(--text-2)"}}>acme/payments-api</span>
      </div>

      {/* advisory meta */}
      <div style={{
        padding:"12px 18px",
        display:"flex", alignItems:"center", gap:18, flexWrap:"wrap",
        fontSize: 12,
        borderBottom:"1px solid var(--border)",
      }}>
        <PipelineMeta label="package" value={`${advisory.pkg}@${advisory.range}`} />
        <PipelineMeta label="cvss"    value={advisory.cvss.toFixed(1)} accent={severityColor(advisory.severity)} />
        <PipelineMeta label="title"   value={advisory.title} muted />
      </div>

      {/* nodes */}
      <div style={{ padding:"22px 18px 14px", position:"relative" }}>
        <PipelineRail nodes={NODES} stage={stage} stageProgress={stageProgress} maxStage={maxStage} />
      </div>

      {/* verdict footer */}
      <div style={{
        padding:"12px 18px 16px",
        borderTop:"1px solid var(--border)",
        background:"var(--bg-deep)",
        minHeight: 62,
        display:"flex", alignItems:"center", justifyContent:"space-between", gap:16,
      }}>
        <div style={{display:"flex", alignItems:"center", gap:14, flexWrap:"wrap"}}>
          <span style={{color:"var(--text-muted)", fontSize:11, letterSpacing:"0.1em", textTransform:"uppercase"}}>verdict</span>
          {verdictPill ? <VerdictPill v={verdictPill} /> : <span style={{color:"var(--text-faint)"}}>…computing</span>}
          {isDone && (
            <span style={{color:"var(--text-3)", fontSize:11}}>
              confidence <span style={{color:"var(--text)"}}>{(advisory.confidence*100).toFixed(0)}%</span>
              &nbsp;·&nbsp;cost <span style={{color:"var(--text)"}}>${advisory.cost.toFixed(2)}</span>
              &nbsp;·&nbsp;<span style={{color:"var(--text)"}}>{advisory.elapsed}s</span>
            </span>
          )}
        </div>
        <span style={{color:"var(--text-faint)", fontSize:11}}>
          {String(advisory.id).slice(-6)}
        </span>
      </div>
    </div>
  );
}

function PipelineMeta({ label, value, accent, muted }) {
  return (
    <span style={{display:"inline-flex", alignItems:"baseline", gap:7}}>
      <span style={{color:"var(--text-muted)", fontSize:11, letterSpacing:"0.08em", textTransform:"uppercase"}}>{label}</span>
      <span style={{color: accent || (muted ? "var(--text-3)" : "var(--text)") }}>{value}</span>
    </span>
  );
}

function PipelineRail({ nodes, stage, stageProgress, maxStage }) {
  return (
    <div style={{position:"relative"}}>
      {/* connecting line + flow */}
      <svg width="100%" height="2" style={{position:"absolute", top: 17, left: 0, right: 0, overflow:"visible"}}>
        <line x1="6%" x2="94%" y1="1" y2="1" stroke="var(--border-strong)" strokeWidth="1" />
        {stage >= 0 && (() => {
          const completedFraction = Math.min(1, (stage + stageProgress) / nodes.length);
          return (
            <line x1="6%" x2={`${6 + completedFraction*88}%`} y1="1" y2="1"
                  stroke="var(--primary)" strokeWidth="1.5" strokeLinecap="round" />
          );
        })()}
      </svg>

      <div style={{display:"grid", gridTemplateColumns:`repeat(${nodes.length}, 1fr)`, gap: 8, position:"relative"}}>
        {nodes.map((n, i) => {
          const isActive = stage === i;
          const isDone = stage > i;
          const isFuture = stage < i && stage !== -1;
          return (
            <PipelineNode key={n.id}
              node={n} index={i}
              active={isActive}
              done={isDone}
              future={isFuture}
              progress={isActive ? stageProgress : (isDone ? 1 : 0)}
              skipped={maxStage < i && stage > maxStage}
            />
          );
        })}
      </div>
    </div>
  );
}

function PipelineNode({ node, index, active, done, future, progress, skipped }) {
  const dimmed = future;
  const bgRing = active ? node.color : (done ? node.color : "var(--border-strong)");
  return (
    <div style={{display:"flex", flexDirection:"column", alignItems:"center", gap:8, opacity: dimmed ? 0.42 : 1, transition:"opacity .25s"}}>
      <div style={{
        position:"relative",
        width: 36, height: 36, borderRadius: "50%",
        background: active ? `radial-gradient(circle at center, ${node.color}22 0%, transparent 70%)` : "transparent",
        display:"flex", alignItems:"center", justifyContent:"center",
      }}>
        <div style={{
          width: 12, height: 12, borderRadius:"50%",
          background: (active || done) ? node.color : "var(--bg)",
          border: `1.5px solid ${bgRing}`,
          boxShadow: active ? `0 0 16px ${node.color}, 0 0 0 4px ${node.color}22` : "none",
          transition:"all .25s",
        }} />
        {active && (
          <svg style={{position:"absolute", inset: 0}} viewBox="0 0 36 36">
            <circle cx="18" cy="18" r="16.5" fill="none" stroke={node.color} strokeWidth="1" strokeOpacity="0.35"
                    strokeDasharray={`${progress*103} 200`} transform="rotate(-90 18 18)" />
          </svg>
        )}
      </div>
      <div style={{textAlign:"center", lineHeight: 1.3}}>
        <div style={{fontSize:11, color: (active||done) ? "var(--text)" : "var(--text-3)", fontWeight: 500}}>
          <span style={{color:"var(--text-muted)", marginRight: 6}}>{node.glyph}</span>{node.label}
        </div>
        <div style={{fontSize:10, color:"var(--text-muted)", marginTop: 2}}>{node.sub}</div>
        {skipped && index > 0 && (
          <div style={{fontSize:9.5, color:"var(--text-faint)", marginTop:3, fontStyle:"italic"}}>skipped</div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// VERDICT PILL
// ─────────────────────────────────────────────────────────────
function VerdictPill({ v, size = "md" }) {
  const map = {
    exposed:  { cls:"pill--exposed",  label:"EXPOSED" },
    safe:     { cls:"pill--safe",     label:"NOT REACHABLE" },
    unsure:   { cls:"pill--unsure",   label:"UNSURE" },
    pending:  { cls:"pill--neutral",  label:"PENDING" },
  };
  const m = map[v] || map.pending;
  return (
    <span className={`pill ${m.cls}`} style={size==="lg" ? {fontSize:12, padding:"5px 10px"} : null}>
      <span className="dot" />{m.label}
    </span>
  );
}

function severityColor(s) {
  if (s === "critical") return "var(--danger-2)";
  if (s === "high")     return "var(--warn-2)";
  if (s === "moderate") return "var(--primary-2)";
  return "var(--text-3)";
}

// ─────────────────────────────────────────────────────────────
// SPARKLINE  — tiny inline chart for dashboard stats
// ─────────────────────────────────────────────────────────────
function Sparkline({ data, color = "var(--primary)", w = 96, h = 28 }) {
  const max = Math.max(...data), min = Math.min(...data);
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / Math.max(1, max - min)) * (h - 4) - 2;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  return (
    <svg width={w} height={h} style={{display:"block"}}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// expose
Object.assign(window, {
  F,
  Logo, Pipeline, PipelineRail, PipelineNode, VerdictPill, Sparkline,
  usePipelineRunner, ADVISORIES, NODES, severityColor,
});
