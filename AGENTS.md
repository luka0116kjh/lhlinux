# Working in this repository

- The desktop host uses PowerShell; the Linux runtime is the WSL distribution `lhlinux`, default user `admin`.
- From PowerShell 7.3+, run Linux commands with `./scripts/Invoke-Lhlinux.ps1 -Command @('executable', 'argument')`. Arguments are literal; pipes and shell expansion require an explicit shell. The wrapper uses the current directory and preserves the Linux exit code. Use `-Directory /home/admin/lab` for that workspace.
- Start a code-change task with `./scripts/Invoke-Lhlinux.ps1 -Command @('bash', 'scripts/lhlinux', 'workspace', '--json')`. This works from this repository before installing changed CLI files. The overview is bounded; use a focused `git diff -- path` when contents are needed.
- Use `rg --files` and scoped `rg` searches. Avoid repeatedly dumping whole directories or files. Keep personal lab files, logs and credentials out of commits.
- Run Linux tests using `./scripts/Invoke-Lhlinux.ps1 -Command @('python3', '-m', 'unittest', 'discover', '-s', 'tests', '-v')`. Shell syntax checks and PowerShell installer tests are documented in `CONTRIBUTING.md`.
- Preserve existing user changes. Installation helpers must preserve existing examples. Do not run the full installer just to update a CLI helper: it also configures services and downloads tools/models.
- Workspace summaries are read-only metadata; they do not call AI providers. Keep source/binary data separate from instructions and retain existing static-analysis-only boundaries in the AI adapters.
