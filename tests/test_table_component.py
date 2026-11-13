import json
from pathlib import Path
from types import SimpleNamespace
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
import smartflow.paths as paths
import smartflow.table_component as tables

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('mode', ['light', 'dark'])
def test_team_edit_add_remove_save_in_both_themes(tmp_path, monkeypatch, mode):
    monkeypatch.setattr(paths, 'ROOT', tmp_path)
    original = [{'Name': 'Sidharth P Nair', 'Registration': 'RA2311026050087', 'Contribution': ''}]
    (tmp_path / 'team.json').write_text(json.dumps(original))
    (tmp_path / 'docs').mkdir()
    for name in ('PROJECT_REPORT.md', 'DEMO_GUIDE.md'):
        (tmp_path / 'docs' / name).write_text((ROOT / 'docs' / name).read_text(encoding='utf-8'), encoding='utf-8')
    rows = [['Sidharth P Nair', 'RA2311026050087', 'Simulation review'], ['Team member', 'R2', 'Presentation']]
    payloads = []
    def edited_component(**kwargs):
        payloads.append(kwargs['data'])
        return SimpleNamespace(rows=[r.copy() for r in rows])
    monkeypatch.setattr(tables, '_grid', edited_component)
    app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=60)
    app.query_params['appearance'] = mode
    app.run()
    app.sidebar.radio[0].set_value('Project Information').run()
    assert not app.exception
    next(b for b in app.button if b.label == 'Save Team Details').click().run()
    saved = json.loads((tmp_path / 'team.json').read_text())
    assert len(saved) == 2 and saved[0]['Contribution'] == 'Simulation review'
    editor = next(p for p in reversed(payloads) if p['editable'])
    assert editor['colors']['card'] == ('#FFFFFF' if mode == 'light' else '#172238')
    rows.pop()
    app.run()
    next(b for b in app.button if b.label == 'Save Team Details').click().run()
    assert len(json.loads((tmp_path / 'team.json').read_text())) == 1
    downloads = [d.proto.label for d in app.get('download_button')]
    assert downloads == ['Download PROJECT_REPORT.md', 'Download DEMO_GUIDE.md']


def test_table_rows_validation_and_layout_clearance():
    assert tables.normalize_rows([['a', None]], ['Name', 'Contribution']).iloc[0].tolist() == ['a', '']
    with pytest.raises(ValueError):
        tables.normalize_rows([['wrong width']], ['Name', 'Contribution'])
    from smartflow.theme import theme_css
    css = theme_css('light')
    assert 'calc(3.75rem + 1.75rem)' in css
    assert 'height:2.5rem' not in css and 'padding-top:1.2rem' not in css
    assert 'max-width:1280px' in css
