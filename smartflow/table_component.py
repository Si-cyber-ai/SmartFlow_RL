"""Theme-isolated, editable HTML tables using Streamlit's supported component API."""
import hashlib
import json
from pathlib import Path
import pandas as pd
import streamlit as st
from streamlit.components.v2 import component

_CSS = '''
.sf-grid{font:14px/1.5 system-ui,sans-serif;color:var(--text);background:var(--card);border:1px solid var(--border);border-radius:12px;min-width:0;max-width:100%;overflow:clip}
.toolbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:12px;background:var(--surface)}
.toolbar span{flex:1 1 160px}.toolbar input{flex:1 1 140px;min-width:80px;max-width:240px}
.sf-grid input,.sf-grid button{font:inherit;color:var(--text);background:var(--card);border:1px solid var(--border);border-radius:6px;padding:7px 10px;box-sizing:border-box}
.sf-grid button{cursor:pointer}.sf-grid button:hover{background:var(--selected)}
.sf-grid input:focus-visible,.sf-grid button:focus-visible,.table-scroll:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.table-scroll{max-height:380px;overflow:auto;max-width:100%}table{border-collapse:separate;border-spacing:0;min-width:100%;text-align:left}
th{position:sticky;top:0;background:var(--surface);color:var(--text);z-index:1;text-align:left;border-bottom:1px solid var(--border)}
th button{border:0!important;background:transparent!important;font-weight:600!important;white-space:nowrap}
td{padding:10px 12px;border-bottom:1px solid var(--border);vertical-align:top;max-width:400px;overflow-wrap:anywhere}
tr:hover td{background:var(--selected)}td input{width:100%;min-width:130px}
.add-row{margin:12px}.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}
'''
_grid = component('smartflow_table', html='<div class="sf-grid"></div>', css=_CSS,
                  js=Path(__file__).with_name('table_component.js').read_text(encoding='utf-8'))


def normalize_rows(rows, columns):
    if not isinstance(rows, list) or any(not isinstance(row, list) or len(row) != len(columns) for row in rows):
        raise ValueError('Invalid table rows')
    return pd.DataFrame(rows, columns=columns).fillna('')


def render_table(frame, mode, *, editable=False, key=None, hide_index=None, **kwargs):
    from .theme import tokens
    t = tokens(mode)
    view = frame if editable or hide_index is True else frame.reset_index()
    columns = [str(c) for c in view.columns]
    rows = json.loads(view.to_json(orient='split', date_format='iso'))['data']
    identity = key or 'table_' + hashlib.sha256(json.dumps(columns).encode()).hexdigest()[:12]
    draft_key = f'{identity}_draft'
    if editable:
        rows = st.session_state.setdefault(draft_key, rows)
    payload = dict(columns=columns, rows=rows, editable=editable, colors=dict(
        text=t['text_primary'], card=t['card'], surface=t['surface'], border=t['border'],
        accent=t['accent'], selected=t['selected_background']))
    result = _grid(key=identity, data=payload, default={'rows': rows} if editable else {},
                   on_rows_change=(lambda: None) if editable else None)
    if editable:
        edited = normalize_rows(result.rows if result.rows is not None else rows, columns)
        st.session_state[draft_key] = edited.values.tolist()
        return edited
    return result
