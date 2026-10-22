# HashCatcher — Code Review & Recommendations

## Bugs fixed in this pass

1. **`.github/workflows/release.yml` was not valid YAML.** The file contained
   the markdown write-up ("save this file as...", prose, a fenced ` ```yaml `
   block, usage instructions) instead of the workflow itself. GitHub Actions
   would have failed to parse it on the next tag push. Replaced with the
   actual YAML only.
2. **Icon filename mismatch.** The workflow referenced
   `assets/hashcatcher-logo.png`, but the file in the repo is named
   `assets/hashcather-logo.png` (note the different spelling). The
   PyInstaller `--icon` step would have failed the build. Pointed the
   workflow at the file that actually exists.
3. **Wrong line-continuation character on Windows.** The `windows-build` job
   used `^` (cmd.exe) inside a `run:` block, but GitHub's `windows-latest`
   runner executes `run:` steps in PowerShell by default, where `^` is not a
   continuation character — the multi-line `pyinstaller` invocation would
   have been parsed as a single malformed line. Switched to the PowerShell
   backtick.
4. **`hcxtools` detection was unreliable / did unnecessary work.**
   `check_hcxtools()` ran `hcxpcapngtool --help` as a subprocess just to see
   if it existed, swallowing all exceptions. Replaced with `shutil.which()`,
   which is the standard, side-effect-free way to check `PATH`.
5. **Conversion failures were logged with no detail.** `subprocess.run(...,
   check=True)` without capturing output meant a `CalledProcessError` on a
   bad/corrupt capture gave the user nothing but the exception string — no
   indication of *why* `hcxpcapngtool` rejected the file. Now captures
   `stdout`/`stderr` and logs the tool's own message.
6. **No guard against double-starting a conversion.** Clicking "Convert"
   twice (or "Clear" mid-run) spawned/reset state while a `QThread` was
   still running, which is a race. Buttons are now disabled while a batch
   runs and re-enabled via a new `finished_signal`.
7. **Missing-file crash path.** If a queued file was deleted/unmounted
   between being added and the convert click, `os.path.getsize` /
   `subprocess` would raise. Added an explicit existence check per file with
   a clear "Missing" status instead of a bare traceback in the log.
8. **Repo hygiene:** `build/`, `dist/`, `scripts/HashCatcher_1.0.0_amd64.deb`,
   and `scripts/package/` (compiled PyInstaller artifacts and a built
   `.deb`) were committed to git, and a stale `src/main.py.old` duplicate of
   the entire app was sitting in the source tree. All removed from tracking
   and a `.gitignore` added so build output, virtualenvs, and — importantly
   — captured traffic (`*.cap`/`*.pcap`/`*.pcapng`/`*.22000`) never get
   committed by accident. `requirements.txt` was referenced by the README
   but didn't exist; added it.

## Remaining suggestions (not yet applied — listed for prioritization)

- **True parallelism.** The README advertises a "Multi-threaded Engine," but
  the implementation runs one `QThread` that converts files sequentially.
  For large batches, running up to `os.cpu_count()` conversions concurrently
  (e.g. `QThreadPool` + `QRunnable`, or a `concurrent.futures.ThreadPoolExecutor`
  feeding progress back via signals) would make that claim true and speed up
  big batches.
- **Overwrite protection.** If `<file>.22000` already exists, it's silently
  overwritten. Worth flagging in the UI (e.g. "Overwrite" badge) or offering
  a per-file choice.
- **Persisted preferences.** Last-used folder, output directory, and window
  geometry aren't remembered between runs (`QSettings` is the natural fit).
- **"Open output folder" action** after a successful batch, and a **"Open
  log"/"Export log"** button for audit trails of a pentest engagement.
- **Unit tests.** There's no test suite at all. The `ConversionWorker`'s
  command-building and status logic is pure enough to test without a Qt
  event loop (mock `subprocess.run`).
- **CI currently only runs on tag push.** There's no `on: pull_request`/`push`
  job that at least `python -m py_compile`s the app and runs lint, so a
  broken `main.py` wouldn't be caught until someone tries to tag a release.
- **Window/app icon.** `assets/hashcather-logo.png` exists but
  `HashCatcher.spec` and the app itself don't set it, so the running app and
  packaged binaries show a generic icon outside of the one place
  (`--icon` in the GitHub Actions build) it's used.
- **Duplicate build tooling.** `build_deb.sh` lives at repo root while the
  README documents `scripts/build_deb.sh`, and there's a second,
  near-duplicate `scripts/package/DEBIAN/control`. Worth consolidating to one
  canonical packaging path.

## "Would Rust be a better language for this?"

Short answer: **no, not worth a rewrite** — PySide6/Python is the right fit
for what HashCatcher actually is: a thin GUI wrapper that shells out to
`hcxpcapngtool` and shows progress. None of the workload is CPU-bound inside
the app itself; the actual cracking/conversion work happens in an external
native binary either way, so Rust buys no runtime performance here.

Where Rust *would* pay off is a different kind of project — e.g. if you ever
want to:
- re-implement hash conversion logic in-process instead of shelling out,
- ship a single static binary with no Python/Qt runtime dependency to
  install, or
- build a CLI/daemon component with tighter memory/startup guarantees.

For those, a Rust core (with `egui`/`iced`/`slint`, or Tauri for a
web-view UI) is a reasonable future direction, but it's a rewrite, not an
incremental step, and the main pain points found in this review (the broken
CI YAML, no tests, build artifacts in git, no real parallelism) are
language-agnostic — they'd follow you into a Rust rewrite just as easily.
**Fix the process/structure issues first**; only reach for Rust if you later
need a standalone binary with no Python runtime, or decide to do real
cracking/parsing work in-process rather than delegating to `hcxtools`.
