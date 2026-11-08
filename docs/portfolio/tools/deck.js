// Compatibility entry point. The maintained generator produces both complete ten-slide decks.
const { spawnSync } = require("node:child_process");
const path = require("node:path");
const root = path.resolve(__dirname, "../../..");
const python = process.env.PORTFOLIO_PYTHON || path.join(root, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const result = spawnSync(python, [path.join(__dirname, "build_portfolio.py")], { cwd: root, stdio: "inherit" });
if (result.error) throw result.error;
process.exit(result.status ?? 1);
