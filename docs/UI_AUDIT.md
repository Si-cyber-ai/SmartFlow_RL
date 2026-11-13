# Source audit and UI repair

The seven pages live in `app.py`, with the live view in `dashboard_live.py`;
there were no separate seven page modules to rebuild. Inspection covered these
files, theme CSS, SVG/iframe rendering, chart exports, navigation/session state,
table wrappers, requirements and `.streamlit/config.toml` (Streamlit 1.55.0).

## Root causes and corrections

| Source finding | Correction |
|---|---|
| Global content padding was 1.2rem while the fixed header was forced to 2.5rem; native toolbar geometry was not respected. A mobile rule used another unrelated offset. | Removed forced header height and inconsistent generic padding. Main content now reserves the native 3.75rem toolbar plus a 1.75rem page gap. Sidebar padding is separate. |
| A style-only Markdown element could introduce an empty layout block/gap. | CSS uses supported `st.html`, which handles style-only content without a content-space block. |
| Overview lacked a normal page title; live used a smaller heading than other pages. | `layout.page_header` supplies the same brand, title, anchor and short description to every page. Removed duplicate page headings. |
| Native canvas/editor header and editable cells do not consume Pandas Styler colors. | Replaced app table wrappers with one supported v2 bidirectional component. It controls the whole table surface, including editable inputs and headers, using centralized tokens. No parent DOM access or private production API. |
| Per-chart margins as small as 5–10px left little room for tick/axis labels and legends. | Shared Plotly helper enforces axis automatic margins, common outer margins and consistent horizontal legends; keeps explicit font/background colors and `theme=None`. |
| Phase text used a float, and narrow button/card columns could compete for width. | Phase strip uses wrapping flex layout. Main content is capped at 1280px, with fluid horizontal padding and wrapping columns below 1100/700px. |
| Obsolete native-grid style rules remained after migration. | Removed the unused Styler helper and canvas/table CSS overrides. Component CSS is isolated in its own shadow root. |

Clipping fixes are source-verified, not screenshot-verified. No negative top margin,
layout transform or parent-window JavaScript scroll workaround was introduced.
Absolute positioning is confined to intentional screen-reader-only labels. Table
overflow is local, preserving the complete page and chart layout. The existing SVG
iframe remains bounded intentionally and retains its original geometry.

## Tables and team editing

The table component uses Streamlit's documented v2 `component`, `data`,
`setStateValue` and `on_rows_change` interfaces. See the
[official component API](https://docs.streamlit.io/develop/api-reference/custom-components/st.components.v2.component).
Streamlit minimum requirement is now 1.55, matching the installed/tested version.
No external JS library or new Python dependency is added.

Native HTML inputs preserve team editing; add/remove controls publish draft rows
to session state. Theme/navigation reruns retain that draft. Save Team Details
keeps the same JSON format. Empty teams retain their column schema. Read-only
tables keep filtering, numeric sorting and CSV export; negative values remain
negative, and CSV exports retain original values rather than display rounding.
Data is inserted with `textContent` / input values rather than interpreted HTML.

## Verification boundaries

AppTest checks Python rendering, headings, navigation, both themes, state and save
paths. Streamlit 1.55 AppTest mocks its v2 registry, so tests install a real v2
registry in the test harness; production rendering is not bypassed. Edit/save
integration tests inject frontend return values and write only into temporary
team files. Separately, Node executes the actual frontend module against a small
DOM harness for editing, add/remove, sorting, filtering and lossless CSV behavior.
That harness does **not** measure pixels, execute a full browser or take screenshots.
Node is optional for this extra developer check, not required to run the app.

Browser automation remains unavailable. The requested 14 screenshots were **not**
captured. Native header/scroll behavior and visual layout require the checks below.

## Manual browser checklist

At **1366×768**, **1440×900** and **1920×1080**, and at a narrower width:

- Open/refresh every page in both themes, then repeat after scrolling down another page.
- Confirm branding and the complete page heading clear the toolbar without excess blank space.
- Check the page-title jump link, sidebar heading and circular current-mode icon.
- Check for page-level horizontal scrolling, overlapping cards, clipped charts or hidden controls.
- Verify axes, legends, negative rewards/improvements, hover labels, formulas and alerts.
- In each theme, edit a team cell, add/remove a row, save and reopen; verify JSON persists.
- Check editable table headers, focus/hover colors, filtering, numeric sort and CSV download.
- Run RL playback and change theme; ensure clock, queues, model and controller are preserved.
- Download the project report and demo guide; only those two document downloads remain.
- Inspect browser console for new errors.

Capture and inspect these 14 screenshots; boxes are intentionally unverified:

| Page | Light | Dark |
|---|---|---|
| Overview | [ ] | [ ] |
| Live Traffic Simulation | [ ] | [ ] |
| Train RL Agent | [ ] | [ ] |
| Learning Analytics | [ ] | [ ] |
| Performance Comparison | [ ] | [ ] |
| RL Explanation | [ ] | [ ] |
| Project Information | [ ] | [ ] |
