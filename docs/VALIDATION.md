# Validation and remaining manual checks

## Current UI audit revision

The previous native-grid fallback limitation in the historical notes below is
superseded: current tables use a supported, fully palette-controlled v2 component
with editable team cells, add/remove, filter, numeric sort and CSV export. The
native canvas widget is no longer the application's table renderer.
Source findings, corrections and the 14-screenshot checklist are in [UI_AUDIT.md](UI_AUDIT.md).
Current checks: `python -m pytest -q` **38 passed in 16.33s, exit 0**;
`node tests/table_component_test.mjs` passed all frontend behavior checks;
compilation passed; Streamlit started and health returned `ok`. All 15 protected
core/model/result hashes remain unchanged. Existing host temp cleanup warnings
still appear after successful test exit. No screenshot or pixel-level browser
verification is claimed. Browser/console/viewport/scroll checks remain manual.

## Contrast repair and single icon toggle

Completion follow-up: fixed normal-size link contrast in Light Mode and the
brand separator. Expanded tests verify the exact current-theme sun/moon icon,
exactly one theme button on every page, and link/button text contrast. Latest
full suite: **35 passed, 14 dependency warnings, 16.00 seconds, exit 0**.
Compilation passed and all 15 protected-file hashes remain unchanged. Browser
tool discovery still found no browser automation; Playwright/Selenium are absent.

Final `python -m pytest -q`: **35 passed, 14 dependency deprecation warnings,
17.74 seconds, exit 0**. Targeted theme tests: **7 passed**. Tests exercise every
page in both modes, native button actions/tooltips, repeated running-playback
switches without time advancement, and URL restoration. New cases override
previous white chart fonts and verify explicit colors on primary/secondary axes,
titles, ticks, legends, annotations, per-trace text, colorbars, hover boxes and
modebars. Chart data and semantic shape colors are preserved. Palette tests
verify normal chart and key UI text contrast of at least 4.5:1.

The former segmented selector is replaced by one 38px circular native Streamlit
button next to Control center. The current-mode icon is visible; the action label
is visually clipped while remaining available to assistive technology. All chart
calls explicitly use `theme=None` to prevent Streamlit's chart overlay from
conflicting with the application palette.

Compilation passed, Streamlit started on port 8501, and HTTP health returned `ok`.
All 15 protected core/model/experiment hashes remain unchanged. No Git operations,
model training or new dependencies. Existing host cleanup and installed-library
deprecation warnings remain separate from the passing assertions.

Browser automation is unavailable: visual verification is **not** claimed. In a
real browser at laptop resolution, inspect every chart's tick labels, titles,
legends, annotations, hover labels and toolbar in both modes. Check the circular
icon appearance, hover tooltip, Tab focus, keyboard activation and screen-reader
action name; inspect menus, radio selection, alerts, formulas, and native grid/editor
surfaces. The native grid/editor fallback-theme limitation described below remains.

## Light/Dark Appearance switcher

Final `python -m pytest -q`: **32 passed, 14 dependency deprecation warnings,
39.01 seconds, exit 0**. Four new theme tests check semantic tokens, URL preference
restoration, chart data preservation, SVG geometry/IDs, all seven pages in both
modes, loaded-model retention and repeated theme switching during running RL
playback. The running test deliberately makes the next tick overdue, then verifies
the theme redraw does not advance the clock, queues, decisions, rewards or history.
Subsequent timed fragments can continue playback normally. All 28 existing tests
also pass. Protected-file hash checks confirm all 15 simulator/RL/model/experiment
files are unchanged. No Git operations, new dependencies or retraining were used.

`python -m compileall -q app.py smartflow` passed. Streamlit started on port 8501
and its health endpoint returned `ok`. An initial standalone AppTest probe used
its three-second default timeout and timed out; rerunning with an explicit
30-second timeout succeeded. Theme tests allow 60 seconds. The host's existing
temporary-directory cleanup PermissionError still appears after successful exit.

The theme control uses supported session state, a native button and query
parameters. CSS, Plotly and SVG colors are centralized in `smartflow/theme.py`.
Installed Streamlit 1.55 source and official docs confirm that runtime
`st.set_option('theme.*', ...)` is unsupported; no private configuration API is used.
Pandas Styler colors native read-only grid cells where supported. Native grid
headers and editable-cell chrome still use Streamlit's configured fallback theme,
so full native-grid recoloring is a known limitation of this app-level switcher.

Browser automation remains unavailable. Manual checklist:

- Switch Appearance several times on each of the seven pages.
- Check headings, captions, formulas, code, menus, alerts and disabled controls.
- Inspect chart axes, hover labels, grid lines and series in both modes.
- Inspect table headers, editable team cells and dropdown popup contrast; native
  canvas/editor surfaces may retain the configured Streamlit fallback colors.
- Start RL playback, toggle modes, then verify smooth continuation without reset.
- Verify light surroundings, dark roads, readable queue counters and distinct signals.
- Refresh the URL and confirm the chosen appearance is restored.
- Confirm the report/demo downloads remain and the removed document is absent.

## Interactive dashboard enhancement

The enhancement preserves all 15 protected core/model/result files byte-for-byte,
verified against `dashboard_preservation_hashes.json`. It does not retrain, update
the Q-table, change rewards or alter evaluation logic. No Git commands were run.

Final `python -m pytest -q`: **28 passed in 9.58 seconds, exit 0**. This includes
all 10 environment tests, model loading, exact decision values and truthful
tie/constraint explanations, synchronized traces and times, bounded four-road
histories, pause/resume/reset/completion, current queue IDs and departure IDs in
animated SVG, static-render behavior and signal snapshots. AppTest covers
disabled controls, live chart series, changing speed while paused, paired mode,
Heavy overload warning, scenario resets and state preservation across navigation.
Existing training/save/evaluation tests use temporary isolated outputs.

`python -m compileall -q app.py smartflow` passed. Streamlit started successfully
on port 8501 and `/_stcore/health` returned `ok`. The verification server was stopped
after checks. The pre-existing host temporary-directory cleanup warning still
occurs after successful pytest exit; it does not indicate a failed assertion.

No browser automation tools, Playwright or Selenium were available. Python-side
AppTest and SVG XML checks do not verify actual browser rendering or SVG animation.
Manually verify interpolation smoothness, paused snapshots, 1×–8× playback,
side-by-side readability and the 65%/35% layout on the presentation laptop.
Animated departure ghosts belong to the previous service interval; lamps show
the current snapshot. Check that this explanatory label is visible in the browser.

## Executed checks

Development machine: Windows, Python 3.13.2, CPU-only. Original Stage 1 sources
were preserved. Git writes were denied and subsequently waived by the user.

| Command / check | Actual outcome |
|---|---|
| Stage 1 `python -m pytest -q` | 10 passed |
| Stage 2 `python -m pytest -q` | 14 passed |
| Stage 3 `python -m pytest -q` | 18 passed |
| Stage 4 `python -m pytest -q` | 20 passed |
| Final `python -m pytest -q` | 22 passed, exit 0; host cleanup warning noted below |
| `python train.py --episodes 1000 --seed 42` | Completed; 300,000 updates, 3,720 nonzero entries |
| `python evaluate.py --episodes 20` | Completed; six scenarios × 20 seeds × two controllers |
| `python -m pip install --no-index -r requirements.txt` | Existing dependencies satisfied |
| `python -m streamlit run app.py --server.headless true --server.port 8501` | Server started |
| HTTP `http://localhost:8501/_stcore/health` | `ok` |
| `python -m compileall -q smartflow app.py train.py evaluate.py` | Passed |
| `python train.py --help` / `python evaluate.py --help` | Both passed; documented arguments supported |

`tests/test_environment.py` verifies reset, seed reproducibility, FIFO, waiting,
reward, clearance, duration enforcement, conservation, horizon and signal safety.
Agent tests verify state encoding, exploration, masking, numerical targets,
terminal/truncated behavior, decay, changed Q-values and persistence.
Training tests check deterministic histories, model outputs and interruption
checkpoints. Evaluation tests check identical trace hashes and counts, metric math,
seed separation, reproducibility and model/history non-mutation. AppTest loads all
seven pages and exercises simulation controls, missing model handling, training,
model save/load and comparison; SVG vehicle counts match queues.

## Host restrictions encountered

The host denies pytest private-mode cache/temp directories. Tests are restricted
to `tests/`, disable cache/tmpdir plugins, and use ordinary workspace test-artifact
directories. The host also produced a Streamlit-internal temporary-directory cleanup
PermissionError at process exit even when all assertions passed and exit status was
zero. Existing pip `~andas` metadata warnings do not prevent Pandas imports.
These are recorded rather than hidden. A fresh virtual environment is recommended.

No clean-machine dependency download/install was performed; the no-index check
confirmed this machine's installed versions satisfy requirements. No Git permission
retries were made after the user removed the commit requirement.

## Browser checks still required

- Check laptop layout, typography, SVG sizing and labels at the intended screen size.
- Confirm timed Start/Pause/Resume playback and speed changes in an active browser.
- Confirm timer stops at the horizon and scenario/controller/configuration changes
  start a fresh episode without losing the trained model.
- Download history/evaluation CSVs and all report files using the browser.
- Edit additional team rows, save and reopen; verify names and real contributions.
- Check long-queue schematic readability and yellow/all-red appearance.
- Rehearse the five-minute script and saved-artifact fallback.

AppTest validates Python-side widget actions but does not assess browser rendering,
downloaded browser files or wall-clock animation. No screenshot or smooth vehicle
trajectory animation is claimed.
