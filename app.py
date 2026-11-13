"""Run with: python -m streamlit run app.py"""
from dataclasses import replace
import json
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from smartflow.config import EnvConfig, SCENARIOS
from smartflow.controllers import FixedTimeController
from smartflow.environment import TrafficEnv
from smartflow.evaluation import compare
from smartflow.paths import ROOT, MODEL, RESULTS
from smartflow.q_learning_agent import QLearningAgent, AgentConfig
from smartflow.training import train
from smartflow.dashboard_live import render_live_page
from smartflow.live_simulation import SCENARIO_LABELS
from smartflow.layout import page_header
from smartflow.theme import initialize_theme, toggle_appearance, theme_css, chart_colors, tokens, style_figure, themed_dataframe, themed_editor

st.set_page_config(page_title='SmartFlow AI', page_icon='🚦', layout='wide')
ss = st.session_state
initialize_theme(ss, st.query_params)
if 'agent' not in ss:
    ss.agent = None
    ss.running = False
    ss.model_message = 'No model loaded'


def load_model():
    try:
        agent = QLearningAgent.load(MODEL)
        if not agent.trained:
            raise ValueError('Saved model has no learning updates')
        ss.agent = agent
        ss.running = False
        if 'live_simulation' in ss:
            ss.live_simulation.pause()
        ss.model_message = f'Loaded: {agent.updates:,} learning updates'
        st.success(ss.model_message)
    except ValueError as exc:
        st.error(str(exc))


def read_csv(name):
    path = RESULTS / name
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except (OSError, ValueError, pd.errors.EmptyDataError) as exc:
        st.warning(f'Cannot read {name}: {exc}')
        return pd.DataFrame()


pages = ['Overview', 'Live Traffic Simulation', 'Train RL Agent', 'Learning Analytics',
         'Performance Comparison', 'RL Explanation', 'Project Information']
with st.sidebar:
    heading, appearance = st.columns([4, 1], vertical_alignment='center')
    heading.subheader('Control center')
    with appearance:
        with st.container(key='appearance_control'):
            action = 'Switch to Dark Mode' if ss.theme_mode == 'light' else 'Switch to Light Mode'
            st.button(action, icon='☀️' if ss.theme_mode == 'light' else '🌙', help=action,
                      key='appearance_toggle', on_click=toggle_appearance, args=(ss, st.query_params))
    page = st.radio('Navigation', pages, key='page')
    st.markdown('[Jump to page heading](#page-title)')
    scenario = st.selectbox('Traffic scenario', list(SCENARIOS), index=1, format_func=SCENARIO_LABELS.get)
    st.write('Model: trained' if ss.agent is not None and ss.agent.trained else 'Model: not loaded')
    st.caption(ss.model_message)
    if st.button('Load Saved Model', key='sidebar_load'):
        load_model()
    with st.expander('Simulation configuration'):
        duration = st.number_input('Episode seconds', 30, 3600, 300, step=30)
        live_seed = st.number_input('Simulation seed', 0, 10000000, 1234)
        min_green = st.number_input('Minimum green (s)', 1, 60, 5)
        max_green = st.number_input('Maximum green (s)', int(min_green), 120, max(30, int(min_green)))
        yellow = st.number_input('Yellow (s)', 1, 10, 2)
        all_red = st.number_input('All-red (s)', 1, 10, 1)
        service = st.number_input('Vehicles per green approach / second', 1, 5, 1)
        fixed_green = st.number_input('Fixed-time green (s)', 1, 120, 15)

st.html(theme_css(ss.theme_mode))
page_header(page)

live_config = EnvConfig(int(duration), int(min_green), int(max_green), int(yellow), int(all_red), int(service))


def analytics():
    data = read_csv('training_history.csv')
    if data.empty:
        st.info('Train an agent to create learning analytics.')
        return
    if not {'episode', 'reward', 'avg_wait', 'avg_queue', 'epsilon', 'served'}.issubset(data.columns):
        st.warning('Training history has an unsupported schema.')
        return
    first, last = int(data.episode.min()), int(data.episode.max())
    selected_range = st.slider('Episode range', first, last, (first, last)) if first < last else (first, last)
    smooth = st.select_slider('Moving average window (episodes)', options=[1, 10, 25, 50, 100], value=50)
    filtered = data[data.episode.between(*selected_range)]
    a1, a2, a3 = st.columns(3)
    a1.metric('Episodes shown', len(filtered))
    a2.metric('Mean recorded reward', f'{filtered.reward.mean():.2f}')
    a3.metric('Mean total queue', f'{filtered.avg_queue.mean():.2f}')
    st.caption('Raw records are always visible. Moving averages use the full history before filtering the displayed episode range.')
    for metric, title in [('reward', 'Cumulative episode reward'), ('avg_wait', 'Served-vehicle waiting time (s)'),
                          ('avg_queue', 'Average total queue (vehicles)'), ('epsilon', 'Exploration epsilon'),
                          ('served', 'Throughput (vehicles)')]:
        plot = data[['episode', metric]].copy()
        if metric != 'epsilon' and smooth > 1:
            plot[f'{smooth}-episode moving average'] = data[metric].rolling(smooth, min_periods=1).mean()
        plot = plot[plot.episode.between(*selected_range)]
        fig = px.line(plot, x='episode', y=list(plot.columns[1:]), title=title,
                      color_discrete_sequence=chart_colors(ss.theme_mode), labels={'episode': 'Training episode', 'value': title, 'variable': 'Series'})
        fig.update_layout(height=300, hovermode='x unified',
                          legend=dict(orientation='h', title=None), margin=dict(t=50, b=10))
        fig.update_xaxes(rangeslider_visible=metric == 'reward')
        st.plotly_chart(style_figure(fig, ss.theme_mode), width='stretch', theme=None, config={'displaylogo': False})
    st.download_button('Export Training CSV', data.to_csv(index=False), 'training_history.csv', 'text/csv')
    if ss.agent is not None:
        a = ss.agent
        with st.expander('Model configuration and training provenance'):
            st.json({'training': a.metadata, 'hyperparameters': vars(a.config), 'environment': vars(a.env_config)})
        st.write(f'{(a.visits > 0).sum():,} visited states / {len(a.q_table):,} possible states; '
                 f'{np.count_nonzero(a.q_table):,} nonzero entries; {a.updates:,} updates')
        index = st.number_input('Inspect encoded state', 0, len(a.q_table)-1, 0)
        st.write('State coordinates:', tuple(int(v) for v in np.unravel_index(int(index), a.env_config.state_shape)))
        themed_dataframe(pd.DataFrame([a.q_table[int(index)]], columns=['Keep Q-value', 'Switch Q-value']))


if page == 'Overview':
    st.markdown('<div class="overview-hero"><small>LEARN · OBSERVE · COMPARE</small><h2>Every green is a decision.</h2>'
                '<p>Watch a learned policy control a four-way intersection, inspect its decisions, and measure congestion '
                'against fixed timing on exactly the same traffic.</p></div>', unsafe_allow_html=True)
    history = read_csv('training_history.csv')
    total = len(history)
    summary = st.columns(4)
    summary[0].metric('Saved training episodes', f'{total:,}')
    summary[1].metric('Saved model', 'Available' if MODEL.exists() else 'Not found')
    summary[2].metric('Session policy', 'Loaded' if ss.agent is not None else 'Not loaded')
    summary[3].metric('Last recorded epsilon', f'{history.epsilon.iloc[-1]:.3f}' if total and 'epsilon' in history else '—')
    if total and 'reward' in history:
        window = min(100, total)
        st.caption(f'Saved training progress · first {window} reward mean {history.reward.head(window).mean():.2f} '
                   f'→ last {window} mean {history.reward.tail(window).mean():.2f}. '
                   'Exploration and traffic traces vary; these are learning diagnostics, not a controlled baseline comparison.')
    for col, destination in zip(st.columns(3), ['Live Traffic Simulation', 'Train RL Agent', 'Performance Comparison']):
        def navigate(target=destination):
            ss.page = target
        col.button(destination, on_click=navigate, width='stretch')
    with st.expander('Explore traffic demand presets'):
        themed_dataframe(pd.DataFrame(SCENARIOS, index=['North', 'South', 'East', 'West']).T.rename(index=SCENARIO_LABELS).rename_axis('Scenario'), width='stretch')
        st.caption('Poisson vehicles/second. Dynamic reverses NS/EW demand halfway through. Heavy demand exceeds ideal default capacity.')
    results = read_csv('improvements.csv')
    if not results.empty and {'scenario', 'metric', 'baseline', 'rl', 'improvement_pct'}.issubset(results):
        st.subheader('Saved measured comparison')
        queues = results[results.metric == 'avg_queue'][['scenario', 'baseline', 'rl', 'improvement_pct']]
        fig = px.bar(queues, x='scenario', y='improvement_pct', color='improvement_pct',
                     color_continuous_scale=[tokens(ss.theme_mode)['error'], tokens(ss.theme_mode)['secondary']], color_continuous_midpoint=0,
                     labels={'improvement_pct': 'Average queue reduction (%)', 'scenario': 'Evaluation scenario'})
        fig.update_layout(height=280, showlegend=False, coloraxis_showscale=False, margin=dict(t=10,b=10))
        st.plotly_chart(style_figure(fig, ss.theme_mode), width='stretch', theme=None)
        themed_dataframe(queues.rename(columns={'scenario': 'Scenario', 'baseline': 'Fixed average queue', 'rl': 'RL average queue', 'improvement_pct': 'Queue reduction (%)'}), hide_index=True)
        st.caption('Positive improvement is better; negative values show worse performance. Saved results may use a different scenario from the sidebar.')

elif page == 'Live Traffic Simulation':
    render_live_page(live_config, scenario, int(live_seed), int(fixed_green))

elif page == 'Train RL Agent':
    defaults = dict(train_episodes=1000, train_alpha=.1, train_gamma=.95, train_epsilon=1.,
                    train_min=.05, train_decay=.995, train_duration=300, train_seed=42, train_scenario='NS Rush')
    if st.button('Reset Training Configuration'):
        for key, value in defaults.items():
            ss[key] = value
    for key, value in defaults.items():
        if key not in ss:
            ss[key] = value
    c1, c2, c3 = st.columns(3)
    episodes = c1.number_input('Training episodes', 1, 20000, key='train_episodes')
    alpha = c1.number_input('Learning rate', .001, 1., key='train_alpha')
    gamma = c1.number_input('Discount factor', 0., 1., key='train_gamma')
    epsilon = c2.number_input('Starting epsilon', 0., 1., key='train_epsilon')
    epsilon_min = c2.number_input('Minimum epsilon', 0., 1., key='train_min')
    decay = c2.number_input('Epsilon decay', .001, 1., key='train_decay', format='%.3f')
    seconds = c3.number_input('Training episode seconds', 10, 3600, key='train_duration')
    seed = c3.number_input('Training seed', 0, 10000000, key='train_seed')
    selected = c3.selectbox('Training scenario', [*SCENARIOS, 'Mixed'], key='train_scenario')
    st.caption('Training uses the signal/service configuration in the sidebar. Starting training replaces the saved training history. '
               'Completed episode rows persist immediately; the model checkpoints every 50 episodes and on handled interruption.')
    cols = st.columns(3)
    start = cols[0].button('Start Training', type='primary')
    if cols[1].button('Load Saved Model', key='training_load'):
        load_model()
    if cols[2].button('Save Model', disabled=ss.agent is None):
        try:
            ss.agent.save(MODEL)
            st.success('Model saved to models/q_table.npz')
        except (OSError, ValueError) as exc:
            st.error(f'Model could not be saved: {exc}')
    if start:
        ss.running = False
        if 'live_simulation' in ss:
            ss.live_simulation.pause()
        progress = st.progress(0.)
        status = st.empty()
        recent = []
        def report(row, agent):
            recent.append(row['reward'])
            progress.progress(row['episode'] / int(episodes))
            status.info(f'Episode {row["episode"]}/{episodes} · {row["episode"]/episodes:.0%} · '
                        f'epsilon {agent.epsilon:.3f} · recent reward {np.mean(recent[-50:]):.2f} · '
                        f'{row["visited_states"]} visited states')
        try:
            agent, history = train(int(episodes), int(seed), selected, replace(live_config, duration=int(seconds)),
                                    AgentConfig(alpha, gamma, epsilon, epsilon_min, decay),
                                    output_dir=RESULTS, model_path=MODEL, callback=report)
            ss.agent = agent
            ss.model_message = f'Trained {len(history)} episodes; {agent.updates:,} updates'
            st.success(ss.model_message + '. Model and history saved.')
        except (OSError, ValueError) as exc:
            st.error(f'Training could not finish: {exc}. Completed checkpoints remain on disk.')
    analytics()

elif page == 'Learning Analytics':
    st.caption('Recorded episode data, including exploration. Reward progress alone does not establish superiority to a baseline.')
    analytics()

elif page == 'Performance Comparison':
    chosen = st.multiselect('Evaluation scenarios', list(SCENARIOS), default=list(SCENARIOS))
    c1, c2, c3 = st.columns(3)
    count = c1.number_input('Evaluation seeds per scenario', 1, 100, 20)
    eval_seed = c2.number_input('First unseen seed', 0, 10000000, 100000)
    eval_duration = c3.number_input('Evaluation seconds', 30, 3600, 300)
    st.caption('Both controllers receive the same pre-generated arrivals and the loaded model’s service/signal configuration. '
               'Evaluation uses epsilon=0 and does not change Q-values. Fixed-time green is configured in the sidebar.')
    if st.button('Run Comparison', type='primary'):
        if ss.agent is None:
            st.warning('Load or train a model first.')
        else:
            try:
                with st.spinner('Evaluating paired unseen traces…'):
                    compare(ss.agent, int(count), int(eval_seed), chosen, int(eval_duration), int(fixed_green), output_dir=RESULTS)
                st.success('Comparison complete; genuine results saved.')
            except (ValueError, OSError) as exc:
                st.error(str(exc))
    data, pairs = read_csv('evaluation_results.csv'), read_csv('improvements.csv')
    if data.empty:
        st.info('Run a comparison to see results.')
    elif not {'controller', 'scenario', 'avg_wait', 'avg_queue', 'served', 'reward'}.issubset(data):
        st.warning('Evaluation data has an unsupported schema.')
    else:
        st.caption('Displaying saved results; changing controls takes effect when Run Comparison is clicked.')
        themed_dataframe(pairs, hide_index=True, width='stretch')
        st.caption('Paired difference = RL minus baseline; SE is the standard error across paired seeds. Undefined percentage denominators appear blank.')
        for metric in ('avg_wait', 'avg_queue', 'served', 'reward'):
            grouped = data.groupby(['scenario', 'controller'])[metric].mean().reset_index()
            figure = px.bar(grouped, x='scenario', y=metric, color='controller', barmode='group', title=metric,
                            color_discrete_map={'Fixed-Time': tokens(ss.theme_mode)['violet'], 'Q-Learning': tokens(ss.theme_mode)['secondary']})
            st.plotly_chart(style_figure(figure, ss.theme_mode), width='stretch', theme=None)
        st.download_button('Export Evaluation Results', data.to_csv(index=False), 'evaluation_results.csv', 'text/csv')
        themed_dataframe(data, hide_index=True)

elif page == 'RL Explanation':
    st.write('Agent: the signal controller. Environment: the four-way intersection. State: four queue buckets '
             '(0–3, 4–7, 8+), active phase, exact green clock, and exact clearance countdown. '
             'Policy: choose the legal action with the greatest learned Q-value. Exploration tries legal actions at random; '
             'exploitation uses their estimated long-term return.')
    st.latex(r'r_t = -0.1\sum_d q_{d,t+1} - 0.5\,\mathbf{1}[\mathrm{switch\ initiated}]')
    st.latex(r'Q(s,a)\leftarrow Q(s,a)+\alpha[r+\gamma\max_{a^\prime\in A(s^\prime)}Q(s^\prime,a^\prime)-Q(s,a)]')
    st.write('Action 0 keeps green; action 1 requests a switch. The environment masks switches before minimum green, '
             'allows no new switch during clearance, and forces switching at maximum green. Only compatible roads receive green. '
             'True terminal targets use reward only; time-limit truncations retain bootstrapping because this is a continuing control task.')
    st.write('Default state space: 3⁴ × 2 × 31 × 4 = 20,088 states and 40,176 Q-values. '
             'Many combinations are unreachable. Queue bucketing and unobserved dynamic demand make this an approximate state abstraction.')
    a = ss.agent
    state = ss.env.get_state() if 'env' in ss else (0, 0, 0, 0, 0, 0, 0)
    st.code(f'Observed example state: {state}')
    if a is not None:
        try:
            themed_dataframe(pd.DataFrame([a.q_table[a.encode_state(state)]], columns=['Keep', 'Switch']))
        except ValueError:
            st.info('Current live state uses a different timing configuration; inspect model states in Learning Analytics.')
    st.caption('No queue-length heuristic replaces the learned controller. Initial and unseen-state ties are broken deterministically during evaluation.')

elif page == 'Project Information':
    st.write('Assessment Task 2: RL Innovation Hackathon — Build an Intelligent Learning Agent')
    st.write('Sidharth P Nair · RA2311026050087 · B.Tech CSE (AI and ML) · Reinforcement Learning')
    st.write('SRM Institute of Science and Technology, Tiruchirappalli')
    st.code('Seeded arrivals → TrafficEnv → masked Q-Learning → model + metrics\n'
            '                           ↘ fixed-time paired evaluation ↗\n'
            '                       Streamlit + Plotly dashboard')
    st.write('Python, NumPy, Pandas, Streamlit, Plotly, Matplotlib and pytest. Objective: reduce cumulative queueing delay safely.')
    team_path = ROOT / 'team.json'
    default_team = [{'Name': 'Sidharth P Nair', 'Registration': 'RA2311026050087', 'Contribution': ''}]
    try:
        team = json.loads(team_path.read_text(encoding='utf-8')) if team_path.exists() else default_team
    except (ValueError, OSError):
        team = default_team
    team_frame = pd.DataFrame(team).reindex(columns=list(default_team[0]), fill_value='')
    edited = themed_editor(team_frame, num_rows='dynamic', key='team_editor', width='stretch')
    if st.button('Save Team Details'):
        try:
            team_path.write_text(edited.fillna('').to_json(orient='records', indent=2), encoding='utf-8')
            st.success('Team details saved locally. Enter only actual contributions.')
        except OSError as exc:
            st.error(f'Could not save team details: {exc}')
    st.write('Limitations: a single intersection, no turning or pedestrians, stochastic arrivals, bucketed queues, '
             'finite training coverage and no real-world validation. Heavy demand cannot be stabilized. '
             'Future proposals: SUMO, emergency priority, multiple intersections and deep RL.')
    st.markdown('[Q-learning: Watkins & Dayan (1992)](https://doi.org/10.1007/BF00992698) · '
                '[Sutton & Barto textbook](http://incompleteideas.net/book/the-book-2nd.html) · '
                '[Streamlit](https://docs.streamlit.io/) · [NumPy](https://numpy.org/doc/)')
    for name in ('PROJECT_REPORT.md', 'DEMO_GUIDE.md'):
        path = ROOT / 'docs' / name
        if path.exists():
            st.download_button(f'Download {name}', path.read_text(encoding='utf-8'), name)
