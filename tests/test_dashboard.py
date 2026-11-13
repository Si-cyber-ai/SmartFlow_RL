from pathlib import Path
from streamlit.testing.v1 import AppTest
import smartflow.paths as paths
from smartflow.visualization import intersection_svg
from smartflow.environment import TrafficEnv


def button(app, label):
    return next(b for b in app.button if b.label == label)


def input_value(app, label, value):
    next(w for w in app.number_input if w.label == label).set_value(value)


def test_all_pages_and_critical_controls(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, 'ROOT', tmp_path)
    monkeypatch.setattr(paths, 'MODEL', tmp_path / 'model.npz')
    monkeypatch.setattr(paths, 'RESULTS', tmp_path / 'results')
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=30).run()
    assert not app.exception
    app.sidebar.radio[0].set_value('Live Traffic Simulation').run()
    button(app, 'Step Forward').click().run()
    assert app.session_state['env'].time == 1
    assert button(app, 'Start').disabled
    button(app, 'Resume').click().run()
    assert app.session_state['running']
    button(app, 'Pause').click().run()
    assert not app.session_state['running']
    button(app, 'Resume').click().run()
    assert app.session_state['running']
    button(app, 'Reset').click().run()
    assert app.session_state['env'].time == 0
    next(w for w in app.selectbox if w.label == 'Controller').set_value('Trained Q-Learning').run()
    assert any('Load or train' in w.value for w in app.warning)
    app.sidebar.radio[0].set_value('Train RL Agent').run()
    input_value(app, 'Training episodes', 2)
    input_value(app, 'Training episode seconds', 10)
    button(app, 'Start Training').click().run()
    assert not app.exception
    assert app.session_state['agent'].trained
    assert app.session_state['agent'].updates == 20
    button(app, 'Save Model').click().run()
    button(app, 'Load Saved Model').click().run()
    assert not app.exception
    button(app, 'Reset Training Configuration').click().run()
    assert app.session_state['train_episodes'] == 1000
    app.sidebar.radio[0].set_value('Live Traffic Simulation').run()
    next(w for w in app.selectbox if w.label == 'Controller').set_value('Trained Q-Learning').run()
    button(app, 'Step Forward').click().run()
    assert app.session_state['env'].time == 1
    assert not app.exception
    app.sidebar.radio[0].set_value('Performance Comparison').run()
    input_value(app, 'Evaluation seeds per scenario', 1)
    input_value(app, 'Evaluation seconds', 30)
    button(app, 'Run Comparison').click().run()
    assert not app.exception
    assert (tmp_path / 'results' / 'evaluation_results.csv').exists()
    for page in ['Learning Analytics', 'RL Explanation', 'Project Information', 'Overview']:
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception, page
        if page == 'Project Information':
            button(app, 'Save Team Details').click().run()
            assert (tmp_path / 'team.json').exists()


def test_render_matches_queues():
    env = TrafficEnv()
    for _ in range(20):
        env.step(0)
    svg = intersection_svg(env.get_render_data())
    assert svg.count('<title>Vehicle ') == env.get_metrics()['remaining']


def test_live_presets_comparison_and_state_preservation():
    import numpy as np
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=30).run()
    button(app, 'Load Saved Model').click().run()
    assert app.session_state['agent'].trained
    original = app.session_state['agent'].q_table.copy()
    app.sidebar.radio[0].set_value('Live Traffic Simulation').run()
    assert button(app, 'Pause').disabled and button(app, 'Resume').disabled
    button(app, 'Start').click().run()
    assert app.session_state['running'] and button(app, 'Start').disabled
    assert button(app, 'Step Forward').disabled
    button(app, 'Pause').click().run()
    paused_time = app.session_state['env'].time
    assert button(app, 'Pause').disabled and not button(app, 'Resume').disabled
    app.run()
    assert app.session_state['env'].time == paused_time
    next(w for w in app.select_slider if w.label == 'Simulation speed (steps / second)').set_value(8).run()
    assert app.session_state['env'].time == paused_time
    assert len(app.session_state['live_log']) == paused_time + 1
    chart = next(w for w in app.get('plotly_chart') if w.proto.id.endswith('-live_queue_chart'))
    import json
    assert len(json.loads(chart.proto.spec)['data']) == 4
    next(w for w in app.toggle if w.label == 'Synchronized comparison').set_value(True).run()
    button(app, 'Step Forward').click().run()
    live = app.session_state['live_simulation']
    assert live.paired and {e.time for e in live.envs.values()} == {1}
    np.testing.assert_array_equal(live.envs['Fixed-Time'].trace, live.envs['Trained Q-Learning'].trace)
    app.sidebar.selectbox[0].set_value('Heavy').run()
    assert app.session_state['env'].time == 0
    assert any('Overloaded demand' in w.value for w in app.warning)
    button(app, 'Step Forward').click().run()
    app.sidebar.radio[0].set_value('Overview').run()
    app.sidebar.radio[0].set_value('Live Traffic Simulation').run()
    assert app.session_state['env'].time == 1
    np.testing.assert_array_equal(original, app.session_state['agent'].q_table)
