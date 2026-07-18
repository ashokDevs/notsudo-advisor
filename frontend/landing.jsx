// landing.jsx — full NotSudo Advisor landing page
// All 10 sections. Terminal/security-research aesthetic. Animated pipeline hero.

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "monoFont": "geist"
}/*EDITMODE-END*/;

const MONO_FONTS = {
  geist:    `"Geist Mono", ui-monospace, "SFMono-Regular", Menlo, monospace`,
  jetbrains:`"JetBrains Mono", ui-monospace, "SFMono-Regular", Menlo, monospace`,
  berkeley: `"IBM Plex Mono", "Berkeley Mono", ui-monospace, Menlo, monospace`,
};

function applyMonoFont(key) {
  const fam = MONO_FONTS[key] || MONO_FONTS.geist;
  document.documentElement.style.setProperty("--font-mono", fam);
}

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  useEffect(() => { applyMonoFont(t.monoFont); }, [t.monoFont]);

  return (
    <F>
      <Nav />
      <Hero />
      <Problem />
      <Features />
      <HowItWorks />
      <AdversarialCallout />
      <Testimonials />
      <Pricing />
      <FinalCTA />
      <Footer />

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
// NAV  — real GitHub OAuth Sign in
// ─────────────────────────────────────────────────────────────
function GithubIcon({ size = 15 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z"/>
    </svg>
  );
}

function Nav() {
  const [me, setMe] = useState(null);
  const [authError, setAuthError] = useState(null);

  useEffect(() => {
    fetch("/api/me")
      .then(r => r.json())
      .then(setMe)
      .catch(() => setMe({ user: null, configured: false }));
    try {
      const q = new URLSearchParams(window.location.search);
      if (q.get("oauth_error")) {
        setAuthError(q.get("oauth_error"));
        window.history.replaceState({}, "", window.location.pathname);
      }
    } catch (_) { /* ignore */ }
  }, []);

  const user = me && me.user;
  const oauthReady = me && me.configured;

  return (
    <header style={{
      position:"sticky", top:0, zIndex:20,
      background:"rgba(8,11,18,0.78)",
      backdropFilter:"blur(12px) saturate(140%)",
      WebkitBackdropFilter:"blur(12px) saturate(140%)",
      borderBottom:"1px solid var(--border)",
    }}>
      <div className="container" style={{
        display:"flex", alignItems:"center", justifyContent:"space-between",
        height:62,
      }}>
        <div style={{display:"flex", alignItems:"center", gap:24}}>
          <a href="Landing.html"><Logo size={22}/></a>
          <span className="pill pill--neutral" style={{fontSize:10}}>v0.4 · early access</span>
        </div>
        <nav style={{display:"flex", alignItems:"center", gap:28, fontSize:13, color:"var(--text-3)", whiteSpace:"nowrap"}}>
          <a href="#how" className="mono">how it works</a>
          <a href="#pricing" className="mono">pricing</a>
          <a href="https://github.com/ashokDevs/notsudo-advisor" className="mono" target="_blank" rel="noreferrer">docs</a>
        </nav>
        <div style={{display:"flex", alignItems:"center", gap:10, whiteSpace:"nowrap"}}>
          {user ? (
            <>
              <a href="Dashboard.html" className="btn btn--ghost btn--sm" style={{display:"inline-flex", alignItems:"center", gap:8}}>
                {user.avatar_url
                  ? <img src={user.avatar_url} alt="" width={18} height={18} style={{borderRadius:"50%"}} />
                  : <GithubIcon size={14} />}
                <span className="mono">{user.login}</span>
              </a>
              <a href="Dashboard.html" className="btn btn--primary btn--sm">
                Open dashboard <span style={{opacity:0.7}}>→</span>
              </a>
            </>
          ) : (
            <>
              <a
                href="/auth/github/login?next=/Dashboard.html"
                className="btn btn--ghost btn--sm"
                style={{display:"inline-flex", alignItems:"center", gap:8}}
                title="Sign in with GitHub (OAuth)"
                data-oauth-signin="1"
              >
                <GithubIcon size={14} /> Sign in with GitHub
              </a>
              <a href="Dashboard.html" className="btn btn--primary btn--sm">
                Open dashboard <span style={{opacity:0.7}}>→</span>
              </a>
            </>
          )}
        </div>
      </div>
      {authError && (
        <div className="container" style={{paddingBottom:10}}>
          <div className="mono" style={{
            fontSize:12, color:"var(--danger-2)",
            border:"1px solid rgba(239,68,68,0.35)",
            background:"rgba(239,68,68,0.08)",
            borderRadius:8, padding:"8px 12px",
            display:"flex", justifyContent:"space-between", gap:12,
          }}>
            <span>✕ Sign in failed: {authError}</span>
            <button type="button" onClick={() => setAuthError(null)}
                    style={{background:"none", border:"none", color:"inherit", cursor:"pointer", fontFamily:"inherit"}}>
              dismiss
            </button>
          </div>
        </div>
      )}
    </header>
  );
}

// ─────────────────────────────────────────────────────────────
// HERO  — Drizzle-flavored: bold mono headline, scanning console
// ─────────────────────────────────────────────────────────────
function Hero() {
  return (
    <section style={{position:"relative", paddingTop: 140, paddingBottom: 130, overflow:"hidden"}}>
      <HeroBackdrop />
      <div className="container" style={{position:"relative", display:"grid", gridTemplateColumns:"minmax(0, 1.04fr) minmax(0, 1fr)", gap:56, alignItems:"center"}}>
        <div>
          <div className="eyebrow" style={{marginBottom: 22, display:"inline-flex", alignItems:"center", gap:10, whiteSpace:"nowrap", flexWrap:"wrap"}}>
            <span style={{
              display:"inline-flex", alignItems:"center", gap:6,
              padding:"3px 8px",
              border:"1px solid rgba(249,115,22,0.30)",
              borderRadius: 999,
              color:"var(--primary-2)",
              background:"var(--primary-soft)",
            }}>
              <span style={{
                width:6, height:6, borderRadius:"50%",
                background:"var(--primary)",
                boxShadow:"0 0 8px var(--primary)",
                animation:"pulse-dot 1.4s ease-in-out infinite",
              }}/>
              <span style={{fontSize: 10.5, letterSpacing:"0.12em"}}>v0.4 — early access</span>
            </span>
            <span style={{color:"var(--text-faint)"}}>·</span>
            <span>reachability-aware CVE triage</span>
          </div>

          <h1 style={{
            fontFamily:"var(--font-mono)",
            fontSize: "clamp(38px, 4.8vw, 64px)",
            lineHeight: 0.98,
            letterSpacing:"-0.045em",
            fontWeight: 600,
            margin: "0 0 24px",
            color:"var(--text)",
            textWrap: "balance",
          }}>
            Catch real bugs<br/>
            <span style={{color:"var(--primary)"}}>before&nbsp;they&nbsp;ship.</span>
          </h1>

          <p style={{
            fontSize: 17.5, lineHeight: 1.55, color:"var(--text-3)",
            margin: "0 0 32px", maxWidth: 540, textWrap:"pretty",
          }}>
            Most CVE scanners flag every vulnerable package they find. NotSudo Advisor
            traces whether the vulnerable code is <em style={{color:"var(--text)", fontStyle:"normal"}}>actually reachable</em> from your app —
            kills the 87% that aren&rsquo;t, and opens a PR with cited evidence on the 13% that are.
          </p>

          <div style={{display:"flex", gap:10, alignItems:"center", marginBottom: 40, flexWrap:"wrap", whiteSpace:"nowrap"}}>
            <a href="Dashboard.html" className="btn btn--primary">
              See it on a real repo&nbsp;&nbsp;→
            </a>
            <a href="#how" className="btn">
              <span style={{color:"var(--text-muted)"}}>$</span>&nbsp;cat architecture.md
            </a>
            <span style={{
              fontFamily:"var(--font-mono)", fontSize: 11, color:"var(--text-muted)",
              marginLeft: 4,
            }}>
              free for 50 advisories
            </span>
          </div>

          {/* stat strip */}
          <div style={{
            display:"grid", gridTemplateColumns:"repeat(4, 1fr)", gap: 0,
            border:"1px solid var(--border)", borderRadius:"var(--r-lg)",
            background:"linear-gradient(180deg, var(--surface) 0%, rgba(13,17,23,0.4) 100%)",
            overflow:"hidden",
          }}>
            <StatCell big="87%"   label="killed at triage" />
            <StatCell big="$0.16" label="avg / advisory"     divide />
            <StatCell big="43s"   label="time to verdict"    divide />
            <StatCell big="<10%"  label="false-positive target" divide />
          </div>
        </div>

        <div style={{position:"relative"}}>
          <ScanConsole />
          <div style={{
            display:"flex", alignItems:"center", justifyContent:"space-between",
            marginTop: 12, fontFamily:"var(--font-mono)", fontSize: 11, color:"var(--text-muted)",
          }}>
            <span>// live scan · acme/payments-api</span>
            <span><span style={{color:"var(--text-faint)"}}>read-only sandbox</span></span>
          </div>
        </div>
      </div>
    </section>
  );
}

// Security-flavored ambient background.
// Layers: faint hex/grid + a slow radar sweep + corner crosshairs + scanlines.
function HeroBackdrop() {
  return (
    <div aria-hidden="true" style={{position:"absolute", inset:0, pointerEvents:"none", overflow:"hidden"}}>
      {/* drifting grid */}
      <div className="grid-bg" style={{
        position:"absolute", inset: -2,
        animation:"grid-drift 22s linear infinite",
        maskImage:"radial-gradient(ellipse 90% 75% at 60% 45%, black 20%, transparent 75%)",
        WebkitMaskImage:"radial-gradient(ellipse 90% 75% at 60% 45%, black 20%, transparent 75%)",
        opacity: 0.9,
      }}/>
      {/* warm orange glow upper-right (where the console is) */}
      <div style={{
        position:"absolute", top:"-10%", right:"-5%",
        width: 720, height: 720,
        background:"radial-gradient(circle, rgba(249,115,22,0.16) 0%, rgba(249,115,22,0.05) 35%, transparent 65%)",
        filter:"blur(4px)",
      }}/>
      {/* radar sweep behind the console — orange cone rotating slowly */}
      <div style={{
        position:"absolute", top: 80, right: -120,
        width: 540, height: 540, borderRadius:"50%",
        overflow:"hidden", opacity: 0.42,
        maskImage:"radial-gradient(circle, black 30%, transparent 75%)",
        WebkitMaskImage:"radial-gradient(circle, black 30%, transparent 75%)",
      }}>
        <div style={{
          position:"absolute", inset:0,
          background:"conic-gradient(from 0deg, transparent 0deg, rgba(249,115,22,0.30) 30deg, transparent 60deg)",
          animation:"radar-sweep 7s linear infinite",
        }}/>
        {/* radar rings */}
        <svg style={{position:"absolute", inset:0}} viewBox="0 0 540 540" fill="none">
          <circle cx="270" cy="270" r="80"  stroke="rgba(249,115,22,0.18)" strokeWidth="1"/>
          <circle cx="270" cy="270" r="160" stroke="rgba(249,115,22,0.13)" strokeWidth="1"/>
          <circle cx="270" cy="270" r="240" stroke="rgba(249,115,22,0.08)" strokeWidth="1"/>
        </svg>
      </div>
      {/* corner crosshairs (the security/HUD touch) */}
      <Crosshair top="56px" left="32px" />
      <Crosshair top="56px" right="32px" />
      {/* faint horizontal scanlines */}
      <div style={{
        position:"absolute", inset:0,
        backgroundImage:"repeating-linear-gradient(0deg, rgba(241,245,249,0.018) 0 1px, transparent 1px 4px)",
        mixBlendMode:"screen",
      }}/>
    </div>
  );
}

function Crosshair({ top, left, right }) {
  const size = 14, c = "rgba(249,115,22,0.45)";
  return (
    <div style={{position:"absolute", top, left, right, width: size, height: size}}>
      <span style={{position:"absolute", top:0, left:0, width:size, height:1, background:c}}/>
      <span style={{position:"absolute", top:0, left: left ? 0 : "auto", right: right ? 0 : "auto", width:1, height:size, background:c}}/>
    </div>
  );
}

function StatCell({ big, label, divide }) {
  return (
    <div style={{
      padding:"14px 16px",
      borderLeft: divide ? "1px solid var(--border)" : "none",
    }}>
      <div style={{
        fontFamily:"var(--font-mono)", fontSize: 24, fontWeight: 600,
        letterSpacing:"-0.03em", color:"var(--text)",
      }}>{big}</div>
      <div style={{
        fontFamily:"var(--font-mono)", fontSize: 10.5, color:"var(--text-muted)",
        letterSpacing:"0.08em", textTransform:"uppercase", marginTop:2,
      }}>{label}</div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// PROBLEM  — before/after PR view
// ─────────────────────────────────────────────────────────────
function Problem() {
  return (
    <section id="problem" style={{padding:"160px 0 140px", borderTop:"1px solid var(--border)"}}>
      <div className="container">
        <SectionHeader
          eye="§ 01 · the problem"
          h="Every scanner says the same thing."
          sub="If a vulnerable package is in package.json, it gets flagged. That's cheap to compute and mostly correct &mdash; and it's exactly why every engineer on your team has muted the bot."
        />
        <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap: 18, marginTop: 48}}>
          <PRMock variant="dependabot" />
          <PRMock variant="notsudo" />
        </div>
        <div style={{
          marginTop: 22, fontFamily:"var(--font-mono)", fontSize: 12,
          color:"var(--text-muted)", textAlign:"center",
        }}>
          ────── same CVE, different signal ──────
        </div>
      </div>
    </section>
  );
}

function PRMock({ variant }) {
  const noisy = variant === "dependabot";
  return (
    <div style={{
      border:"1px solid var(--border)",
      borderRadius:"var(--r-lg)",
      overflow:"hidden",
      background:"var(--surface)",
      display:"flex", flexDirection:"column",
    }}>
      <div style={{
        padding:"12px 16px", borderBottom:"1px solid var(--border)",
        display:"flex", alignItems:"center", gap:10,
        background:"var(--surface-2)",
        fontFamily:"var(--font-mono)", fontSize:12, color:"var(--text-3)",
      }}>
        {noisy ? (
          <F>
            <span style={{color:"var(--text-muted)"}}>github.com/acme/payments-api · </span>
            <span>#4823</span>
            <span className="pill pill--neutral" style={{marginLeft:"auto", fontSize:10}}>dependabot</span>
          </F>
        ) : (
          <F>
            <span style={{color:"var(--text-muted)"}}>github.com/acme/payments-api · </span>
            <span>#4824</span>
            <span className="pill pill--primary" style={{marginLeft:"auto", fontSize:10}}>notsudo</span>
          </F>
        )}
      </div>
      <div style={{padding:"18px 22px 22px", flex:1, display:"flex", flexDirection:"column", gap: 14}}>
        <div style={{
          fontFamily:"var(--font-mono)", fontSize: 15, color:"var(--text)",
          letterSpacing:"-0.005em", lineHeight: 1.4,
        }}>
          {noisy
            ? <F>chore(deps): bump <span style={{color:"var(--node-2)"}}>express</span> from 4.18.2 to 4.19.2</F>
            : <F>fix(security): <span style={{color:"var(--danger-2)"}}>EXPOSED</span> &mdash; bump <span style={{color:"var(--node-2)"}}>express</span> for open-redirect (4 reachable call sites)</F>}
        </div>

        {noisy ? (
          <F>
            <p style={{fontSize:13, color:"var(--text-3)", margin:0, lineHeight:1.55}}>
              Bumps <span className="mono" style={{color:"var(--text-2)"}}>express</span> from 4.18.2 to 4.19.2.
              <br/><br/>
              <span className="mono" style={{color:"var(--text-muted)"}}>Release notes&nbsp;·&nbsp;Commits&nbsp;·&nbsp;Maintainer info</span>
            </p>
            <div style={{
              padding:"10px 12px", border:"1px dashed var(--border-strong)", borderRadius:6,
              fontFamily:"var(--font-mono)", fontSize:11, color:"var(--text-muted)",
              background:"rgba(148,163,184,0.04)",
            }}>
              <span style={{color:"var(--text-3)"}}>compatibility</span> ████░░ 67%
              &nbsp;·&nbsp;<span style={{color:"var(--text-3)"}}>22</span> previous bumps merged
            </div>
            <div style={{marginTop:"auto", display:"flex", gap:8, flexWrap:"wrap"}}>
              <span className="pill pill--neutral">deps</span>
              <span className="pill pill--neutral">javascript</span>
            </div>
            <div style={{
              fontFamily:"var(--font-mono)", fontSize: 11, color:"var(--text-faint)",
              fontStyle:"italic", marginTop: 6,
            }}>
              // muted by maya on 2024-11-03
            </div>
          </F>
        ) : (
          <F>
            <div style={{display:"flex", gap:8, flexWrap:"wrap"}}>
              <VerdictPill v="exposed" />
              <span className="pill pill--neutral">confidence 0.81</span>
              <span className="pill pill--neutral">cost $0.24</span>
              <span className="pill pill--neutral">62s</span>
            </div>

            <div style={{fontSize:13, color:"var(--text-2)", lineHeight:1.6, margin:0}}>
              <span className="eyebrow" style={{display:"block", marginBottom:6}}>// reasoning</span>
              Four <span className="mono" style={{color:"var(--text)"}}>res.redirect()</span> call
              sites take values derived from <span className="mono" style={{color:"var(--text)"}}>req.query.next</span> without
              an allow-list. Reachable from <span className="mono" style={{color:"var(--text)"}}>POST /auth/callback</span>.
            </div>

            <div style={{
              fontFamily:"var(--font-mono)", fontSize: 12,
              padding:"10px 12px",
              background:"var(--bg-deep)",
              border:"1px solid var(--border)",
              borderLeft:"2px solid var(--node-3)",
              borderRadius:4, color:"var(--text-2)",
            }}>
              <div style={{color:"var(--text-muted)", fontSize:10, letterSpacing:"0.08em", textTransform:"uppercase", marginBottom:4}}>
                evidence · GHSA-rv95-896h-c2vc § Details
              </div>
              &ldquo;Versions of Express prior to 4.19.2 do not perform encoding on the redirect URL allowing for the possibility of open redirect.&rdquo;
            </div>

            <div style={{marginTop:"auto", display:"flex", gap:8, flexWrap:"wrap"}}>
              <span className="pill pill--exposed">requires review</span>
              <span className="pill pill--neutral">reachable: 4 sites</span>
              <span className="pill pill--neutral">entry: routes/auth.ts</span>
            </div>
          </F>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// FEATURES — 3 cards
// ─────────────────────────────────────────────────────────────
function Features() {
  const items = [
    {
      no: "01",
      title: "Reachability, not presence",
      body: "Static call-graph analysis plus a runtime probe. We trace from your declared entry points through the import graph until we hit the vulnerable function — or don’t.",
      foot: "// the 13% that actually matter",
    },
    {
      no: "02",
      title: "Capability isolation",
      body: "Advisory text is attacker-controlled. NotSudo ingests it through a sandboxed parser with no tool access. The reasoner that decides verdicts never sees raw text.",
      foot: "// prompt injection ≠ command execution",
    },
    {
      no: "03",
      title: "Cost-aware routing",
      body: "A cheap classifier handles 70% of advisories in under a second. The frontier model only runs when the cheap path returns low confidence. Average advisory: $0.16.",
      foot: "// haiku first, opus last",
    },
  ];
  return (
    <section id="features" style={{padding:"140px 0", borderTop:"1px solid var(--border)"}}>
      <div className="container">
        <SectionHeader
          eye="§ 02 · how it stays useful"
          h="Three architectural decisions."
          sub="Most security tooling treats AI as a magic box. We don't. Every choice below is the difference between a tool engineers trust and one they mute."
        />
        <div style={{display:"grid", gridTemplateColumns:"repeat(3, 1fr)", gap: 16, marginTop: 48}}>
          {items.map(it => (
            <div key={it.no} className="card" style={{padding:"24px 24px 22px", display:"flex", flexDirection:"column", gap:14, position:"relative", overflow:"hidden"}}>
              <div className="mono" style={{
                fontSize: 11, color:"var(--text-muted)", letterSpacing:"0.1em",
              }}>{it.no}</div>
              <h3 style={{
                fontSize: 20, margin:0, fontWeight: 600,
                letterSpacing:"-0.015em", color:"var(--text)",
              }}>{it.title}</h3>
              <p style={{fontSize: 14, color:"var(--text-3)", lineHeight:1.6, margin:0, textWrap:"pretty"}}>{it.body}</p>
              <div className="mono" style={{
                marginTop:"auto", paddingTop: 14, borderTop:"1px dashed var(--border)",
                fontSize: 11, color:"var(--text-faint)",
              }}>{it.foot}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────
// HOW IT WORKS  — 4-node pipeline detail
// ─────────────────────────────────────────────────────────────
function HowItWorks() {
  const stages = [
    {
      n: NODES[0],
      title: "Triage",
      body: "Fast classifier looks at the advisory metadata, your package manifest, and a static map of which packages even export symbols you import. Kills the obvious noise.",
      meta: ["Haiku 4.5", "~600ms", "70% caught here"],
    },
    {
      n: NODES[1],
      title: "Reachability",
      body: "A call-graph walker starts at every declared entry point in your repo and traces forward, checking whether any path lands in the vulnerable function. Symbol-level, not file-level.",
      meta: ["tree-sitter + LSP", "~12s", "no symbol → done"],
    },
    {
      n: NODES[2],
      title: "Evidence",
      body: "Pulls direct quotes from the advisory text and the relevant source files. Validates each quote against its source. Anything synthesized is rejected.",
      meta: ["citation guard", "~8s", "no quotes = no PR"],
    },
    {
      n: NODES[3],
      title: "Verdict",
      body: "Reasoner gets the evidence — never the raw advisory. Returns one of EXPOSED, NOT REACHABLE, or UNSURE, with a confidence score and a draft PR body.",
      meta: ["Sonnet 4.5", "~22s", "auto-merge: off"],
    },
  ];
  return (
    <section id="how" style={{padding:"160px 0 150px", borderTop:"1px solid var(--border)", position:"relative"}}>
      <div className="container">
        <SectionHeader
          eye="§ 03 · how it works"
          h="Four nodes. Cheap first, frontier last."
          sub="Every advisory goes through the same pipeline. Most fall out at node 1 or 2. The expensive nodes only run when the cheap ones can't decide."
        />

        <div style={{marginTop: 56, display:"grid", gridTemplateColumns:"1fr 1fr 1fr 1fr", gap: 0, borderLeft:"1px solid var(--border)", borderRight:"1px solid var(--border)", borderRadius: 10, overflow:"hidden", background:"var(--surface)"}}>
          {stages.map((s, i) => (
            <div key={s.n.id} style={{
              padding:"28px 24px 26px",
              borderRight: i < stages.length - 1 ? "1px solid var(--border)" : "none",
              position:"relative",
              borderTop:"1px solid var(--border)",
              borderBottom:"1px solid var(--border)",
            }}>
              <div style={{
                display:"flex", alignItems:"center", gap:10, marginBottom: 18,
              }}>
                <span style={{
                  width: 10, height: 10, borderRadius:"50%", background: s.n.color,
                  boxShadow:`0 0 12px ${s.n.color}`,
                }}/>
                <span className="mono" style={{fontSize:11, color:"var(--text-muted)", letterSpacing:"0.1em"}}>NODE {s.n.glyph}</span>
              </div>
              <h3 style={{
                fontSize: 22, margin:"0 0 12px", fontWeight: 600,
                letterSpacing:"-0.015em",
                fontFamily:"var(--font-mono)",
                color: s.n.color,
              }}>{s.title}</h3>
              <p style={{fontSize:13.5, lineHeight:1.6, color:"var(--text-3)", margin:"0 0 18px", textWrap:"pretty"}}>{s.body}</p>
              <div style={{display:"flex", flexDirection:"column", gap:6, fontFamily:"var(--font-mono)", fontSize:11, color:"var(--text-muted)"}}>
                {s.meta.map(m => <div key={m}><span style={{color:"var(--text-faint)"}}>›</span>&nbsp;{m}</div>)}
              </div>
            </div>
          ))}
        </div>

        {/* a static rail at the bottom showing the flow + RRF detail */}
        <div style={{
          marginTop: 24, padding:"14px 18px",
          border:"1px dashed var(--border-strong)", borderRadius:8,
          fontFamily:"var(--font-mono)", fontSize: 12, color:"var(--text-3)",
          display:"flex", gap:18, alignItems:"center", justifyContent:"space-between", flexWrap:"wrap",
        }}>
          <span><span style={{color:"var(--text-muted)"}}>retrieval</span> · vector + FTS &nbsp;<span style={{color:"var(--text-faint)"}}>merged via</span>&nbsp; <span style={{color:"var(--node-2)"}}>RRF(k=60)</span></span>
          <span><span style={{color:"var(--text-muted)"}}>throttle</span> · max <span style={{color:"var(--text)"}}>5 PRs/repo/day</span></span>
          <span><span style={{color:"var(--text-muted)"}}>replay</span> · deterministic on the same seed</span>
          <span><span style={{color:"var(--text-muted)"}}>traces</span> · LangSmith on Pro+</span>
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────
// ADVERSARIAL CALLOUT  — the red one
// ─────────────────────────────────────────────────────────────
function AdversarialCallout() {
  return (
    <section id="adversarial" style={{padding:"140px 0 140px", borderTop:"1px solid var(--border)"}}>
      <div className="container">
        <div style={{
          position:"relative", overflow:"hidden",
          border:"1px solid rgba(239,68,68,0.32)",
          borderRadius:"var(--r-lg)",
          background:"linear-gradient(180deg, rgba(239,68,68,0.06) 0%, rgba(239,68,68,0.02) 100%)",
          padding:"36px 40px",
        }}>
          {/* faint hatched background */}
          <div aria-hidden="true" style={{
            position:"absolute", inset:0,
            backgroundImage:"repeating-linear-gradient(135deg, rgba(239,68,68,0.05) 0 1px, transparent 1px 12px)",
            pointerEvents:"none",
          }}/>
          <div style={{display:"grid", gridTemplateColumns:"minmax(0, 1fr) minmax(0, 1.05fr)", gap:48, alignItems:"center", position:"relative"}}>
            <div>
              <div className="eyebrow" style={{color:"var(--danger-2)", display:"inline-flex", gap:8, alignItems:"center"}}>
                <span style={{
                  width:7, height:7, borderRadius:"50%",
                  background:"var(--danger-2)",
                  boxShadow:"0 0 10px var(--danger-2)",
                  animation:"pulse-dot 1.4s ease-in-out infinite",
                }}/>
                § 04 · threat model
              </div>
              <h2 style={{
                fontSize:"clamp(28px, 3.6vw, 40px)",
                lineHeight: 1.1, letterSpacing:"-0.02em",
                margin:"14px 0 16px", fontWeight: 600,
                color:"var(--text)",
                textWrap:"balance",
              }}>
                Advisory text is <span style={{fontFamily:"var(--font-mono)", color:"var(--danger-2)", letterSpacing:"-0.03em"}}>attacker-controlled.</span>
              </h2>
              <p style={{fontSize:15.5, color:"var(--text-2)", lineHeight:1.65, margin:0, textWrap:"pretty"}}>
                OSV and GHSA accept community submissions. A sufficiently motivated attacker can embed
                instructions inside an advisory description &mdash; instructions designed to manipulate any AI agent that reads it.
                Most tools that process advisories with an LLM have <em>not</em> thought about this.
              </p>
              <p style={{fontSize:15.5, color:"var(--text-2)", lineHeight:1.65, margin:"16px 0 0", textWrap:"pretty"}}>
                NotSudo solves it architecturally: the component with capabilities <em>never sees the raw text.</em>
                Prompt injection becomes inert &mdash; not because we trained around it, but because there&rsquo;s nothing to inject into.
              </p>
            </div>
            <div style={{
              fontFamily:"var(--font-mono)", fontSize: 12,
              color:"var(--text-2)",
              border:"1px solid var(--border)",
              borderRadius:"var(--r-md)",
              background:"var(--bg-deep)",
              padding:"18px 18px",
              lineHeight: 1.7,
            }}>
              <div style={{color:"var(--text-muted)", fontSize:10, letterSpacing:"0.1em", textTransform:"uppercase", marginBottom:10}}>
                isolation boundary
              </div>
              <div><span style={{color:"var(--danger-2)"}}>┌─</span> <span style={{color:"var(--text-muted)"}}>ingest</span>  parser :: no tools, no net</div>
              <div><span style={{color:"var(--danger-2)"}}>│</span>  &nbsp;&nbsp;&nbsp;<span style={{color:"var(--text-3)"}}>raw advisory text lives here →</span></div>
              <div><span style={{color:"var(--danger-2)"}}>│</span>  &nbsp;&nbsp;&nbsp;<span style={{color:"var(--text-faint)"}}>(stripped to structured fields)</span></div>
              <div><span style={{color:"var(--danger-2)"}}>└─</span> <span style={{color:"var(--text-muted)"}}>emit</span>    {`{ pkg, range, function, quotes[] }`}</div>
              <div style={{margin:"10px 0 10px", color:"var(--text-faint)"}}>──────────────────────────────────</div>
              <div><span style={{color:"var(--node-4)"}}>┌─</span> <span style={{color:"var(--text-muted)"}}>reason</span>  has tools :: <span style={{color:"var(--text-2)"}}>fs.read, git.diff, pr.draft</span></div>
              <div><span style={{color:"var(--node-4)"}}>│</span>  &nbsp;&nbsp;&nbsp;<span style={{color:"var(--text-3)"}}>only structured fields →</span></div>
              <div><span style={{color:"var(--node-4)"}}>│</span>  &nbsp;&nbsp;&nbsp;<span style={{color:"var(--text-faint)"}}>(quotes validated against sources)</span></div>
              <div><span style={{color:"var(--node-4)"}}>└─</span> <span style={{color:"var(--text-muted)"}}>verdict</span> EXPOSED · NOT REACHABLE · UNSURE</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────
// TESTIMONIALS — 3 quotes + key-numbers editorial moment
// ─────────────────────────────────────────────────────────────
function Testimonials() {
  const quotes = [
    {
      body: "We went from 25 Dependabot PRs a week to 3 PRs that we actually merged. The others were either killed at triage or came back 'not reachable' with the reasoning attached. Engineers stopped muting the bot.",
      name: "Priya S.",
      role: "Head of Engineering, Fintech (Series B)",
    },
    {
      body: "The prompt-injection isolation story is what sold me. We ingest advisories automatically — I'd been worried about that attack surface and hadn't seen another tool that had even thought about it architecturally.",
      name: "Tom K.",
      role: "Staff Security Engineer, Developer tools",
    },
    {
      body: "The evidence quotes in the PRs changed how my team thinks about CVE triage. Instead of 'bump it and move on', they read the reasoning. That's the real value — not just the automation.",
      name: "Asel M.",
      role: "Platform Engineer, E-commerce",
    },
    {
      body: "We connected it to our SOC 2 audit workflow. Every advisory we assessed has a dated record with the verdict, the evidence, and the confidence score. Auditors actually liked seeing it.",
      name: "Daniel R.",
      role: "CTO, B2B SaaS (Series A)",
    },
  ];
  return (
    <section id="proof" style={{padding:"160px 0 160px", borderTop:"1px solid var(--border)"}}>
      <div className="container">
        {/* editorial big-numbers moment */}
        <div style={{
          display:"grid", gridTemplateColumns:"minmax(0, 1.2fr) minmax(0, 1fr)", gap:64, alignItems:"end",
          marginBottom: 80, position:"relative",
        }}>
          <div>
            <div className="eyebrow" style={{marginBottom: 18}}>§ 05 · the numbers</div>
            <div style={{
              fontFamily:"var(--font-mono)",
              fontSize:"clamp(80px, 14vw, 200px)",
              lineHeight: 0.85, letterSpacing:"-0.06em",
              color:"var(--text)", fontWeight:600,
              display:"flex", alignItems:"baseline",
            }}>
              87<span style={{color:"var(--primary-2)", fontSize:"0.55em"}}>%</span>
            </div>
            <div style={{
              marginTop: 14, fontSize: 17, color:"var(--text-3)",
              maxWidth: 460, lineHeight:1.55,
            }}>
              of advisories never reach production code. We kill those at triage. The other <span style={{color:"var(--text)"}}>13%</span> get the frontier treatment &mdash; with cited evidence and a draft PR.
            </div>
          </div>
          <div style={{
            display:"grid", gridTemplateColumns:"1fr", gap: 22,
            paddingLeft: 32, borderLeft:"1px solid var(--border)",
          }}>
            <BigNumber n="$0.16" l="average cost per advisory" sub="cheap classifier first; frontier only when it matters" />
            <BigNumber n="43s"   l="median time to verdict"   sub="from advisory ingest to draft PR" />
            <BigNumber n="5"     l="max PRs / repo / day"     sub="hard cap. we will not flood your inbox." />
          </div>
        </div>

        <SectionHeader
          eye="§ 06 · operators using it"
          h="Trusted by teams who don't trust automation."
          sub="Engineers who'd already muted Dependabot. The bar was high."
        />

        <div style={{display:"grid", gridTemplateColumns:"1.05fr 1fr 1fr", gap: 16, marginTop: 48}}>
          <Quote big {...quotes[0]} />
          <Quote {...quotes[1]} />
          <Quote {...quotes[2]} />
        </div>
        <div style={{marginTop:16}}>
          <Quote wide {...quotes[3]} />
        </div>
      </div>
    </section>
  );
}

function BigNumber({ n, l, sub }) {
  return (
    <div>
      <div style={{
        fontFamily:"var(--font-mono)", fontSize: 44, fontWeight: 600,
        letterSpacing:"-0.04em", color:"var(--text)", lineHeight: 1,
      }}>{n}</div>
      <div style={{
        marginTop: 8, fontFamily:"var(--font-mono)", fontSize: 12,
        color:"var(--text-3)", textTransform:"uppercase", letterSpacing:"0.08em",
      }}>{l}</div>
      <div style={{marginTop: 6, fontSize:13, color:"var(--text-muted)"}}>{sub}</div>
    </div>
  );
}

function Quote({ body, name, role, big, wide }) {
  return (
    <figure style={{
      margin:0, padding:"24px 26px 22px",
      background: big ? "linear-gradient(180deg, var(--surface-2) 0%, var(--surface) 100%)" : "var(--surface)",
      border:"1px solid var(--border)",
      borderRadius:"var(--r-lg)",
      display:"flex", flexDirection:"column", gap:18,
      gridColumn: wide ? "1 / -1" : undefined,
    }}>
      <span className="mono" style={{color:"var(--node-2)", fontSize:24, lineHeight:0.5}}>“</span>
      <blockquote style={{
        margin:0, fontSize: big ? 16.5 : 14.5,
        lineHeight: 1.6, color:"var(--text-2)", textWrap:"pretty",
      }}>{body}</blockquote>
      <figcaption style={{
        marginTop:"auto", paddingTop: 14, borderTop:"1px dashed var(--border)",
        display:"flex", flexDirection:"column", gap:2,
      }}>
        <span style={{fontFamily:"var(--font-mono)", fontSize:12, color:"var(--text)"}}>{name}</span>
        <span style={{fontFamily:"var(--font-mono)", fontSize:11, color:"var(--text-muted)"}}>{role}</span>
      </figcaption>
    </figure>
  );
}

// ─────────────────────────────────────────────────────────────
// PRICING — 4 tiers
// ─────────────────────────────────────────────────────────────
function Pricing() {
  const tiers = [
    {
      name:"Free", price:"$0", unit:"/ mo",
      blurb:"For trying it on a side project.",
      feats:["1 repo","50 advisories / month","Community Slack","Public verdict log"],
      cta:"Start free",
    },
    {
      name:"Pro", price:"$29", unit:"/ repo / mo",
      blurb:"For teams already drowning in noise.",
      feats:["Unlimited advisories","LangSmith traces","Slack notifications","Deterministic replay","Email + chat support"],
      cta:"Start 14-day trial",
      highlight:true,
    },
    {
      name:"Team", price:"$79", unit:"/ repo / mo",
      blurb:"For DevSecOps platform teams.",
      feats:["Everything in Pro","Custom eval sets","SAML SSO","Audit log","Priority support"],
      cta:"Start Team",
    },
    {
      name:"Enterprise", price:"Custom", unit:"",
      blurb:"For fleet-wide deployments.",
      feats:["VPC / on-prem","SLA & DPA","Custom model routing","Dedicated reviewer","Security questionnaire support"],
      cta:"Talk to us",
    },
  ];
  return (
    <section id="pricing" style={{padding:"160px 0 150px", borderTop:"1px solid var(--border)"}}>
      <div className="container">
        <SectionHeader
          eye="§ 07 · pricing"
          h="Per repo, not per seat."
          sub="This is infrastructure. Pricing scales with the thing being protected — not the size of your team."
        />
        <div style={{display:"grid", gridTemplateColumns:"repeat(4, 1fr)", gap: 14, marginTop: 48}}>
          {tiers.map(t => (
            <div key={t.name} style={{
              position:"relative",
              padding:"26px 24px 24px",
              background: t.highlight ? "linear-gradient(180deg, rgba(99,102,241,0.10) 0%, var(--surface) 50%)" : "var(--surface)",
              border:`1px solid ${t.highlight ? "rgba(99,102,241,0.45)" : "var(--border)"}`,
              borderRadius:"var(--r-lg)",
              display:"flex", flexDirection:"column", gap: 18,
              boxShadow: t.highlight ? "0 24px 60px -30px var(--primary-glow)" : "none",
            }}>
              {t.highlight && (
                <span className="pill pill--primary" style={{
                  position:"absolute", top: -10, left: 22, fontSize:10,
                }}>
                  most teams pick this
                </span>
              )}
              <div>
                <div style={{
                  fontFamily:"var(--font-mono)", fontSize: 12,
                  color: t.highlight ? "var(--primary-2)" : "var(--text-3)",
                  letterSpacing:"0.1em", textTransform:"uppercase",
                }}>{t.name}</div>
                <div style={{marginTop: 14, display:"flex", alignItems:"baseline", gap:6, whiteSpace:"nowrap"}}>
                  <span style={{
                    fontFamily:"var(--font-mono)", fontSize: 36, fontWeight: 600,
                    letterSpacing:"-0.03em", color:"var(--text)",
                  }}>{t.price}</span>
                  <span style={{fontFamily:"var(--font-mono)", fontSize:12, color:"var(--text-muted)"}}>{t.unit}</span>
                </div>
                <div style={{marginTop: 8, fontSize:13, color:"var(--text-3)", lineHeight:1.45}}>{t.blurb}</div>
              </div>
              <ul style={{
                listStyle:"none", padding: 0, margin: 0,
                display:"flex", flexDirection:"column", gap:9,
                borderTop:"1px dashed var(--border)", paddingTop: 16,
              }}>
                {t.feats.map(f => (
                  <li key={f} style={{
                    display:"flex", gap:10, fontSize:13, color:"var(--text-2)",
                  }}>
                    <span className="mono" style={{color: t.highlight ? "var(--primary-2)" : "var(--node-4)", fontSize:12}}>›</span>
                    {f}
                  </li>
                ))}
              </ul>
              <a href="/auth/github/login?next=/Dashboard.html"
                 className={`btn ${t.highlight ? "btn--primary" : ""}`}
                 style={{marginTop:"auto", justifyContent:"center", textDecoration:"none"}}>
                {t.cta}
              </a>
            </div>
          ))}
        </div>
        <div style={{
          marginTop: 22, fontFamily:"var(--font-mono)", fontSize: 12,
          color:"var(--text-muted)", textAlign:"center",
        }}>
          $29 ≈ one engineer · two hours · one week. you do the math.
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────
// FINAL CTA
// ─────────────────────────────────────────────────────────────
function FinalCTA() {
  const [val, setVal] = useState("github.com/acme/payments-api");
  return (
    <section style={{padding:"160px 0 160px", borderTop:"1px solid var(--border)", position:"relative", overflow:"hidden"}}>
      <div aria-hidden="true" style={{
        position:"absolute", inset:0, pointerEvents:"none",
        background:"radial-gradient(circle at 50% 50%, rgba(99,102,241,0.12) 0%, transparent 55%)",
      }}/>
      <div className="container" style={{position:"relative", textAlign:"center"}}>
        <div className="eyebrow" style={{marginBottom: 18}}>§ 08 · ship it</div>
        <h2 style={{
          fontSize:"clamp(36px, 5.4vw, 60px)",
          lineHeight: 1.05, letterSpacing:"-0.025em",
          margin:"0 auto 14px", fontWeight: 600,
          maxWidth: 800, textWrap:"balance",
        }}>
          Point it at a repo. Get a real verdict in <span className="mono" style={{color:"var(--node-4)", letterSpacing:"-0.04em"}}>43 seconds.</span>
        </h2>
        <p style={{fontSize:16, color:"var(--text-3)", maxWidth:560, margin:"0 auto 30px"}}>
          Free for the first 50 advisories. No credit card. We&rsquo;ll show you what gets killed and why.
        </p>
        <form onSubmit={(e)=>{
          e.preventDefault();
          const t = (val || "").trim();
          try { if (t) sessionStorage.setItem("notsudo_scan_target", t); } catch (_) {}
          window.location.href = "Dashboard.html";
        }} style={{
          display:"flex", gap:8, maxWidth: 560, margin:"0 auto",
          padding: 6,
          background:"var(--surface)",
          border:"1px solid var(--border)",
          borderRadius: 10,
        }}>
          <span style={{
            display:"flex", alignItems:"center", paddingLeft: 12, fontFamily:"var(--font-mono)", fontSize: 13, color:"var(--text-muted)",
          }}>$</span>
          <input value={val} onChange={(e)=>setVal(e.target.value)}
                 spellCheck={false}
                 placeholder="https://github.com/org/repo"
                 style={{
                   flex:1, border:"none", outline:"none", background:"transparent",
                   fontFamily:"var(--font-mono)", fontSize: 14, color:"var(--text)",
                   padding:"10px 4px",
                 }}/>
          <button type="submit" className="btn btn--primary">
            Run advisor <span style={{opacity:0.7}}>→</span>
          </button>
        </form>
        <div style={{marginTop:16, display:"flex", justifyContent:"center", gap:12}}>
          <a href="/auth/github/login?next=/Dashboard.html" className="btn btn--ghost btn--sm"
             style={{display:"inline-flex", alignItems:"center", gap:8, textDecoration:"none"}}>
            <GithubIcon size={14} /> Sign in with GitHub
          </a>
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────
// FOOTER
// ─────────────────────────────────────────────────────────────
function Footer() {
  const cols = [
    { h: "Product", l:["Advisor","Dashboard","Slack app","CLI","Changelog"] },
    { h: "Docs",    l:["Architecture","Reachability model","Threat model","API reference","Eval suite"] },
    { h: "Company", l:["Manifesto","Security","SOC 2","Careers","Contact"] },
  ];
  return (
    <footer style={{padding:"88px 0 56px", borderTop:"1px solid var(--border)", background:"var(--bg-deep)"}}>
      <div className="container">
        <div style={{display:"grid", gridTemplateColumns:"1.4fr 1fr 1fr 1fr", gap: 32, marginBottom: 40}}>
          <div>
            <Logo size={22}/>
            <p style={{fontSize:13, color:"var(--text-3)", maxWidth: 320, marginTop: 14, lineHeight: 1.55}}>
              A reachability-aware CVE triage agent.
              Built by ex-security engineers who got tired of muting Dependabot.
            </p>
            <div style={{display:"flex", gap:8, marginTop: 18, flexWrap:"wrap"}}>
              <span className="pill pill--neutral">SOC 2 Type II (pending)</span>
              <span className="pill pill--neutral">model-agnostic</span>
            </div>
          </div>
          {cols.map(c => (
            <div key={c.h}>
              <div className="eyebrow" style={{marginBottom: 14}}>{c.h}</div>
              <ul style={{listStyle:"none", margin:0, padding:0, display:"flex", flexDirection:"column", gap:8}}>
                {c.l.map(li => (
                  <li key={li}><a href="#" style={{fontFamily:"var(--font-mono)", fontSize:13, color:"var(--text-3)"}}>{li}</a></li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div style={{
          paddingTop: 22, borderTop:"1px solid var(--border)",
          display:"flex", justifyContent:"space-between", alignItems:"center",
          fontFamily:"var(--font-mono)", fontSize:11, color:"var(--text-muted)",
        }}>
          <span>© 2026 NotSudo Labs · all rights reserved</span>
        </div>
      </div>
    </footer>
  );
}

// ─────────────────────────────────────────────────────────────
// SECTION HEADER  — shared
// ─────────────────────────────────────────────────────────────
function SectionHeader({ eye, h, sub }) {
  return (
    <div style={{maxWidth: 720}}>
      <div className="eyebrow" style={{marginBottom: 14}}>{eye}</div>
      <h2 style={{
        fontSize:"clamp(28px, 3.6vw, 42px)",
        lineHeight: 1.1, letterSpacing:"-0.02em",
        margin: "0 0 14px", fontWeight: 600,
        color:"var(--text)", textWrap:"balance",
      }} dangerouslySetInnerHTML={{__html: h}}/>
      <p style={{fontSize:16, color:"var(--text-3)", margin:0, lineHeight:1.6, textWrap:"pretty", maxWidth: 640}}
         dangerouslySetInnerHTML={{__html: sub}}/>
    </div>
  );
}

// mount
ReactDOM.createRoot(document.getElementById("root")).render(<App />);
