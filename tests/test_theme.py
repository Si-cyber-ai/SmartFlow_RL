from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET
import json
import numpy as np
import plotly.graph_objects as go
import pytest
from streamlit.testing.v1 import AppTest
from smartflow.environment import TrafficEnv
from smartflow.theme import THEMES, tokens, initialize_theme, toggle_appearance, theme_css, style_figure
from smartflow.visualization import intersection_svg

ROOT = Path(__file__).resolve().parents[1]


def test_theme_tokens_styles_and_persistence():
    required = {'background', 'surface', 'sidebar', 'text_primary', 'text_secondary', 'border', 'accent',
                'chart_background', 'chart_text', 'road_color', 'road_markings'}
    for mode in THEMES:
        assert required <= tokens(mode).keys()
        assert tokens(mode)['background'] in theme_css(mode)
    assert tokens('light')['road_color'] == tokens('dark')['road_color']
    with pytest.raises(ValueError):
        tokens('unknown')
    state, query = {}, {}
    assert initialize_theme(state, query) == 'dark'
    state.update(appearance='☀️ Light Mode', page='Live Traffic Simulation', marker=99)
    toggle_appearance(state, query)
    assert state['theme_mode'] == query['appearance'] == 'light' and state['theme_redraw_only']
    assert state['marker'] == 99
    assert initialize_theme({}, query) == 'light'
    assert initialize_theme({}, {'appearance': 'invalid'}) == 'dark'


def test_chart_and_intersection_theme_preserve_data():
    fig = go.Figure(go.Scatter(x=[0, 1], y=[4, 2]))
    data_before = fig.to_json()
    style_figure(fig, 'light')
    assert fig.layout.font.color == tokens('light')['chart_text']
    assert json.loads(data_before)['data'][0]['x'] == json.loads(fig.to_json())['data'][0]['x']
    assert json.loads(data_before)['data'][0]['y'] == json.loads(fig.to_json())['data'][0]['y']
    env = TrafficEnv()
    for _ in range(10):
        env.step(0)
    data = env.get_render_data()
    ns = {'s': 'http://www.w3.org/2000/svg'}
    trees = [ET.fromstring(intersection_svg(data, theme=mode)) for mode in ('dark', 'light')]
    groups = [[g.attrib for g in tree.findall('.//s:g[@class="queued-vehicle"]', ns)] for tree in trees]
    assert groups[0] == groups[1]
    for mode, tree in zip(('dark', 'light'), trees):
        assert tree.find('s:rect', ns).attrib['fill'] == tokens(mode)['scene_background']


def test_all_seven_pages_in_both_themes_and_refresh():
    app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=60).run()
    assert app.session_state['theme_mode'] == 'dark'
    next(b for b in app.button if b.label == 'Load Saved Model').click().run()
    agent = app.session_state['agent']
    q = agent.q_table.copy()
    pages = ['Overview', 'Live Traffic Simulation', 'Train RL Agent', 'Learning Analytics',
             'Performance Comparison', 'RL Explanation', 'Project Information']
    for label, mode in [('☀️ Light Mode', 'light'), ('🌙 Dark Mode', 'dark')]:
        app.button(key='appearance_toggle').click().run()
        assert not app.exception
        assert app.session_state['theme_mode'] == mode
        assert not app.get('button_group')
        toggle = app.button(key='appearance_toggle')
        expected_action = 'Switch to Dark Mode' if mode == 'light' else 'Switch to Light Mode'
        assert toggle.label == toggle.proto.help == expected_action
        assert toggle.proto.icon == ('☀️' if mode == 'light' else '🌙')
        for page in pages:
            app.sidebar.radio[0].set_value(page).run()
            assert not app.exception, (mode, page)
            from smartflow.layout import PAGE_DETAILS
            assert app.header[0].value == PAGE_DETAILS[page][0]
            assert app.session_state['theme_mode'] == mode
            assert len([b for b in app.button if b.key == 'appearance_toggle']) == 1
            for chart in app.get('plotly_chart'):
                layout = json.loads(chart.proto.spec)['layout']
                assert layout['font']['color'] == tokens(mode)['chart_text']
                assert layout['xaxis']['tickfont']['color'] == tokens(mode)['chart_ticks']
                assert layout['yaxis']['title']['font']['color'] == tokens(mode)['chart_axis_title']
                assert chart.proto.theme == ''
    assert app.session_state['agent'] is agent
    np.testing.assert_array_equal(q, agent.q_table)
    refreshed = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=60)
    refreshed.query_params['appearance'] = 'light'
    refreshed.run()
    assert refreshed.session_state['theme_mode'] == 'light' and not refreshed.exception


def test_theme_switch_does_not_advance_or_reset_running_simulation():
    app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=60).run()
    next(b for b in app.button if b.label == 'Load Saved Model').click().run()
    app.sidebar.radio[0].set_value('Live Traffic Simulation').run()
    next(w for w in app.selectbox if w.label == 'Controller').set_value('Trained Q-Learning').run()
    next(b for b in app.button if b.label == 'Start').click().run()
    live, agent = app.session_state['live_simulation'], app.session_state['agent']
    original_q = agent.q_table.copy()
    metrics = deepcopy(live.env.get_metrics())
    queues = deepcopy(live.env.get_render_data())
    history = deepcopy(list(live.histories[live.controller]))
    identity = app.session_state['live_identity']
    for label in ['☀️ Light Mode', '🌙 Dark Mode', '☀️ Light Mode']:
        app.session_state['live_next_tick'] = 0.  # A normal due rerun would advance.
        app.button(key='appearance_toggle').click().run()
        assert not app.exception
        assert app.session_state['live_simulation'] is live
        assert app.session_state['live_identity'] == identity
        assert app.session_state['running'] and live.status == 'running'
        assert live.env.get_metrics() == metrics
        assert live.env.get_render_data() == queues
        assert list(live.histories[live.controller]) == history
        assert app.session_state['agent'] is agent
    np.testing.assert_array_equal(original_q, agent.q_table)


@pytest.mark.parametrize('mode', ['light', 'dark'])
def test_explicit_plotly_contrast_secondary_axes_and_annotations(mode):
    from plotly.subplots import make_subplots
    fig = make_subplots(specs=[[{'secondary_y': True}]])
    fig.add_trace(go.Scatter(x=[1, 2], y=[3, 4], text=['a', 'b'], textfont_color='white'), secondary_y=False)
    fig.add_trace(go.Bar(x=[1, 2], y=[9, 8], name='Throughput'), secondary_y=True)
    fig.update_layout(title=dict(text='Measured reward', font_color='white'),
                      legend_font_color='white', xaxis_tickfont_color='white',
                      yaxis2_title=dict(text='Secondary metric', font_color='white'))
    fig.add_annotation(x=1, y=3, text='Actual observation', font_color='white')
    fig.add_shape(type='line', x0=1, x1=2, y0=3, y1=3, line_color='red')
    fig.update_layout(coloraxis=dict(colorbar=dict(title=dict(text='Value', font_color='white'), tickfont_color='white')))
    style_figure(fig, mode)
    t = tokens(mode)
    assert fig.layout.title.font.color == t['chart_text']
    for axis in (fig.layout.xaxis, fig.layout.yaxis, fig.layout.yaxis2):
        assert axis.tickfont.color == t['chart_ticks']
        assert axis.title.font.color == t['chart_axis_title']
        assert axis.gridcolor == t['chart_grid'] and axis.zerolinecolor == t['chart_zero']
    assert fig.layout.legend.font.color == t['chart_legend']
    assert fig.layout.annotations[0].font.color == t['chart_annotation']
    assert fig.layout.hoverlabel.bgcolor == t['chart_hover']
    assert fig.layout.modebar.color == t['chart_ticks']
    assert fig.layout.coloraxis.colorbar.tickfont.color == t['chart_ticks']
    assert fig.data[0].textfont.color == t['chart_text']
    assert fig.layout.shapes[0].line.color == 'red'
    assert tuple(fig.data[0].y) == (3, 4)


def test_normal_text_palette_contrast():
    def luminance(color):
        rgb = [int(color[i:i+2], 16)/255 for i in (1, 3, 5)]
        linear = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in rgb]
        return sum(v*w for v, w in zip(linear, (.2126, .7152, .0722)))
    def contrast(a, b):
        light, dark = sorted([luminance(a), luminance(b)], reverse=True)
        return (light+.05)/(dark+.05)
    for mode in THEMES:
        t = tokens(mode)
        for text in ('chart_text', 'chart_axis_title', 'chart_ticks', 'chart_legend', 'chart_annotation'):
            assert contrast(t[text], t['chart_background']) >= 4.5
        for text in ('text_primary', 'text_secondary', 'secondary_text'):
            assert contrast(t[text], t['surface']) >= 4.5
        for surface in ('background', 'surface', 'sidebar', 'card'):
            assert contrast(t['link_text'], t[surface]) >= 4.5
        assert contrast(t['background'], t['button_accent']) >= 4.5
        assert contrast(t['secondary_text'], t['selected_background']) >= 4.5
