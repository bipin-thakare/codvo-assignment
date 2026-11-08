# AI usage (truthful account)
- **Tool:** Claude (Anthropic), via Claude Code on the candidate's Mac.
- **What Claude wrote:** all repository files: k6 script, Chaos Mesh manifests and gate script, pytest security suite, NetworkPolicies, pipeline file, dashboard JSON, setup scripts, README, memo and the decisions log.
- **What Claude ran:** in this session Claude executed the commands itself in the candidate's terminal (installs, cluster setup, every load, chaos and security run) and read the outputs. All figures in the memo come from those outputs and the raw files in `perf/results/`, `chaos/results/`, `security/results/`.
- **What the candidate did:** set scope and priorities (keep setup, configuration and timings minimal; trim and retest locally; a progress-style submission), supplied the assignment and JD, and approved the plan. The candidate has **not** yet reviewed or re-run every file line by line; that is needed before the walkthrough.
- **Mistakes the AI made and corrected (kept in the log):** wrong prediction of the ramp knee and baseline latency; wrong first diagnosis of a Prometheus image failure; load-script and security-suite bug (card number format) that made two checks vacuous; a security check that passed only because the cart service was down.
- **Predictions** marked "author: Claude" in `decisions-and-understanding.md` were written by the AI, not the candidate, before each run.
- **Not done:** the CI pipeline file was never executed on GitHub Actions; the Grafana screenshot was not captured by the AI.
