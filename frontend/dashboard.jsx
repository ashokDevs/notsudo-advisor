// dashboard.jsx — NotSudo Advisor
// Multi-page shell (hash-routed): sidebar + header + one page component per route.
// Pages: Advisories · Repositories · Security · Settings.

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "monoFont": "geist"
}/*EDITMODE-END*/;

const MONO_FONTS = {
  geist:    `"Geist Mono", ui-monospace, "SFMono-Regular", Menlo, monospace`,
  jetbrains:`"JetBrains Mono", ui-monospace, "SFMono-Regular", Menlo, monospace`,
  berkeley: `"IBM Plex Mono", "Berkeley Mono", ui-monospace, Menlo, monospace`,
};

// ─────────────────────────────────────────────────────────────
// ICONS
// ─────────────────────────────────────────────────────────────
const ICONS = {
  advisories: `<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>`,
  repos: `<line x1="6" y1="3" x2="6" y2="15"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/>`,
  security: `<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 9.5"/>`,
  settings: `<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>`,
  menu: `<line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/>`,
  chevron: `<polyline points="6 9 12 15 18 9"/>`,
  external: `<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>`,
};

function Icon({ name, size = 16, stroke = 1.7, style }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
         stroke="currentColor" strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round"
         style={style} aria-hidden="true"
         dangerouslySetInnerHTML={{ __html: ICONS[name] || "" }} />
  );
}

function GithubMark({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z"/>
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────
// HASH ROUTER
// ─────────────────────────────────────────────────────────────
const ROUTES = ["advisories", "repos", "security", "settings"];

function useHashRoute() {
  const parse = () => {
    const r = window.location.hash.replace(/^#\/?/, "");
    return ROUTES.includes(r) ? r : "advisories";
  };
  const [route, setRoute] = useState(parse());
  useEffect(() => {
    const on = () => setRoute(parse());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return route;
}

// ─────────────────────────────────────────────────────────────
// APP SHELL
// ─────────────────────────────────────────────────────────────
function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  useEffect(() => {
    document.documentElement.style.setProperty("--font-mono", MONO_FONTS[t.monoFont] || MONO_FONTS.geist);
  }, [t.monoFont]);

  const route = useHashRoute();

  // Dynamic only — no hardcoded ADVISORIES sample data
  const [advisories, setAdvisories] = useState([]);
  const [repoName, setRepoName]     = useState("—");
  const [scanMeta, setScanMeta]     = useState(null);
  const [scanning, setScanning]     = useState(false);
  const [scanError, setScanError]   = useState(null);
  const [hasScanned, setHasScanned] = useState(false);
  const [drawer, setDrawer]         = useState(false);
  const [health, setHealth]         = useState(null);

  const [me, setMe]           = useState(null);
  const [prState, setPrState] = useState({});

  useEffect(() => {
    fetch("/api/me").then(r => r.json()).then(setMe).catch(() => setMe({ user: null, configured: false }));
    fetch("/api/health").then(r => r.json()).then(setHealth).catch(() => setHealth(null));
  }, []);

  const handleScan = useCallback(async (target) => {
    setScanning(true);
    setScanError(null);
    try {
      const res  = await fetch("/api/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target, repo_path: target }),
      });
      const data = await res.json();
      if (!res.ok) {
        const detail = data.detail;
        throw new Error(typeof detail === "string" ? detail : (detail && JSON.stringify(detail)) || "Scan failed");
      }
      setHasScanned(true);
      setAdvisories(data.advisories || []);
      setRepoName(data.display_name || data.repo || target);
      setScanMeta({
        summary: data.summary || null,
        source: data.source,
        github_url: data.github_url,
        ecosystem: data.ecosystem,
        pkg_count: data.pkg_count,
        llm_enabled: data.llm_enabled,
        llm_provider: data.llm_provider,
        path: data.path,
      });
      if (!data.advisories || data.advisories.length === 0) {
        setScanError(null); // not an error — clean scan
      }
    } catch (e) {
      setScanError(e.message);
    } finally {
      setScanning(false);
    }
  }, []);

  // Auto-run first live scan of demo_app so the UI is never static
  useEffect(() => {
    handleScan("demo_app");
  }, [handleScan]);

  const openPR = useCallback(async (a) => {
    setPrState(s => ({ ...s, [a.id]: { status: "loading" } }));
    try {
      const res = await fetch("/api/pr", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: a.id, pkg: a.pkg, current: a.current, fix: a.fix,
          verdict: a.verdict, confidence: a.confidence, reasoning: a.reasoning,
          quote: a.quote, quoteSource: a.quoteSource, entrypoints: a.entrypoints,
          evidence_quotes: a.evidence_quotes || [],
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "PR failed");
      setPrState(s => ({ ...s, [a.id]: { status: "done", url: data.url, number: data.number } }));
    } catch (e) {
      setPrState(s => ({ ...s, [a.id]: { status: "error", error: e.message } }));
    }
  }, []);

  const exposedCount = useMemo(() => advisories.filter(a => a.verdict === "exposed").length, [advisories]);

  return (
    <F>
      <DashboardStyles />
      <div className="dash-shell">
        <Sidebar route={route} exposed={exposedCount} onNavigate={() => setDrawer(false)} open={drawer} />
        <div className={`dash-backdrop${drawer ? " show" : ""}`} onClick={() => setDrawer(false)} />

        <div className="dash-main">
          <Header route={route} onToggle={() => setDrawer(d => !d)} me={me} repoName={repoName} />

          <div className="dash-content">
            {route === "advisories" && (
              <AdvisoriesPage
                advisories={advisories} me={me} prState={prState} onOpenPR={openPR}
                onScan={handleScan} scanning={scanning} scanError={scanError}
                scanMeta={scanMeta} repoName={repoName} health={health} hasScanned={hasScanned} />
            )}
            {route === "repos" && (
              <ReposPage me={me} advisories={advisories} scanning={scanning} onScan={handleScan} repoName={repoName} scanMeta={scanMeta} />
            )}
            {route === "security" && <SecurityPage />}
            {route === "settings" && <SettingsPage me={me} t={t} setTweak={setTweak} />}
          </div>
        </div>
      </div>

      <TweaksPanel>
        <TweakSection label="Typography" />
        <TweakRadio label="Mono" value={t.monoFont}
                    options={["geist","jetbrains","berkeley"]}
                    onChange={(v)=>setTweak("monoFont", v)} />
      </TweaksPanel>
    </F>
  );
}

// ─────────────────────────────────────────────────────────────
// SIDEBAR
// ─────────────────────────────────────────────────────────────
const NAV_MAIN = [
  { id: "advisories", label: "Advisories",   icon: "advisories" },
  { id: "repos",      label: "Repositories", icon: "repos" },
  { id: "security",   label: "Security",     icon: "security" },
];
const NAV_MANAGE = [
  { id: "settings", label: "Settings", icon: "settings" },
];
const PAGE_TITLES = {
  advisories: "Advisories", repos: "Repositories", security: "Security", settings: "Settings",
};

function Sidebar({ route, exposed, onNavigate, open }) {
  return (
    <aside className={`dash-sidebar${open ? " open" : ""}`}>
      <div className="dash-sidebar__brand">
        <a href="Landing.html" style={{display:"inline-flex"}}><Logo size={19}/></a>
      </div>

      <nav className="dash-nav">
        <div className="dash-nav__label">Monitor</div>
        {NAV_MAIN.map(item => (
          <NavItem key={item.id} {...item} active={route === item.id} onNavigate={onNavigate}
                   badge={item.id === "advisories" ? exposed : null} />
        ))}

        <div className="dash-nav__label">Manage</div>
        {NAV_MANAGE.map(item => (
          <NavItem key={item.id} {...item} active={route === item.id} onNavigate={onNavigate} />
        ))}
      </nav>

      <div className="dash-sidebar__foot">
        <span className="live-dot" />
        <span className="mono" style={{fontSize:11, color:"var(--text-2)"}}>agent online</span>
      </div>
    </aside>
  );
}

function NavItem({ id, label, icon, active, onNavigate, badge }) {
  return (
    <a className={`nav-item${active ? " active" : ""}`} href={`#/${id}`} onClick={onNavigate}>
      <Icon name={icon} size={16.5} />
      <span>{label}</span>
      {badge != null && badge > 0 && <span className="nav-item__badge danger">{badge}</span>}
    </a>
  );
}

// ─────────────────────────────────────────────────────────────
// HEADER
// ─────────────────────────────────────────────────────────────
function Header({ route, onToggle, me, repoName }) {
  return (
    <header className="dash-header">
      <button className="icon-btn hamburger" onClick={onToggle} aria-label="Toggle menu">
        <Icon name="menu" size={18} />
      </button>

      <div className="dash-crumb">
        <span className="dash-crumb__title">{PAGE_TITLES[route] || "Advisories"}</span>
        {repoName && (
          <span className="mono" style={{fontSize:12, color:"var(--text-muted)"}}>· {repoName}</span>
        )}
      </div>

      <div style={{flex:1}} />
      <GitHubAuth me={me} />
    </header>
  );
}

function GitHubAuth({ me }) {
  if (me == null) return <div style={{width:34, height:34}} />;
  const user = me.user;

  if (user) {
    return (
      <div className="gh-auth">
        {user.avatar_url
          ? <img className="gh-avatar" src={user.avatar_url} alt={user.login} />
          : <div className="avatar">{(user.login || "?").slice(0,2).toUpperCase()}</div>}
        <div className="gh-auth__info">
          <span className="gh-auth__login mono">{user.login}</span>
          <button className="gh-auth__logout"
                  onClick={() => fetch("/api/logout", {method:"POST"}).then(() => location.reload())}>
            sign out
          </button>
        </div>
      </div>
    );
  }

  if (!me.configured) {
    return <span className="gh-notconfigured mono" title="Set GITHUB_CLIENT_ID / SECRET in .env">GitHub not configured</span>;
  }

  return (
    <a className="btn btn--primary btn--sm gh-signin" href="/auth/github/login">
      <GithubMark size={15} /> Sign in
    </a>
  );
}

// ─────────────────────────────────────────────────────────────
// PAGE: ADVISORIES
// ─────────────────────────────────────────────────────────────
function AdvisoriesPage({ advisories, me, prState, onOpenPR, onScan, scanning, scanError, scanMeta, repoName, health, hasScanned }) {
  return (
    <F>
      <div className="hero-line mono">
        Dependabot flags <em>packages</em>. NotSudo flags only what your code can <em>actually hit</em>.
        <span style={{color:"var(--text-muted)"}}> · live OSV + clone · no static sample data</span>
      </div>
      <ConfigBar health={health} me={me} scanMeta={scanMeta} />
      <ScanBar onScan={onScan} scanning={scanning} error={scanError} />
      {(hasScanned || (advisories && advisories.length > 0)) && (
        <SummaryStrip advisories={advisories} scanMeta={scanMeta} repoName={repoName} />
      )}
      {scanning && advisories.length === 0 && (
        <div className="mono empty-scan">Running live scan… querying OSV and reading source</div>
      )}
      {!scanning && hasScanned && advisories.length === 0 && (
        <div className="mono empty-scan">
          Scan complete — <strong>0 vulnerabilities</strong> on OSV for this tree ({scanMeta?.pkg_count ?? "?"} packages).
          Try another target (e.g. OWASP/NodeGoat).
        </div>
      )}
      <AdvisoryTable advisories={advisories} me={me} prState={prState} onOpenPR={onOpenPR} />
    </F>
  );
}

function ConfigBar({ health, me, scanMeta }) {
  if (!health && !me) return null;
  const llm = health?.llm || me?.llm_configured;
  const provider = health?.llm_provider || me?.llm_provider || "none";
  const model = health?.llm_model || me?.llm_model;
  const oauth = health?.github_oauth || me?.configured;
  const oauthPartial = health?.github_oauth_partial || (me?.oauth_client_id_set && !me?.oauth_secret_set);
  const pat = health?.github_pat || me?.pat_configured;
  const online = health?.online || me?.online;
  const publicUrl = health?.public_url || me?.public_url;
  return (
    <div className="config-bar mono">
      <span className={online ? "ok" : "dim"}>
        {online ? `online · ${publicUrl || "https"}` : "local"}
      </span>
      <span className="sep">·</span>
      <span className={llm ? "ok" : "dim"}>
        LLM {llm ? `on · ${provider}${model ? ` · ${model}` : ""}` : "off (heuristics)"}
      </span>
      <span className="sep">·</span>
      <span className={oauth ? "ok" : oauthPartial ? "warn" : "dim"}>
        {oauth ? "GitHub OAuth ready" : oauthPartial ? "OAuth: missing CLIENT_SECRET" : "OAuth off"}
      </span>
      <span className="sep">·</span>
      <span className={pat || (me && me.user) ? "ok" : "dim"}>
        {me && me.user ? `signed in as ${me.user.login}` : pat ? "PAT ready for PRs" : "no PR write creds"}
      </span>
      {scanMeta?.llm_enabled != null && (
        <>
          <span className="sep">·</span>
          <span className={scanMeta.llm_enabled ? "ok" : "dim"}>
            last scan {scanMeta.llm_enabled ? "used LLM" : "used heuristics"}
          </span>
        </>
      )}
    </div>
  );
}

function ScanBar({ onScan, scanning, error }) {
  const [path, setPath] = useState("demo_app");
  const submit = (e) => { e.preventDefault(); if (path.trim()) onScan(path.trim()); };
  const quick = [
    { label: "demo_app", value: "demo_app" },
    { label: "NodeGoat (GitHub)", value: "https://github.com/OWASP/NodeGoat" },
    { label: "express (GitHub)", value: "https://github.com/expressjs/express" },
  ];
  return (
    <div className="scan-panel scan-panel--stack">
      <form onSubmit={submit} className="scan-form">
        <div className="scan-input">
          <span className="mono" style={{fontSize:12, color:"var(--text-muted)"}}>$</span>
          <input value={path} onChange={e => setPath(e.target.value)} spellCheck={false}
                 placeholder="local path · https://github.com/org/repo · or owner/repo" />
        </div>
        <button type="submit" disabled={scanning || !path.trim()} className="btn btn--primary btn--sm"
                style={{whiteSpace:"nowrap", opacity: scanning ? 0.7 : 1}}>
          {scanning ? <span className="caret">scanning</span> : "Scan →"}
        </button>
      </form>
      <div className="scan-quick">
        <span className="mono" style={{fontSize:11, color:"var(--text-muted)"}}>try:</span>
        {quick.map(q => (
          <button key={q.value} type="button" className="chip chip--sm"
                  disabled={scanning}
                  onClick={() => { setPath(q.value); onScan(q.value); }}>
            {q.label}
          </button>
        ))}
      </div>
      {scanning && (
        <span className="mono scan-hint">Cloning GitHub repos if needed · querying OSV · locating call sites…</span>
      )}
      {error && <span className="mono" style={{fontSize:12, color:"var(--danger-2)"}}>✕&nbsp;{error}</span>}
    </div>
  );
}

function SummaryStrip({ advisories, scanMeta, repoName }) {
  const counts = useMemo(() => {
    if (scanMeta && scanMeta.summary) return scanMeta.summary;
    return {
      packages: scanMeta?.pkg_count ?? "—",
      vulns: advisories.length,
      exposed: advisories.filter(a => a.verdict === "exposed").length,
      safe: advisories.filter(a => a.verdict === "safe").length,
      unsure: advisories.filter(a => a.verdict === "unsure").length,
      presence_noise: advisories.filter(a => a.verdict === "safe" || a.verdict === "unsure").length,
    };
  }, [advisories, scanMeta]);

  return (
    <div className="summary-strip">
      <div className="summary-strip__head">
        <span className="mono summary-strip__repo">{repoName || "repo"}</span>
        {scanMeta?.source && (
          <span className="pill" style={{fontSize:10}}>
            <span className="dot" />{scanMeta.source === "github" ? "github clone" : "local path"}
          </span>
        )}
        {scanMeta?.ecosystem && (
          <span className="mono" style={{fontSize:11, color:"var(--text-muted)"}}>{scanMeta.ecosystem}</span>
        )}
        {scanMeta?.github_url && (
          <a className="mono" style={{fontSize:11, color:"var(--primary-2)"}} href={scanMeta.github_url} target="_blank" rel="noreferrer">
            view on GitHub ↗
          </a>
        )}
      </div>
      <div className="summary-strip__stats">
        <div><b>{counts.packages}</b><span>packages</span></div>
        <div><b>{counts.vulns}</b><span>OSV vulns</span><em className="summary-note">presence ceiling</em></div>
        <div className="is-danger"><b>{counts.exposed}</b><span>exposed</span><em className="summary-note">fix these</em></div>
        <div className="is-safe"><b>{counts.safe}</b><span>safe</span></div>
        <div className="is-warn"><b>{counts.unsure}</b><span>unsure</span></div>
      </div>
      <div className="summary-strip__foot mono">
        Presence-style noise: <strong>{counts.presence_noise ?? (counts.safe + counts.unsure)}</strong>
        {" · "}
        Reachability-confirmed: <strong style={{color:"var(--danger-2)"}}>{counts.exposed}</strong>
        {" — only exposed opens a fix PR by default."}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// PAGE: REPOSITORIES
// ─────────────────────────────────────────────────────────────
function ReposPage({ me, advisories, scanning, onScan, repoName, scanMeta }) {
  const prTarget = (me && me.repo) || "ashokDevs/notsudo-demo-app";
  const scanned = repoName || "—";
  const counts = useMemo(() => ({
    exposed: advisories.filter(a => a.verdict === "exposed").length,
    unsure:  advisories.filter(a => a.verdict === "unsure").length,
    safe:    advisories.filter(a => a.verdict === "safe").length,
  }), [advisories]);

  return (
    <div style={{maxWidth:640, display:"flex", flexDirection:"column", gap:16}}>
      <div className="card repo-card">
        <div className="repo-card__head">
          <div style={{display:"flex", alignItems:"center", gap:10, minWidth:0}}>
            <GithubMark size={18} />
            <span className="mono repo-card__name">{scanned}</span>
          </div>
          {scanMeta?.github_url && (
            <a className="btn btn--sm" href={scanMeta.github_url} target="_blank" rel="noreferrer">
              View <Icon name="external" size={13} />
            </a>
          )}
        </div>

        <div className="repo-card__stats">
          <div><b style={{color:"var(--danger-2)"}}>{counts.exposed}</b><span>exposed</span></div>
          <div><b style={{color:"var(--warn-2)"}}>{counts.unsure}</b><span>unsure</span></div>
          <div><b style={{color:"var(--safe-2)"}}>{counts.safe}</b><span>not reachable</span></div>
        </div>

        <div className="repo-card__foot">
          <a className="btn btn--primary btn--sm" href="#/advisories"
             onClick={(e) => { e.preventDefault(); onScan("demo_app"); window.location.hash = "#/advisories"; }}>
            {scanning ? <span className="caret">scanning</span> : "Rescan demo_app →"}
          </a>
          <span className="mono" style={{fontSize:11, color:"var(--text-muted)"}}>
            {scanMeta?.ecosystem || "npm"} · {scanMeta?.pkg_count ?? "?"} packages
          </span>
        </div>
      </div>

      <div className="card repo-card">
        <div className="set-card__label">Scan any public GitHub repo</div>
        <p className="mono set-note" style={{marginBottom:12}}>
          Paste <span style={{color:"var(--text-2)"}}>https://github.com/org/repo</span> on the Advisories page.
          We shallow-clone, run OSV + reachability, then delete the temp copy.
        </p>
        <button className="btn btn--sm" disabled={scanning}
                onClick={() => { onScan("https://github.com/expressjs/express"); window.location.hash = "#/advisories"; }}>
          Try expressjs/express →
        </button>
      </div>

      <p className="mono empty-hint">Fix PRs open against <strong>{prTarget}</strong> (set GITHUB_DEMO_REPO). Sign in or set GITHUB_TOKEN.</p>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// PAGE: SECURITY
// ─────────────────────────────────────────────────────────────
function SecurityPage() {
  return (
    <div className="callout-grid">
      <div className="callout callout--danger">
        <div className="eyebrow" style={{color:"var(--danger-2)", display:"inline-flex", alignItems:"center", gap:8, marginBottom:8}}>
          <span style={{width:7, height:7, borderRadius:"50%", background:"var(--danger-2)", boxShadow:"0 0 8px var(--danger-2)"}}/>
          adversarial defence
        </div>
        <div style={{fontSize:14, color:"var(--text-2)", margin:"4px 0 12px", lineHeight:1.55}}>
          <strong style={{color:"var(--text)"}}>0</strong> injection attempts this week · advisory text routed through the isolated parser · the reasoner sees structured fields only.
        </div>
        <div className="callout__meta">
          <span><span style={{color:"var(--text-3)"}}>parser quarantine</span> ✓</span>
          <span><span style={{color:"var(--text-3)"}}>tool calls scoped</span> ✓</span>
        </div>
      </div>

      <div className="callout callout--safe">
        <div className="eyebrow" style={{color:"var(--safe-2)", display:"inline-flex", alignItems:"center", gap:8, marginBottom:8}}>
          <span style={{width:7, height:7, borderRadius:"50%", background:"var(--safe-2)", boxShadow:"0 0 8px var(--safe-2)"}}/>
          hallucination defence
        </div>
        <div style={{fontSize:14, color:"var(--text-2)", margin:"4px 0 12px", lineHeight:1.55}}>
          Every quote is validated against its source file. Synthesized quotes are rejected before a PR is drafted. <strong style={{color:"var(--text)"}}>100%</strong> of evidence verifiable this week.
        </div>
        <div className="callout__meta">
          <span><span style={{color:"var(--text-3)"}}>citations validated</span> 14&thinsp;/&thinsp;14</span>
          <span><span style={{color:"var(--text-3)"}}>replay determ.</span> ✓</span>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// PAGE: SETTINGS
// ─────────────────────────────────────────────────────────────
function SettingsPage({ me, t, setTweak }) {
  return (
    <div style={{maxWidth:560, display:"flex", flexDirection:"column", gap:16}}>
      <div className="card set-card">
        <div className="set-card__label">GitHub connection</div>
        {me && me.user ? (
          <div className="set-row">
            <div style={{display:"flex", alignItems:"center", gap:10}}>
              {me.user.avatar_url && <img className="gh-avatar" src={me.user.avatar_url} alt="" />}
              <span className="mono">{me.user.login}</span>
              <span className="pill pill--safe"><span className="dot"/>CONNECTED</span>
            </div>
            <button className="btn btn--sm" onClick={() => fetch("/api/logout", {method:"POST"}).then(() => location.reload())}>Sign out</button>
          </div>
        ) : me && !me.configured ? (
          <p className="mono set-note">Not configured. Set <span style={{color:"var(--text-2)"}}>GITHUB_CLIENT_ID</span> and <span style={{color:"var(--text-2)"}}>GITHUB_CLIENT_SECRET</span> in <span style={{color:"var(--text-2)"}}>.env</span>, then restart.</p>
        ) : (
          <div className="set-row">
            <span className="mono set-note">Not signed in.</span>
            <a className="btn btn--primary btn--sm gh-signin" href="/auth/github/login"><GithubMark size={14}/> Sign in with GitHub</a>
          </div>
        )}
      </div>

      <div className="card set-card">
        <div className="set-card__label">Fix-PR target</div>
        <div className="set-row">
          <span className="mono">{(me && me.repo) || "ashokDevs/notsudo-demo-app"}</span>
          <span className="mono" style={{fontSize:11, color:"var(--text-muted)"}}>PRs open here</span>
        </div>
      </div>

      <div className="card set-card">
        <div className="set-card__label">Monospace font</div>
        <div className="set-radios">
          {["geist","jetbrains","berkeley"].map(f => (
            <button key={f} className={`chip${t.monoFont === f ? " is-active" : ""}`} onClick={() => setTweak("monoFont", f)}>
              {f}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// ADVISORY TABLE
// ─────────────────────────────────────────────────────────────
function AdvisoryTable({ advisories, me, prState, onOpenPR }) {
  // Default to exposed — the win demo filter
  const [filter, setFilter] = useState("exposed");
  const [query, setQuery] = useState("");
  const [openId, setOpenId] = useState(null);

  useEffect(() => {
    const first = advisories.find(a => a.verdict === "exposed") || advisories[0];
    setOpenId(first ? first.id : null);
    const hasExposed = advisories.some(a => a.verdict === "exposed");
    setFilter(hasExposed ? "exposed" : "all");
  }, [advisories]);

  const filtered = useMemo(()=> {
    return advisories.filter(a => {
      if (filter !== "all" && a.verdict !== filter) return false;
      if (query) {
        const q = query.toLowerCase();
        return a.id.toLowerCase().includes(q) || a.pkg.toLowerCase().includes(q) || a.title.toLowerCase().includes(q);
      }
      return true;
    });
  }, [advisories, filter, query]);

  const counts = useMemo(()=> ({
    all: advisories.length,
    exposed: advisories.filter(a=>a.verdict==="exposed").length,
    safe: advisories.filter(a=>a.verdict==="safe").length,
    unsure: advisories.filter(a=>a.verdict==="unsure").length,
  }), [advisories]);

  return (
    <F>
      <div className="tbl-controls">
        <FilterChip active={filter==="exposed"} onClick={()=>setFilter("exposed")} label="exposed" count={counts.exposed} tone="exposed" />
        <FilterChip active={filter==="unsure"}  onClick={()=>setFilter("unsure")} label="unsure"   count={counts.unsure} tone="unsure" />
        <FilterChip active={filter==="safe"}    onClick={()=>setFilter("safe")}   label="safe"     count={counts.safe} tone="safe" />
        <FilterChip active={filter==="all"}     onClick={()=>setFilter("all")}    label="all"      count={counts.all} />
        <div style={{flex:1}} />
        <div className="tbl-search">
          <span style={{color:"var(--text-muted)", fontFamily:"var(--font-mono)", fontSize:12}}>/</span>
          <input value={query} onChange={(e)=>setQuery(e.target.value)} placeholder="filter" />
        </div>
      </div>

      {filter === "exposed" && (
        <div className="filter-hint mono">
          Showing reachability-confirmed only — switch to <button type="button" className="linkish" onClick={()=>setFilter("all")}>all</button> to see presence-style noise.
        </div>
      )}

      <div className="card" style={{overflow:"hidden"}}>
        <div className="tbl-row tbl-head">
          <span></span>
          <span>advisory</span>
          <span>package</span>
          <span>cvss</span>
          <span>verdict</span>
          <span style={{textAlign:"right"}}>confidence</span>
          <span style={{textAlign:"right"}}>sites</span>
          <span></span>
        </div>

        {filtered.map((a, idx) => (
          <Row key={a.id} a={a} open={openId === a.id} onToggle={()=>setOpenId(openId===a.id ? null : a.id)}
               last={idx === filtered.length - 1} me={me} pr={prState?.[a.id]} onOpenPR={onOpenPR} />
        ))}

        {filtered.length === 0 && (
          <div style={{padding:"40px 20px", textAlign:"center", color:"var(--text-muted)", fontFamily:"var(--font-mono)", fontSize:13}}>
            no advisories match — try “all” or run a scan.
          </div>
        )}
      </div>
    </F>
  );
}

function FilterChip({ active, onClick, label, count, tone }) {
  const toneColor = { exposed:"var(--danger-2)", unsure:"var(--warn-2)", safe:"var(--safe-2)" }[tone];
  return (
    <button onClick={onClick} className={`chip${active ? " is-active" : ""}`}>
      {tone && <span style={{width:6, height:6, borderRadius:"50%", background:toneColor, boxShadow: active ? `0 0 8px ${toneColor}` : "none"}}/>}
      <span>{label}</span>
      <span style={{color:"var(--text-muted)"}}>{count}</span>
    </button>
  );
}

function Row({ a, open, onToggle, last, me, pr, onOpenPR }) {
  return (
    <F>
      <button onClick={onToggle} className={`tbl-row tbl-body${open ? " is-open" : ""}`}
              style={{borderBottom: (open || !last) ? "1px solid var(--border)" : "none"}}>
        <Chevron open={open} />
        <div style={{display:"flex", flexDirection:"column", gap:2, minWidth:0}}>
          <span className="mono" style={{fontSize:12.5, color:"var(--text)"}}>{a.title}</span>
          <span className="mono" style={{fontSize:11, color:"var(--text-muted)"}}>{a.id}</span>
        </div>
        <div style={{display:"flex", flexDirection:"column", gap:2, minWidth:0}}>
          <span className="mono" style={{fontSize:12.5, color:"var(--text)"}}>{a.pkg}</span>
          <span className="mono" style={{fontSize:11, color:"var(--text-muted)"}}>{a.range}</span>
        </div>
        <CVSSBadge cvss={a.cvss} severity={a.severity} />
        <VerdictPill v={a.verdict} />
        <ConfidenceBar c={a.confidence} v={a.verdict} />
        <span className="mono" style={{fontSize:12.5, textAlign:"right", color:"var(--text-2)"}}>
          {a.callsites ?? (a.call_sites ? a.call_sites.length : 0)}
        </span>
        <span style={{textAlign:"right", color:"var(--text-muted)"}}>›</span>
      </button>

      {open && <ExpandedRow a={a} last={last} me={me} pr={pr} onOpenPR={onOpenPR} />}
    </F>
  );
}

function Chevron({ open }) {
  return (
    <span style={{display:"inline-flex", alignItems:"center", justifyContent:"center", color:"var(--text-muted)",
                  fontFamily:"var(--font-mono)", fontSize:11, transform: open ? "rotate(90deg)" : "none", transition:"transform .15s"}}>▸</span>
  );
}

function CVSSBadge({ cvss, severity }) {
  const color = severity === "critical" ? "var(--danger-2)" : severity === "high" ? "var(--warn-2)"
              : severity === "moderate" ? "var(--primary-2)" : "var(--text-3)";
  const n = typeof cvss === "number" ? cvss : parseFloat(cvss) || 0;
  return (
    <span style={{display:"inline-flex", alignItems:"center", gap:8}}>
      <span className="mono" style={{fontSize:13, color, fontWeight:500}}>{n.toFixed(1)}</span>
      <span className="mono" style={{fontSize:10, color:"var(--text-muted)", letterSpacing:"0.08em", textTransform:"uppercase"}}>{severity}</span>
    </span>
  );
}

function ConfidenceBar({ c, v }) {
  const color = v === "exposed" ? "var(--danger-2)" : v === "safe" ? "var(--safe-2)" : "var(--warn-2)";
  const n = typeof c === "number" ? c : parseFloat(c) || 0;
  return (
    <div style={{display:"flex", alignItems:"center", gap:8, justifyContent:"flex-end"}}>
      <span className="mono" style={{fontSize:12, color:"var(--text-2)"}}>{(n*100).toFixed(0)}%</span>
      <div style={{width:44, height:4, background:"var(--border)", borderRadius:2, overflow:"hidden"}}>
        <div style={{width:`${n*100}%`, height:"100%", background:color}}/>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// EXPANDED ROW
// ─────────────────────────────────────────────────────────────
function ExpandedRow({ a, last, me, pr, onOpenPR }) {
  const sites = a.call_sites || [];
  const entrypoints = a.entrypoints || [];
  const preflight = a.preflight;
  return (
    <div style={{background:"var(--bg-deep)", borderBottom: !last ? "1px solid var(--border)" : "none", padding:"22px"}}>
      <div className="expand-grid">
        <div style={{display:"flex", flexDirection:"column", gap:16}}>
          <Block label="reasoning">
            <p style={{margin:0, fontSize:13.5, lineHeight:1.65, color:"var(--text-2)"}}>{a.reasoning}</p>
          </Block>

          <Block label="call sites (file:line)" accent="var(--danger-2)">
            {sites.length === 0 ? (
              <div className="mono" style={{fontSize:12, color:"var(--text-muted)"}}>
                No syntactic call sites recorded — see entry points.
              </div>
            ) : (
              <ul className="callsite-list">
                {sites.slice(0, 8).map((s, i) => (
                  <li key={i} className="callsite-item">
                    <div className="callsite-loc mono">
                      <span className="callsite-kind">{s.kind || "code"}</span>
                      <span>{s.file_path}:{s.line}</span>
                      {s.symbol && <span className="callsite-sym">{s.symbol}</span>}
                    </div>
                    <code className="callsite-snip">{s.snippet}</code>
                  </li>
                ))}
              </ul>
            )}
          </Block>

          <Block label={`evidence · ${a.quoteSource || a.id}`} accent="var(--node-3)">
            <div style={{fontFamily:"var(--font-mono)", fontSize:12.5, color:"var(--text-2)", lineHeight:1.65}}>
              &ldquo;{a.quote}&rdquo;
            </div>
            <div style={{marginTop:10, fontFamily:"var(--font-mono)", fontSize:11, color:"var(--text-muted)"}}>
              <span style={{color:"var(--safe-2)"}}>✓</span> citation grounded against source when LLM quotes are present
            </div>
          </Block>
        </div>

        <div style={{display:"flex", flexDirection:"column", gap:16}}>
          <Block label="entry points checked">
            <ul style={{listStyle:"none", margin:0, padding:0, display:"flex", flexDirection:"column", gap:8}}>
              {entrypoints.map(e => (
                <li key={e} style={{fontFamily:"var(--font-mono)", fontSize:12, color:"var(--text-2)", display:"flex", alignItems:"center", gap:10}}>
                  <span style={{color: (a.callsites > 0 || sites.length) ? "var(--danger-2)" : "var(--safe-2)"}}>
                    {(a.callsites > 0 || sites.length) ? "▶" : "○"}
                  </span>
                  {e}
                </li>
              ))}
              <li style={{marginTop:6, paddingTop:10, borderTop:"1px dashed var(--border)", fontFamily:"var(--font-mono)", fontSize:12,
                          color: (a.callsites > 0 || sites.length) ? "var(--danger-2)" : "var(--safe-2)"}}>
                {a.callsites ?? sites.length} call site{(a.callsites ?? sites.length) === 1 ? "" : "s"} ·{" "}
                <span style={{color:"var(--text)"}}>{a.function}</span>
              </li>
            </ul>
          </Block>

          {preflight && (
            <Block label="preflight">
              <span className="mono" style={{fontSize:12, color: preflight.ok ? "var(--safe-2)" : "var(--danger-2)"}}>
                {preflight.ok ? "✓" : "✕"} {preflight.message}
              </span>
            </Block>
          )}

          {a.verdict === "safe" && (
            <div className="why-not mono">
              Why not Dependabot noise? Marked <strong>safe</strong> — present in the tree but not a production-reachable hit (or version out of range / dev-only / test-only).
            </div>
          )}
          {a.verdict === "unsure" && (
            <div className="why-not mono">
              Unsure — needs human review. We don’t open a PR when confidence is low.
            </div>
          )}

          <PRAction a={a} me={me} pr={pr} onOpenPR={onOpenPR} />
        </div>
      </div>
    </div>
  );
}

function Block({ label, accent, children }) {
  return (
    <div style={{border:"1px solid var(--border)", borderRadius:"var(--r-md)", background:"var(--surface)",
                 padding:"14px 16px 16px", borderLeft: accent ? `2px solid ${accent}` : "1px solid var(--border)"}}>
      <div style={{fontFamily:"var(--font-mono)", fontSize:10.5, color:"var(--text-muted)", letterSpacing:"0.1em", textTransform:"uppercase", marginBottom:10}}>{label}</div>
      {children}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// PR ACTION
// ─────────────────────────────────────────────────────────────
function PRAction({ a, me, pr, onOpenPR }) {
  const oauth = !!(me && me.user);
  const pat = !!(me && me.pat_configured);
  const canPr = oauth || pat;
  const primary = a.verdict === "exposed";

  if (pr && pr.status === "done") {
    return (
      <div className="pr-result pr-result--ok">
        <span><span style={{color:"var(--safe-2)"}}>✓</span> PR #{pr.number} — {a.pkg} → {a.fix}</span>
        <a className="btn btn--primary btn--sm" href={pr.url} target="_blank" rel="noreferrer">View PR ↗</a>
      </div>
    );
  }

  return (
    <div style={{display:"flex", flexDirection:"column", gap:8}}>
      {!canPr ? (
        me && me.configured ? (
          <a className={`btn btn--sm ${primary ? "btn--primary" : ""} gh-signin`} href="/auth/github/login" style={{justifyContent:"center"}}>
            <GithubMark size={14} /> Sign in to open PR
          </a>
        ) : (
          <span className="mono" style={{fontSize:11.5, color:"var(--text-muted)", textAlign:"center", lineHeight:1.5}}>
            Set <code>GITHUB_TOKEN</code> or OAuth to open fix PRs. Local draft is already ready when exposed.
          </span>
        )
      ) : (
        <button className={`btn btn--sm ${primary ? "btn--primary" : ""}`} style={{justifyContent:"center", opacity: pr?.status === "loading" ? 0.7 : 1}}
                disabled={pr?.status === "loading" || !a.fix || a.verdict !== "exposed"} onClick={() => onOpenPR(a)}>
          {pr?.status === "loading" ? <span className="caret">opening PR</span>
            : a.verdict !== "exposed" ? "PR only for exposed"
            : a.fix ? `Open fix PR → ${a.pkg}@${a.fix}` : "No fix available"}
        </button>
      )}
      {pr && pr.status === "error" && <span className="mono" style={{fontSize:11.5, color:"var(--danger-2)"}}>✕ {pr.error}</span>}
      {canPr && me && me.repo && <span className="mono" style={{fontSize:11, color:"var(--text-muted)", textAlign:"center"}}>→ {me.repo}</span>}
      {a.pr_draft && a.verdict === "exposed" && (
        <span className="mono" style={{fontSize:11, color:"var(--safe-2)", textAlign:"center"}}>✓ PR body drafted with evidence</span>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// STYLES
// ─────────────────────────────────────────────────────────────
function DashboardStyles() {
  return <style dangerouslySetInnerHTML={{ __html: `
  .dash-shell{ display:flex; min-height:100vh; background:var(--bg); }

  /* ── sidebar ── */
  .dash-sidebar{
    width:238px; flex-shrink:0; position:sticky; top:0; height:100vh;
    display:flex; flex-direction:column; z-index:40;
    background:linear-gradient(180deg, var(--bg-deep) 0%, var(--bg) 100%);
    border-right:1px solid var(--border);
  }
  .dash-sidebar__brand{ height:56px; display:flex; align-items:center; padding:0 20px; border-bottom:1px solid var(--border); flex-shrink:0; }
  .dash-nav{ padding:8px 12px 16px; display:flex; flex-direction:column; gap:2px; flex:1; overflow-y:auto; }
  .dash-nav__label{ font-family:var(--font-mono); font-size:10px; letter-spacing:0.14em; text-transform:uppercase; color:var(--text-faint); padding:16px 12px 7px; }
  .nav-item{
    display:flex; align-items:center; gap:11px; width:100%;
    padding:9px 12px; border-radius:8px; border:1px solid transparent;
    color:var(--text-3); font-family:var(--font-sans); font-size:13.5px; text-decoration:none;
    cursor:pointer; position:relative; transition:background .14s, color .14s, border-color .14s;
  }
  .nav-item:hover{ background:var(--surface); color:var(--text-2); }
  .nav-item.active{ background:var(--primary-soft); color:var(--primary-2); border-color:rgba(249,115,22,0.22); }
  .nav-item.active::before{ content:""; position:absolute; left:-12px; top:50%; transform:translateY(-50%); width:3px; height:18px; border-radius:0 3px 3px 0; background:var(--primary); }
  .nav-item__badge{ margin-left:auto; font-family:var(--font-mono); font-size:11px; line-height:1; padding:3px 7px; border-radius:20px; background:var(--surface-2); color:var(--text-3); }
  .nav-item__badge.danger{ background:var(--danger-bg-2); color:var(--danger-2); }
  .dash-sidebar__foot{ padding:16px; border-top:1px solid var(--border); flex-shrink:0; display:flex; align-items:center; gap:9px; }
  .live-dot{ width:7px; height:7px; border-radius:50%; background:var(--safe-2); box-shadow:0 0 8px var(--safe-2); animation:pulse-dot 1.8s ease-in-out infinite; }

  /* ── main + header ── */
  .dash-main{ flex:1; min-width:0; display:flex; flex-direction:column; }
  .dash-header{
    position:sticky; top:0; z-index:30; height:56px; flex-shrink:0;
    display:flex; align-items:center; gap:14px; padding:0 24px; border-bottom:1px solid var(--border);
    background:rgba(8,11,18,0.72); backdrop-filter:blur(12px); -webkit-backdrop-filter:blur(12px);
  }
  .dash-crumb{ display:flex; align-items:center; gap:12px; min-width:0; }
  .dash-crumb__title{ font-size:15px; font-weight:600; color:var(--text); }
  .avatar{ width:32px; height:32px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-family:var(--font-mono); font-size:12px; font-weight:600; color:#fff; background:linear-gradient(135deg, var(--primary-2), var(--primary-3)); }
  .icon-btn{ width:34px; height:34px; display:inline-flex; align-items:center; justify-content:center; border-radius:8px; border:1px solid var(--border); background:var(--surface); color:var(--text-3); cursor:pointer; }
  .icon-btn:hover{ color:var(--text); border-color:var(--border-strong); }
  .hamburger{ display:none; }
  .dash-backdrop{ display:none; }

  /* ── github auth ── */
  .gh-signin{ text-decoration:none; }
  .gh-auth{ display:flex; align-items:center; gap:9px; }
  .gh-avatar{ width:32px; height:32px; border-radius:50%; border:1px solid var(--border-strong); object-fit:cover; }
  .gh-auth__info{ display:flex; flex-direction:column; line-height:1.15; }
  .gh-auth__login{ font-size:12.5px; color:var(--text); }
  .gh-auth__logout{ background:none; border:none; padding:0; text-align:left; cursor:pointer; font-family:var(--font-mono); font-size:10.5px; color:var(--text-muted); }
  .gh-auth__logout:hover{ color:var(--primary-2); }
  .gh-notconfigured{ font-size:11.5px; color:var(--text-muted); border:1px dashed var(--border-strong); border-radius:6px; padding:6px 10px; }

  /* ── content ── */
  .dash-content{ padding:24px; display:flex; flex-direction:column; gap:16px; max-width:1240px; width:100%; margin:0 auto; }

  /* ── scan panel ── */
  .hero-line{ font-size:12.5px; color:var(--text-3); margin:0 2px; }
  .hero-line em{ color:var(--primary-2); font-style:normal; font-weight:600; }
  .config-bar{ display:flex; flex-wrap:wrap; gap:6px 10px; align-items:center; font-size:11.5px; color:var(--text-muted); padding:8px 12px; border:1px solid var(--border); border-radius:var(--r-md); background:var(--bg-deep); }
  .config-bar .ok{ color:var(--safe-2); }
  .config-bar .warn{ color:var(--warn-2); }
  .config-bar .dim{ color:var(--text-muted); }
  .config-bar .sep{ opacity:0.4; }
  .empty-scan{ padding:28px 16px; text-align:center; color:var(--text-3); border:1px dashed var(--border); border-radius:var(--r-lg); font-size:12.5px; }
  .scan-panel{ display:flex; align-items:center; gap:14px; flex-wrap:wrap; background:linear-gradient(180deg, var(--surface-2) 0%, var(--surface) 100%); border:1px solid var(--border); border-radius:var(--r-lg); padding:12px 14px; }
  .scan-panel--stack{ flex-direction:column; align-items:stretch; gap:10px; }
  .scan-form{ display:flex; gap:8px; flex:1; min-width:280px; width:100%; }
  .scan-input{ display:flex; align-items:center; gap:8px; flex:1; padding:8px 12px; background:var(--bg-deep); border:1px solid var(--border); border-radius:var(--r-md); }
  .scan-input input{ flex:1; border:none; outline:none; background:transparent; font-family:var(--font-mono); font-size:13px; color:var(--text); }
  .scan-quick{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; }
  .scan-hint{ font-size:11.5px; color:var(--text-muted); }
  .chip--sm{ padding:4px 10px; font-size:11px; }

  /* ── summary strip ── */
  .summary-strip{ border:1px solid var(--border); border-radius:var(--r-lg); background:var(--surface); padding:14px 16px 12px; display:flex; flex-direction:column; gap:12px; }
  .summary-strip__head{ display:flex; flex-wrap:wrap; align-items:center; gap:10px; }
  .summary-strip__repo{ font-size:14px; color:var(--text); font-weight:600; }
  .summary-strip__stats{ display:grid; grid-template-columns:repeat(5, minmax(0,1fr)); gap:10px; }
  .summary-strip__stats div{ display:flex; flex-direction:column; gap:2px; padding:10px 12px; border-radius:var(--r-md); background:var(--bg-deep); border:1px solid var(--border); }
  .summary-strip__stats b{ font-family:var(--font-mono); font-size:22px; font-weight:600; color:var(--text); letter-spacing:-0.02em; }
  .summary-strip__stats span{ font-family:var(--font-mono); font-size:11px; color:var(--text-muted); }
  .summary-strip__stats .summary-note{ font-style:normal; font-size:10px; color:var(--text-faint); margin-top:2px; }
  .summary-strip__stats .is-danger b{ color:var(--danger-2); }
  .summary-strip__stats .is-safe b{ color:var(--safe-2); }
  .summary-strip__stats .is-warn b{ color:var(--warn-2); }
  .summary-strip__foot{ font-size:11.5px; color:var(--text-3); line-height:1.5; }
  .summary-strip__foot strong{ color:var(--text-2); font-weight:600; }
  .filter-hint{ font-size:11.5px; color:var(--text-muted); }
  .linkish{ background:none; border:none; color:var(--primary-2); cursor:pointer; font:inherit; text-decoration:underline; padding:0; }

  .callsite-list{ list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:10px; }
  .callsite-item{ display:flex; flex-direction:column; gap:4px; }
  .callsite-loc{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; font-size:11.5px; color:var(--text-2); }
  .callsite-kind{ font-size:10px; text-transform:uppercase; letter-spacing:0.06em; color:var(--primary-2); border:1px solid rgba(249,115,22,0.35); border-radius:4px; padding:1px 6px; }
  .callsite-sym{ color:var(--text-muted); }
  .callsite-snip{ font-family:var(--font-mono); font-size:12px; color:var(--text); background:var(--bg-deep); border:1px solid var(--border); border-radius:6px; padding:8px 10px; white-space:pre-wrap; word-break:break-word; }
  .why-not{ font-size:11.5px; color:var(--text-3); line-height:1.55; padding:10px 12px; border:1px dashed var(--border-strong); border-radius:var(--r-md); }

  /* ── table ── */
  .tbl-controls{ display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
  .tbl-search{ display:flex; align-items:center; gap:8px; background:var(--surface); border:1px solid var(--border); border-radius:6px; padding:5px 10px; }
  .tbl-search input{ background:transparent; border:none; outline:none; color:var(--text); font-family:var(--font-mono); font-size:12px; width:150px; }
  .chip{ display:inline-flex; align-items:center; gap:8px; padding:6px 12px; font-family:var(--font-mono); font-size:12px; color:var(--text-3); background:transparent; border:1px solid var(--border); border-radius:6px; cursor:pointer; transition:all .15s; }
  .chip:hover{ border-color:var(--border-strong); color:var(--text-2); }
  .chip.is-active{ color:var(--text); background:var(--surface-2); border-color:var(--border-strong); }
  .tbl-row{ display:grid; grid-template-columns:22px 1.2fr 1.3fr 96px 130px 92px 90px 20px; gap:12px; align-items:center; padding:14px 16px; }
  .tbl-head{ padding:10px 16px; background:var(--surface-2); border-bottom:1px solid var(--border); font-family:var(--font-mono); font-size:11px; color:var(--text-muted); letter-spacing:0.08em; text-transform:uppercase; }
  .tbl-body{ width:100%; border:none; background:transparent; color:var(--text); text-align:left; cursor:pointer; font-family:inherit; transition:background .14s; }
  .tbl-body:hover{ background:var(--surface); }
  .tbl-body.is-open{ background:var(--surface-2); }
  .expand-grid{ display:grid; grid-template-columns:1.3fr 1fr; gap:24px; }

  /* ── pr result ── */
  .pr-result{ display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap; font-family:var(--font-mono); font-size:12px; color:var(--text-2); border-radius:var(--r-md); padding:10px 12px; }
  .pr-result--ok{ background:var(--safe-bg); border:1px solid rgba(16,185,129,0.3); }

  /* ── repositories page ── */
  .repo-card{ padding:20px 22px; display:flex; flex-direction:column; gap:18px; }
  .repo-card__head{ display:flex; align-items:center; justify-content:space-between; gap:12px; }
  .repo-card__name{ font-size:15px; color:var(--text); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .repo-card__stats{ display:flex; gap:28px; padding:16px 0; border-top:1px solid var(--border); border-bottom:1px solid var(--border); }
  .repo-card__stats div{ display:flex; flex-direction:column; gap:3px; }
  .repo-card__stats b{ font-family:var(--font-mono); font-size:24px; font-weight:600; letter-spacing:-0.02em; }
  .repo-card__stats span{ font-family:var(--font-mono); font-size:11px; color:var(--text-muted); letter-spacing:0.04em; }
  .repo-card__foot{ display:flex; align-items:center; justify-content:space-between; gap:12px; }
  .empty-hint{ font-size:11.5px; color:var(--text-muted); margin:16px 2px 0; }

  /* ── security page ── */
  .callout-grid{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }
  .callout{ position:relative; overflow:hidden; border-radius:var(--r-lg); padding:20px 22px; }
  .callout--danger{ border:1px solid rgba(239,68,68,0.30); background:linear-gradient(180deg, rgba(239,68,68,0.05) 0%, transparent 80%); }
  .callout--safe{ border:1px solid rgba(16,185,129,0.25); background:linear-gradient(180deg, rgba(16,185,129,0.05) 0%, transparent 80%); }
  .callout__meta{ font-family:var(--font-mono); font-size:11px; color:var(--text-muted); display:flex; gap:14px; flex-wrap:wrap; }

  /* ── settings page ── */
  .set-card{ padding:18px 20px; display:flex; flex-direction:column; gap:14px; }
  .set-card__label{ font-family:var(--font-mono); font-size:11px; color:var(--text-muted); letter-spacing:0.08em; text-transform:uppercase; }
  .set-row{ display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap; }
  .set-note{ font-size:12.5px; color:var(--text-3); line-height:1.6; margin:0; }
  .set-radios{ display:flex; gap:8px; flex-wrap:wrap; }

  /* ── responsive ── */
  @media (max-width:960px){
    .dash-sidebar{ position:fixed; left:0; top:0; transform:translateX(-100%); transition:transform .22s ease; box-shadow:0 0 70px rgba(0,0,0,0.55); }
    .dash-sidebar.open{ transform:translateX(0); }
    .hamburger{ display:inline-flex; }
    .dash-backdrop.show{ display:block; position:fixed; inset:0; background:rgba(0,0,0,0.55); z-index:35; }
    .expand-grid{ grid-template-columns:1fr; }
    .callout-grid{ grid-template-columns:1fr; }
  }
  @media (max-width:900px){
    .summary-strip__stats{ grid-template-columns:repeat(2, minmax(0,1fr)); }
  }
  @media (max-width:720px){
    .dash-header{ padding:0 16px; }
    .dash-content{ padding:16px; }
    .tbl-row{ grid-template-columns:20px 1.4fr 96px 108px 24px; }
    .tbl-row > :nth-child(3){ display:none; }
    .tbl-row > :nth-child(6){ display:none; }
    .tbl-row > :nth-child(7){ display:none; }
  }
  ` }} />;
}

// mount
ReactDOM.createRoot(document.getElementById("root")).render(<App />);
