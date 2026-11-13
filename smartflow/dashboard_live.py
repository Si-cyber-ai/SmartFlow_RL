"""Streamlit presentation for the existing simulator and trained policy."""
from dataclasses import replace
import time
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
from .live_simulation import LiveSimulation, SCENARIO_LABELS, ROAD_NAMES, ACTION_NAMES, scenario_rates, policy_snapshot
from .visualization import intersection_document
from .theme import queue_colors, style_figure, themed_dataframe

def phase_panel(env):
    data, config = env.get_render_data(), env.config
    active = 'North–South' if data['phase'] == 0 else 'East–West'
    target = 'North–South' if data['target'] == 0 else 'East–West'
    if data['status'] == 'green':
        text = f'{active} GREEN · {data["elapsed"]} s elapsed'
        value = min(data['elapsed'] / config.max_green, 1.)
    else:
        text = f'{data["status"].upper()} · no green · target {target} · {data["remaining"]} s clearance left'
        value = 1 - data['remaining'] / (config.yellow + config.all_red)
    st.markdown(f'<div class="phase-strip">{text}<span>{env.time:03d} / {config.duration} s</span></div>', unsafe_allow_html=True)
    st.progress(value)
    st.caption(f'Green bounds {config.min_green}–{config.max_green} s · Yellow {config.yellow} s · All-red {config.all_red} s. '
               'The green bar shows elapsed / maximum green; it does not predict an AI switch.')


def decision_monitor(live, controller):
    env = live.envs[controller]
    st.markdown('#### AI decision monitor' if controller == 'Trained Q-Learning' else '#### Fixed-time decision monitor')
    current = policy_snapshot(env, controller, live.agent, live.fixed_green)
    complete = live.status == 'complete'
    st.caption(f'Current state at t={env.time}s · ' + ('episode ended; no next action' if complete else 'next legal decision preview'))
    state_label = f'Encoded state {current["encoded"]}' if current['encoded'] is not None else 'Fixed-time control · Q-values not used'
    st.markdown(f'**{state_label}**')
    st.code(str(current['state']), language=None)
    st.caption(' · '.join(f'{d}: {n}' for d, n in current['queues'].items()) +
               f' · phase {"NS" if current["phase"] == 0 else "EW"} · green elapsed {current["elapsed"]} s')
    cards = []
    for action in (0, 1):
        legal = action in current['valid']
        selected = action == current['action'] and not complete
        q = f'Q {current["q_values"][action]:.4f}' if action in current['q_values'] else ('No Q-value used' if legal else 'Masked')
        cards.append(f'<div class="decision-action {"selected" if selected else ""} {"masked" if not legal else ""}">'
                     f'<b>{"● " if selected else ""}{ACTION_NAMES[action]}</b><br><small>{q}</small></div>')
    st.markdown('<div class="decision-actions">' + ''.join(cards) + '</div>', unsafe_allow_html=True)
    if not complete:
        st.caption(current['explanation'])
    last = live.decisions.get(controller)
    if last:
        st.markdown(f'**Last executed: {ACTION_NAMES[last["applied_action"]]}** · t={last["time"]} → {last["time"]+1}s · reward **{last["reward"]:.2f}**')
        with st.expander('Inspect last executed state and Q-values'):
            st.json({k: last[k] for k in ('time', 'state', 'encoded', 'queues', 'phase', 'elapsed', 'valid', 'q_values', 'action', 'applied_action', 'reward')})
    else:
        st.caption('No action executed yet · latest reward —')


def queue_chart(live):
    history = pd.DataFrame(live.histories[live.controller])
    fig = px.line(history, x='time', y=list(ROAD_NAMES.values()),
                  color_discrete_map=queue_colors(st.session_state.get('theme_mode', 'dark')), labels={'time': 'Simulation time (s)', 'value': 'Waiting vehicles', 'variable': 'Approach'})
    fig.update_layout(height=225, margin=dict(t=10, b=5, l=5, r=5),
                      legend=dict(orientation='h', y=1.18, title=None), hovermode='x unified',
                      uirevision=f'{live.seed}-{live.scenario}')
    fig.update_yaxes(rangemode='tozero')
    st.plotly_chart(style_figure(fig, st.session_state.get('theme_mode', 'dark')), width='stretch', theme=None, key='live_queue_chart', config={'displaylogo': False})
    st.caption(f'Real per-approach queues · latest {live.histories[live.controller].maxlen} snapshots maximum.')


def render_live_page(config, scenario, seed, fixed_green):
    ss = st.session_state
    settings = st.columns([2, 2, 3])
    options = ['Fixed-Time', 'Trained Q-Learning']
    controller = settings[0].selectbox('Controller', options, index=options.index(ss.get('selected_live_controller', options[0])))
    ss.selected_live_controller = controller
    paired = settings[1].toggle('Synchronized comparison', value=ss.get('selected_live_paired', False))
    ss.selected_live_paired = paired
    with settings[2]:
        rates = scenario_rates(scenario, ss.env.time if 'env' in ss and ss.get('live_scenario') == scenario else 0, config.duration)
        st.caption(f'{SCENARIO_LABELS[scenario]} · seed {seed}')
        st.caption(f'{config.duration} seconds · live queue-based traffic control')
    requires_model = paired or controller == 'Trained Q-Learning'
    ready = not requires_model or (ss.agent is not None and ss.agent.trained)
    effective = replace(ss.agent.env_config, duration=config.duration) if requires_model and ready else config
    if not ready:
        st.warning('Load or train a model before using Q-Learning. Comparison also requires a trained model.')
    if requires_model and ready and effective != config:
        st.caption('Using the loaded model’s signal and service settings for compatible inference and a fair comparison.')
    if sum(rates.values()) > 2 * effective.service_rate:
        st.warning(f'Overloaded demand: {sum(rates.values()):.2f} arrivals/s exceeds even ideal capacity '
                   f'{2*effective.service_rate:.2f} vehicles/s before clearance losses. Neither controller can eliminate this congestion.')
    if scenario == 'Dynamic':
        st.caption(f'Dynamic schedule: N/S 0.48, E/W 0.12 veh/s before t={effective.duration//2}s; rates reverse afterward.')

    identity = (scenario, effective, seed, controller, fixed_green, paired, id(ss.agent) if requires_model and ready else None, ready)
    if ss.get('live_identity') != identity:
        changed = 'live_identity' in ss
        # A missing model displays an idle fixed-time scene, with all run controls disabled.
        live = LiveSimulation(effective, scenario, seed, controller if ready else 'Fixed-Time',
                              ss.agent if ready else None, fixed_green, paired and ready)
        ss.live_simulation = live
        ss.live_identity, ss.live_scenario = identity, scenario
        ss.running, ss.live_drawn_time, ss.live_next_tick = False, 0, 0.
        if changed:
            st.info(f'New playback initialized: {SCENARIO_LABELS[scenario]} · {controller} · t=0 s. Configuration changes reset the live episode.')
    live = ss.live_simulation
    ss.env = live.env

    def command(name):
        getattr(live, name)()
        ss.running = live.status == 'running'
        if name in ('reset', 'start', 'resume'):
            ss.live_next_tick = 0.
        if name == 'reset':
            ss.live_drawn_time = 0

    bar = st.columns([1, 1, 1, 1, 1.4, 2.2])
    bar[0].button('Start', on_click=command, args=('start',), disabled=not ready or live.status not in ('idle', 'complete'), type='primary', width='stretch')
    bar[1].button('Pause', on_click=command, args=('pause',), disabled=live.status != 'running', width='stretch')
    bar[2].button('Resume', on_click=command, args=('resume',), disabled=not ready or live.status != 'paused', width='stretch')
    bar[3].button('Reset', on_click=command, args=('reset',), disabled=live.status == 'idle', width='stretch')
    bar[4].button('Step Forward', on_click=command, args=('step',), disabled=not ready or live.status in ('running', 'complete'), width='stretch')
    speed = bar[5].select_slider('Simulation speed (steps / second)', options=[1, 2, 4, 8], value=ss.get('selected_live_speed', 2), label_visibility='collapsed')
    ss.selected_live_speed = speed
    st.caption(f'{live.status.upper()} · {speed}× speed · ' + ('Matched trace playback; both controllers advance together.' if live.paired else 'Inference only; the saved Q-table is unchanged.'))
    animate_enabled = ss.get('animate_live', True)

    @st.fragment(run_every=1/speed if live.status == 'running' else None)
    def frame():
        before = live.status
        redraw_only = ss.pop('theme_redraw_only', False)
        if not redraw_only and live.status == 'running' and time.monotonic() >= ss.live_next_tick:
            live.step()
            ss.live_next_tick = time.monotonic() + 1/speed
        ss.running = live.status == 'running'
        ss.env = live.env
        ss.live_log = list(live.histories[live.controller])
        fresh = live.env.time > ss.live_drawn_time
        motion = animate_enabled and fresh
        current_rates = scenario_rates(scenario, live.env.time, effective.duration)
        st.caption('ACTUAL ARRIVAL RATES · ' + ' / '.join(f'{d} {rate:.2f}' for d, rate in current_rates.items()) + ' vehicles/s (Poisson means)')
        if live.paired:
            st.caption('Vehicle interpolation shows the completed service interval; signal lamps show the current snapshot.')
            for col, name in zip(st.columns(2), live.controllers):
                with col:
                    st.markdown(f'**{name}**')
                    phase_panel(live.envs[name])
                    components.html(intersection_document(live.envs[name].get_render_data(), live.previous.get(name), motion, .85/speed, theme=ss.get('theme_mode', 'dark')), height=360, scrolling=False)
            rows = []
            for name, env in live.envs.items():
                m = env.get_metrics()
                rows.append({'Controller': name, **{d: len(env.queues[d]) for d in ROAD_NAMES},
                             'Average wait (s)': m['avg_wait'] if m['served'] else None, 'Served': m['served'],
                             'Waiting': m['remaining'], 'Max total queue': m['max_queue'], 'Reward': m['reward']})
            themed_dataframe(pd.DataFrame(rows), hide_index=True, width='stretch')
            left, right = st.columns([.65, .35])
            with left:
                st.markdown('#### Directional queues · selected controller')
                queue_chart(live)
            with right:
                decision_monitor(live, 'Trained Q-Learning')
        else:
            left, right = st.columns([.65, .35], gap='medium')
            with left:
                phase_panel(live.env)
                components.html(intersection_document(live.env.get_render_data(), live.previous.get(live.controller), motion, .85/speed, theme=ss.get('theme_mode', 'dark')), height=450, scrolling=False)
                st.caption('Cyan: N/S · teal: E/W · one rectangle per queued vehicle. Motion interpolates real IDs; '
                           'departures depict the last completed second, signals show the current snapshot.')
            with right:
                st.caption(f'CONTROLLER · {controller}')
                m = live.env.get_metrics()
                for row in [[('Arrived', m['arrived']), ('Served', m['served'])],
                            [('Waiting now', m['remaining']), ('Average wait', f'{m["avg_wait"]:.2f} s' if m['served'] else 'No departures')],
                            [('Episode reward', f'{m["reward"]:.1f}'), ('Max total queue', m['max_queue'])]]:
                    for col, (label, value) in zip(st.columns(2), row):
                        col.metric(label, value)
                if ready:
                    decision_monitor(live, live.controller)
                else:
                    st.info('AI decision monitor is available after loading a trained model.')
            st.markdown('#### Live directional queues')
            queue_chart(live)
        if live.status == 'complete':
            st.info(f'Episode complete. {live.env.get_metrics()["remaining"]} unresolved vehicles remain for the selected controller. Start replays the same saved arrival trace.')
        ss.live_drawn_time = live.env.time
        if before == 'running' and live.status != 'running':
            st.rerun()
    frame()
    st.toggle('Animate vehicle movements', value=True, key='animate_live', help='Disable for static snapshots. Motion is illustrative and does not change traffic or metrics.')
