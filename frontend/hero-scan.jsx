// hero-scan.jsx — cinematic security scan console for the landing hero.
// Drizzle-inspired: dense monospace, streaming log, one accent color, ASCII rhythm.

// A scrolling stream of analysis events for a fake repo scan.
// Each event has: kind (info / scan / hit / clear / verdict), text, package, optional verdict.
const SCAN_EVENTS = [
  { kind:"info",  t:"$ notsudo scan acme/payments-api --branch main" },
  { kind:"info",  t:"+ resolved 487 deps · 36 advisories matched" },
  { kind:"sep" },

  { kind:"scan",  t:"node[01] triage", sub:"lodash@<4.17.21 · GHSA-7w7v-r4w8-x5p3" },
  { kind:"clear", t:"node[02] reachability", sub:"no path from entry → lodash.merge" },
  { kind:"hit",   t:"VERDICT", sub:"NOT REACHABLE · 94% · $0.12 · 38s", v:"safe" },
  { kind:"sep" },

  { kind:"scan",  t:"node[01] triage", sub:"minimist@<1.2.6 · GHSA-xvch-5gv4-984h" },
  { kind:"scan",  t:"node[02] reachability", sub:"src/cli/serve.ts → minimist(argv)" },
  { kind:"scan",  t:"node[03] evidence", sub:"§ Details · prototype pollution · setKey()" },
  { kind:"hit",   t:"VERDICT", sub:"EXPOSED · 88% · $0.21 · 51s", v:"exposed" },
  { kind:"sep" },

  { kind:"scan",  t:"node[01] triage", sub:"path-parse@<1.0.7 · GHSA-9wv6-86v2-598j" },
  { kind:"clear", t:"killed at triage", sub:"devDependency only · no runtime path" },
  { kind:"hit",   t:"VERDICT", sub:"NOT REACHABLE · 97% · $0.09 · 22s", v:"safe" },
  { kind:"sep" },

  { kind:"scan",  t:"node[01] triage", sub:"express@<4.19.2 · GHSA-rv95-896h-c2vc" },
  { kind:"scan",  t:"node[02] reachability", sub:"4 call sites · routes/auth.ts:42" },
  { kind:"scan",  t:"node[03] evidence", sub:"open redirect via req.query.next" },
  { kind:"hit",   t:"VERDICT", sub:"EXPOSED · 81% · $0.24 · 62s", v:"exposed" },
  { kind:"sep" },

  { kind:"scan",  t:"node[01] triage", sub:"semver@>=7.0.0 <7.5.2 · GHSA-c2qf-rxjj-qqgw" },
  { kind:"scan",  t:"node[02] reachability", sub:"reaches version-check.ts · input constrained" },
  { kind:"hit",   t:"VERDICT", sub:"UNSURE · 58% · $0.18 · 47s · → human review", v:"unsure" },
];

// Hook: drives a windowed view that advances every N ms.
function useScanFeed(events, periodMs = 700) {
  const [head, setHead] = useState(2);          // how many events to render
  const [tick, setTick]   = useState(0);          // re-render cadence (clock)
  const total = events.length;

  useEffect(() => {
    let id = setInterval(() => {
      setHead(h => {
        // when we hit the end, loop back to 2 events shown
        if (h >= total) return 2;
        return h + 1;
      });
    }, periodMs);
    return () => clearInterval(id);
  }, [total, periodMs]);

  useEffect(() => {
    let raf;
    const loop = () => { setTick(t => t + 1); raf = requestAnimationFrame(loop); };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, []);

  // visible window: last ~8 events
  const WIN = 9;
  const visibleStart = Math.max(0, head - WIN);
  const visible = events.slice(visibleStart, head);
  return { visible, head, total, tick };
}

// Tally of verdicts found so far in the feed.
function useScanTally(events, head) {
  return useMemo(() => {
    const t = { exposed:0, safe:0, unsure:0 };
    for (let i = 0; i < head && i < events.length; i++) {
      const e = events[i];
      if (e.kind === "hit" && e.v) t[e.v] = (t[e.v]||0) + 1;
    }
    return t;
  }, [events, head]);
}

function ScanConsole() {
  const { visible, head, total } = useScanFeed(SCAN_EVENTS, 720);
  const tally = useScanTally(SCAN_EVENTS, head);
  const progressPct = Math.min(100, Math.round((head / total) * 100));

  return (
    <div style={{
      position:"relative",
      background:"var(--surface)",
      border:"1px solid var(--border)",
      borderRadius:"var(--r-xl)",
      overflow:"hidden",
      fontFamily:"var(--font-mono)",
      fontSize: 12.5,
      color:"var(--text-2)",
      boxShadow:"0 40px 100px -40px rgba(0,0,0,0.7), 0 0 0 1px rgba(249,115,22,0.04)",
    }}>
      <ScanHeader />
      <ScanProgressBar pct={progressPct} />
      <div style={{
        position:"relative",
        padding:"14px 18px 16px",
        minHeight: 310, maxHeight: 310, overflow:"hidden",
        background:"var(--bg-deep)",
        backgroundImage:"repeating-linear-gradient(0deg, rgba(255,255,255,0.012) 0 1px, transparent 1px 3px)",
      }}>
        <ScanStream visible={visible} />
      </div>
      <ScanFooter tally={tally} head={head} total={total} />
    </div>
  );
}

function ScanHeader() {
  return (
    <div style={{
      display:"flex", alignItems:"center", justifyContent:"space-between",
      padding:"11px 16px", borderBottom:"1px solid var(--border)",
      background:"var(--surface-2)",
    }}>
      <div style={{display:"flex", alignItems:"center", gap:12, color:"var(--text-3)", fontSize:11, whiteSpace:"nowrap", overflow:"hidden"}}>
        <span style={{display:"inline-flex", gap:5, flex:"0 0 auto"}}>
          <span style={{width:9,height:9,borderRadius:"50%",background:"#3a4356"}}/>
          <span style={{width:9,height:9,borderRadius:"50%",background:"#3a4356"}}/>
          <span style={{width:9,height:9,borderRadius:"50%",background:"#3a4356"}}/>
        </span>
        <span style={{letterSpacing:"0.04em", overflow:"hidden", textOverflow:"ellipsis"}}>notsudo · scan @ acme/payments-api</span>
      </div>
      <div style={{display:"flex", alignItems:"center", gap:8, fontSize:10, color:"var(--text-muted)"}}>
        <span style={{
          width:7, height:7, borderRadius:"50%",
          background:"var(--primary)",
          boxShadow:"0 0 10px var(--primary)",
          animation:"pulse-dot 1.4s ease-in-out infinite",
        }}/>
        <span style={{textTransform:"uppercase", letterSpacing:"0.14em"}}>scanning</span>
      </div>
    </div>
  );
}

function ScanProgressBar({ pct }) {
  return (
    <div style={{
      position:"relative", height: 2, background:"var(--border)",
      overflow:"hidden",
    }}>
      <div style={{
        position:"absolute", inset:"0 auto 0 0",
        width: `${pct}%`, background:"var(--primary)",
        boxShadow:"0 0 8px var(--primary)",
        transition:"width 320ms cubic-bezier(.4,0,.2,1)",
      }}/>
    </div>
  );
}

function ScanBeam() {
  return (
    <div aria-hidden="true" style={{
      position:"absolute", left:0, right:0, top:0, bottom:0,
      pointerEvents:"none",
      background:"linear-gradient(180deg, transparent 0%, rgba(249,115,22,0.10) 50%, transparent 100%)",
      backgroundSize:"100% 80px",
      animation:"scan-beam 2.8s linear infinite",
      mixBlendMode:"screen",
    }}/>
  );
}

function ScanStream({ visible }) {
  return (
    <div style={{display:"flex", flexDirection:"column", gap: 6, position:"relative"}}>
      {visible.map((e, i) => (
        <ScanLine key={`${e.kind}-${e.t}-${i}`} e={e} isLast={i === visible.length - 1} />
      ))}
    </div>
  );
}

function ScanLine({ e, isLast }) {
  if (e.kind === "sep") {
    return (
      <div style={{
        fontFamily:"var(--font-mono)", fontSize: 10,
        color:"var(--text-faint)", padding:"2px 0", lineHeight: 1,
      }}>
        {"────────────────────────────────────────────────"}
      </div>
    );
  }
  const marker =
    e.kind === "info"  ? <span style={{color:"var(--text-muted)"}}>›</span> :
    e.kind === "scan"  ? <span style={{color:"var(--primary)"}}>▸</span>     :
    e.kind === "clear" ? <span style={{color:"var(--safe-2)"}}>○</span>      :
    e.kind === "hit"   ? <span style={{color:"var(--primary)"}}>■</span>     : null;

  const titleColor =
    e.kind === "info"  ? "var(--text-3)"  :
    e.kind === "hit"   ? "var(--text)"    :
                         "var(--text-2)";

  const subColor = e.kind === "hit"
    ? (e.v === "exposed" ? "var(--danger-2)" :
       e.v === "safe"    ? "var(--safe-2)"   : "var(--warn-2)")
    : "var(--text-muted)";

  return (
    <div style={{
      display:"flex", alignItems:"flex-start", gap: 10,
      lineHeight: 1.45, minHeight: 18,
      opacity: isLast ? 1 : 0.92,
    }}>
      <span style={{flex:"0 0 12px", fontSize:11, lineHeight:1.6}}>{marker}</span>
      <span style={{flex:"1 1 auto", display:"block"}}>
        <span style={{color: titleColor, letterSpacing:"-0.005em", marginRight: 12}}>
          {e.t}{isLast && e.kind !== "hit" ? <span className="caret"/> : null}
        </span>
        {e.sub && (
          <span style={{color: subColor, fontSize: 11.5}}>{e.sub}</span>
        )}
      </span>
    </div>
  );
}

function ScanFooter({ tally, head, total }) {
  return (
    <div style={{
      padding:"12px 16px",
      borderTop:"1px solid var(--border)",
      display:"flex", alignItems:"center", justifyContent:"space-between", gap:14,
      background:"var(--surface)", flexWrap:"wrap",
    }}>
      <div style={{display:"flex", alignItems:"center", gap:14, flexWrap:"wrap"}}>
        <Tally n={tally.exposed} label="EXPOSED" tone="exposed" />
        <Tally n={tally.safe}    label="NOT REACHABLE" tone="safe" />
        <Tally n={tally.unsure}  label="UNSURE" tone="unsure" />
      </div>
      <div style={{display:"flex", alignItems:"center", gap:10, fontFamily:"var(--font-mono)", fontSize:11, color:"var(--text-muted)"}}>
        <span>events {String(head).padStart(2,"0")}/{String(total).padStart(2,"0")}</span>
        <span style={{color:"var(--text-faint)"}}>·</span>
        <span style={{color:"var(--primary-2)"}}>looping</span>
      </div>
    </div>
  );
}

function Tally({ n, label, tone }) {
  const c =
    tone === "exposed" ? "var(--danger-2)" :
    tone === "safe"    ? "var(--safe-2)"   :
                         "var(--warn-2)";
  return (
    <span style={{display:"inline-flex", alignItems:"baseline", gap:8, whiteSpace:"nowrap"}}>
      <span style={{
        fontFamily:"var(--font-mono)", fontSize: 18, fontWeight: 600,
        color: c, letterSpacing:"-0.02em",
      }}>{String(n).padStart(2,"0")}</span>
      <span style={{
        fontFamily:"var(--font-mono)", fontSize: 10, color:"var(--text-muted)",
        letterSpacing:"0.1em", textTransform:"uppercase",
      }}>{label}</span>
    </span>
  );
}

Object.assign(window, { ScanConsole, SCAN_EVENTS });
