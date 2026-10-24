# HashCatcher — Code Review & Recommendations

## Bugs fixed in this pass

1. **`.github/workflows/release.yml` was not valid YAML.** The file contained
   the markdown write-up ("save this file as...", prose, a fenced ` ```yaml `
   block, usage instructions) instead of the workflow itself. GitHub Actions
   would have failed to parse it on the next tag push. Replaced with the
   actual YAML only.
2. **Icon file wasn't where the workflow expected it.** The workflow
   referenced `assets/hashcatcher-logo.png`, but the logo was sitting at the
   repo root as `hashcather-logo.png` (note the different spelling too) and
   wasn't in `assets/` at all. The PyInstaller `--icon` step, and the Linux
   job's `.desktop`/icon packaging step, would have failed. Moved the file
   into `assets/hashcather-logo.png` and pointed the workflow at it; the app
   itself now also uses it for the window icon and header logo.
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

## Applied in a follow-up pass

- **Redesigned the app window.** The running app previously looked nothing
  like the marketing mockup (`assets/banner.png`): a bare title bar, toolbar,
  table, progress bar and log box with no branding. Rebuilt `src/main.py`'s
  layout to match the mockup — header with the logo, "HashCatcher" title, a
  `v1.0` badge and subtitle; a left sidebar listing the app's capabilities;
  a drag-and-drop zone next to the queue table; and a footer bar showing
  supported input formats, the output format, and the "authorized use only"
  notice. Functionality (worker thread, drag & drop, conversion) is
  unchanged — this was styling/layout only, using the logo now at
  `assets/hashcather-logo.png` for both the header and the window icon.

## Applied in a second follow-up pass

Everything below this list was open in the previous revision of this
document; all of it is now done:

- **True parallelism.** `ConversionWorker` now runs up to N files
  concurrently via `concurrent.futures.ThreadPoolExecutor` (configurable
  thread count in Settings, with a Low Resource Mode that forces it to 1).
- **Persisted preferences.** hcxpcapngtool path, output directory, thread
  count and low-resource mode are all stored via `QSettings` and restored
  on launch.
- **"Open output folder" action.** Each queue row has a folder button that
  opens the output directory for that file (`QDesktopServices.openUrl`).
  There's also a Logs page (sidebar → Logs) showing the full run log.
- **Unit tests.** Added `tests/test_conversion.py` (stdlib `unittest`,
  no Qt event loop needed) covering `ConversionWorker._output_path`,
  `detect_tool_version`, and `check_hcxtools`.
- **CI now runs on every push/PR**, not just tag pushes:
  `.github/workflows/ci.yml` installs dependencies, compile-checks
  `src/main.py`, and runs the test suite.
- **`HashCatcher.spec` now sets `icon=` and bundles `assets/`** via
  `datas=[('assets', 'assets')]`, so a local `pyinstaller HashCatcher.spec`
  build has parity with the CI build and actually ships the logo — the app
  itself now also resolves `assets/` correctly whether run from source or
  from a frozen PyInstaller bundle (`sys._MEIPASS`).
- **Duplicate build tooling.** Was really just a stale README reference to
  `scripts/build_deb.sh`; `scripts/` was never tracked by git and the
  README now points at the real root-level `build_deb.sh`. Nothing left to
  consolidate.

## Remaining suggestions (not yet applied — listed for prioritization)

- **Overwrite protection.** If `<file>.22000` already exists, it's silently
  overwritten. Worth flagging in the UI (e.g. a visible "will overwrite"
  badge in the queue table) or offering a per-file choice before converting.
- **Export log to file.** The Logs page shows the run log, but there's no
  button to save it to disk for an audit trail of a pentest engagement.

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
