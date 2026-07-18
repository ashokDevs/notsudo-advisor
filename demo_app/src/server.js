const express = require("express");
const _ = require("lodash");
const minimist = require("minimist");

const args = minimist(process.argv.slice(2));
const port = args.port || 3000;

const app = express();
app.use(express.json());

// Vulnerable: lodash.merge prototype pollution when user controls source object
app.post("/api/profile", (req, res) => {
  const base = { role: "user", prefs: { theme: "light" } };
  const merged = _.merge({}, base, req.body || {});
  res.json({ profile: merged });
});

// Vulnerable path: open redirect-style pattern (demo)
app.get("/go", (req, res) => {
  const next = req.query.next || "/";
  res.redirect(String(next));
});

app.get("/health", (_req, res) => {
  res.json({ ok: true });
});

if (require.main === module) {
  app.listen(port, () => {
    console.log(`demo app on :${port}`);
  });
}

module.exports = { app, mergeProfile: (body) => _.merge({ role: "user" }, body) };
