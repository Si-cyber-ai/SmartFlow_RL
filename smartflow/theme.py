"""Presentation-only themes. No global Streamlit configuration mutations."""
from types import MappingProxyType

_COMMON = dict(road_color='#23354B', road_markings='#D7E8F5', road_centerline='#D2B861',
               intersection='#1A2B40', signal_housing='#060E19', signal_off='#263548',
               vehicle_ns='#38BDF8', vehicle_ew='#2DD4BF', vehicle_outline='#B9F4FF',
               vehicle_window='#15374B', departed_vehicle='#A7F3D0')
THEMES = MappingProxyType({
    'dark': MappingProxyType(dict(_COMMON, background='#0B1120', surface='#111827', sidebar='#151E30',
        card='#172238', text_primary='#F8FAFC', text_secondary='#CBD5E1', muted='#94A3B8', border='#334155',
        accent='#38BDF8', secondary='#14B8A6', success='#22C55E', warning='#F59E0B', error='#F87171',
        chart_background='#0B1120', chart_text='#F8FAFC', chart_grid='#334155',
        chart_axis_title='#E2E8F0', chart_ticks='#CBD5E1', chart_legend='#E2E8F0', chart_zero='#475569',
        chart_annotation='#F8FAFC', chart_hover='#1E293B', secondary_text='#5EEAD4', button_accent='#38BDF8', link_text='#38BDF8',
        scene_background='#0B1626', scene_grid='#16283E', scene_text='#E6F7FF', scene_muted='#91AAC3',
        selected_background='#10383B', shadow='none', violet='#A5B4FC')),
    'light': MappingProxyType(dict(_COMMON, background='#FFFFFF', surface='#F8FAFC', sidebar='#F1F5F9',
        card='#FFFFFF', text_primary='#0F172A', text_secondary='#475569', muted='#64748B', border='#CBD5E1',
        accent='#0284C7', secondary='#0D9488', success='#15803D', warning='#B45309', error='#B91C1C',
        chart_background='#FFFFFF', chart_text='#0F172A', chart_grid='#E2E8F0',
        chart_axis_title='#334155', chart_ticks='#475569', chart_legend='#334155', chart_zero='#CBD5E1',
        chart_annotation='#334155', chart_hover='#FFFFFF', secondary_text='#0F766E', button_accent='#0369A1', link_text='#0369A1',
        scene_background='#F1F5F9', scene_grid='#E2E8F0', scene_text='#0F172A', scene_muted='#475569',
        selected_background='#E6F6F2', shadow='0 2px 8px rgb(15 23 42 / 5%)', violet='#6D28D9')),
})
def tokens(mode='dark'):
    if mode not in THEMES:
        raise ValueError('Theme must be light or dark')
    return THEMES[mode]


def toggle_appearance(state, query):
    """Widget callback: update presentation state only, never simulation state."""
    state['theme_mode'] = 'light' if state.get('theme_mode', 'dark') == 'dark' else 'dark'
    query['appearance'] = state['theme_mode']
    state['theme_redraw_only'] = state.get('page') == 'Live Traffic Simulation'


def initialize_theme(state, query):
    if 'theme_mode' not in state:
        preferred = query.get('appearance', 'dark')
        state['theme_mode'] = preferred if preferred in THEMES else 'dark'
    return state['theme_mode']


def chart_colors(mode='dark'):
    t = tokens(mode)
    return [t['accent'], t['secondary'], t['violet'], t['warning']]


def queue_colors(mode='dark'):
    t = tokens(mode)
    return dict(North=t['accent'], South=t['violet'], East=t['secondary'], West=t['warning'])


def style_figure(figure, mode='dark'):
    t = tokens(mode)
    figure.update_layout(template='plotly_white' if mode == 'light' else 'plotly_dark',
                          paper_bgcolor=t['chart_background'], plot_bgcolor=t['chart_background'],
                          font=dict(color=t['chart_text']), title_font_color=t['chart_text'], colorway=chart_colors(mode),
                          legend=dict(font_color=t['chart_legend'], title_font_color=t['chart_legend']),
                          modebar=dict(color=t['chart_ticks'], activecolor=t['accent'], bgcolor=t['chart_background']),
                          hoverlabel=dict(bgcolor=t['chart_hover'], font_color=t['text_primary'], bordercolor=t['border']))
    figure.update_layout(autosize=True, height=max(280, figure.layout.height or 300),
                          margin=dict(l=64, r=24, t=72, b=60), title=dict(automargin=True),
                          legend=dict(orientation='h', x=0, y=1.02, xanchor='left', yanchor='bottom'))
    axis_colors = dict(gridcolor=t['chart_grid'], zerolinecolor=t['chart_zero'], color=t['chart_ticks'],
                       title_font_color=t['chart_axis_title'], tickfont_color=t['chart_ticks'], automargin=True)
    figure.update_xaxes(**axis_colors)
    figure.update_yaxes(**axis_colors)
    figure.update_annotations(font_color=t['chart_annotation'], arrowcolor=t['chart_annotation'],
                              bgcolor=t['chart_background'], bordercolor=t['border'])
    colorbar_style = dict(tickfont_color=t['chart_ticks'], title_font_color=t['chart_axis_title'],
                          bgcolor=t['chart_background'], outlinecolor=t['border'])
    for key in figure.layout:
        if key.startswith('coloraxis'):
            figure.layout[key].colorbar.update(**colorbar_style)
        if key.startswith('xaxis') and figure.layout[key].rangeslider.visible:
            figure.layout[key].rangeslider.update(bgcolor=t['chart_background'], bordercolor=t['border'])
    for menu in figure.layout.updatemenus:
        menu.update(font_color=t['chart_text'], bgcolor=t['card'], bordercolor=t['border'])
    for slider in figure.layout.sliders:
        slider.update(font_color=t['chart_ticks'], currentvalue_font_color=t['chart_text'],
                      bgcolor=t['surface'], bordercolor=t['border'], tickcolor=t['chart_ticks'])
    for trace in figure.data:
        if hasattr(trace, 'textfont'):
            trace.update(textfont_color=t['chart_text'])
        if hasattr(trace, 'hoverlabel'):
            trace.hoverlabel.update(bgcolor=t['chart_hover'], font_color=t['text_primary'], bordercolor=t['border'])
        if hasattr(trace, 'colorbar'):
            trace.colorbar.update(**colorbar_style)
        if hasattr(trace, 'marker') and hasattr(trace.marker, 'colorbar'):
            trace.marker.colorbar.update(**colorbar_style)
    # Semantic shape colors (traffic indicators, thresholds) remain intact.
    return figure


def themed_dataframe(frame, **kwargs):
    import streamlit as st
    from .table_component import render_table
    return render_table(frame, st.session_state.get('theme_mode', 'dark'), **kwargs)


def themed_editor(frame, **kwargs):
    import streamlit as st
    from .table_component import render_table
    return render_table(frame, st.session_state.get('theme_mode', 'dark'), editable=True, **kwargs)


def theme_css(mode='dark'):
    t = tokens(mode)
    variables = ';'.join(f'--sf-{name.replace("_", "-")}:{value}' for name, value in t.items())
    return '<style id="smartflow-theme">:root{' + variables + ';color-scheme:' + mode + ';}' + r'''
:root,.stApp,[data-testid="stAppViewContainer"],[data-testid="stSidebar"]{
--text-color:var(--sf-text-primary);--background-color:var(--sf-background);
--secondary-background-color:var(--sf-surface);--primary-color:var(--sf-accent);color:var(--sf-text-primary)}
.stApp,[data-testid="stAppViewContainer"],.stMain{background:var(--sf-background);color:var(--sf-text-primary)}
.stMain .block-container{padding:calc(3.75rem + 1.75rem) clamp(1rem,2vw,2rem) 2rem;max-width:1280px;min-width:0}
header[data-testid="stHeader"]{background:var(--sf-background)}
[data-testid="stSidebar"]{background:var(--sf-sidebar)}
[data-testid="stSidebarUserContent"]{padding:1.5rem 1.25rem}
.st-key-page_heading{margin-bottom:1rem;scroll-margin-top:5rem}
.st-key-page_heading h2{font-size:1.875rem;line-height:1.3;margin:0;padding:.25rem 0 .5rem}
#page-title{scroll-margin-top:5rem}
[data-testid="stMetric"]{background:var(--sf-card);padding:10px 12px;border-radius:12px;
border:1px solid var(--sf-border);box-shadow:var(--sf-shadow);min-width:0}
[data-testid="stMetricLabel"]{font-size:.76rem;color:var(--sf-text-secondary)}
[data-testid="stMetricValue"]{font-size:1.5rem;line-height:1.5;color:var(--sf-text-primary);overflow-wrap:anywhere}
[data-testid="stMetricValue"]>div{white-space:normal}
h1,h2,h3,h4{line-height:1.4;color:var(--sf-text-primary);overflow-wrap:break-word}
.stMain h3{font-size:1.375rem}.stMain h4{font-size:1.125rem}
[data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"],label, .katex{color:var(--sf-text-primary)}
[data-testid="stMarkdownContainer"] p{color:inherit}
button [data-testid="stMarkdownContainer"]{color:inherit}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p{color:var(--sf-text-secondary)}
a{color:var(--sf-link-text)}
button[kind], [data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-tertiary"]{border-radius:9px!important;background:var(--sf-card);color:var(--sf-text-primary);border-color:var(--sf-border)}
[data-testid="stBaseButton-primary"]{background:var(--sf-button-accent)!important;color:var(--sf-background)!important;border-color:var(--sf-button-accent)!important}
button:disabled{opacity:.45}button:hover:not(:disabled){border-color:var(--sf-accent)}
input,textarea,[data-baseweb="select"]>div,[data-baseweb="input"],[data-baseweb="base-input"],
[data-baseweb="popover"],[data-baseweb="menu"],[role="listbox"],[role="option"]{background:var(--sf-surface)!important;color:var(--sf-text-primary)!important;border-color:var(--sf-border)!important}
input::placeholder,textarea::placeholder{color:var(--sf-text-secondary)!important}
[data-baseweb="select"] span,[data-baseweb="select"] svg,[data-baseweb="input"] svg{color:var(--sf-text-primary)}
[role="option"]:hover,[aria-selected="true"][role="option"]{background:var(--sf-selected-background)!important}
[role="option"] span{color:inherit}
[data-baseweb="tag"]{background:var(--sf-selected-background);color:var(--sf-text-primary)}
[data-baseweb="tag"] span{color:inherit}
[data-testid="stNumberInput"] button{color:var(--sf-text-primary);background:var(--sf-surface)}
[data-testid="stRadio"] [role="radiogroup"]{color:var(--sf-text-primary)}
input[type="radio"],input[type="checkbox"]{accent-color:var(--sf-button-accent)}
[role="slider"]{background:var(--sf-accent)!important;border-color:var(--sf-accent)!important}
[data-testid="stSliderTickBar"], [data-testid="stSliderThumbValue"]{color:var(--sf-text-secondary)}
[data-testid="stProgress"] [role="progressbar"]{background:var(--sf-surface)}
[data-testid="stProgress"] [role="progressbar"]>div{background:var(--sf-accent)}
[data-testid="stExpander"] details,[data-testid="stVerticalBlockBorderWrapper"]{border-color:var(--sf-border)}
[data-testid="stExpander"] summary{background:var(--sf-surface);color:var(--sf-text-primary)}
[data-testid="stCode"], [data-testid="stCode"] pre,[data-testid="stCode"] code,
[data-testid="stJson"]{background:var(--sf-surface)!important;color:var(--sf-text-primary)!important;border-radius:8px}
[data-testid="stCode"] span,[data-testid="stJson"] span{color:var(--sf-text-primary)!important}
[data-testid="stAlert"] [role="alert"]{background:var(--sf-surface);color:var(--sf-text-primary);border:1px solid var(--sf-border)}
[data-testid="stAlert"] svg{color:var(--sf-accent)}
.brand{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin:0 0 8px}
.brand strong{font-size:27px;color:var(--sf-accent);letter-spacing:-1px}.brand span{color:var(--sf-text-secondary);font-size:12px}
.phase-strip{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;background:var(--sf-surface);border:1px solid var(--sf-border);border-radius:10px;padding:12px 16px;font-size:13px;color:var(--sf-secondary-text)}
.phase-strip span{color:var(--sf-text-primary);font-variant-numeric:tabular-nums}
.decision-actions{display:flex;gap:8px;margin:6px 0}.decision-action{flex:1;padding:9px 12px;border:1px solid var(--sf-border);border-radius:10px;background:var(--sf-card);font-size:12px}
.decision-action.selected{border-color:var(--sf-secondary);background:var(--sf-selected-background);color:var(--sf-secondary-text)}
.decision-action.masked{color:var(--sf-text-secondary);border-style:dashed}
.overview-hero{padding:22px 26px;border:1px solid var(--sf-border);border-radius:18px;background:var(--sf-surface);margin-bottom:14px}
.overview-hero small{color:var(--sf-secondary-text);letter-spacing:2px}.overview-hero h2{margin:5px 0;font-size:28px}
.st-key-appearance_control button{width:38px!important;height:38px!important;min-height:38px!important;
border-radius:50%!important;padding:0!important;display:flex;align-items:center;justify-content:center;
border:1px solid var(--sf-border)!important;background:var(--sf-card)!important;
box-shadow:var(--sf-shadow);transition:background-color .15s,border-color .15s,box-shadow .15s}
.st-key-appearance_control button:hover{background:var(--sf-selected-background)!important;border-color:var(--sf-accent)!important}
.st-key-appearance_control button:focus-visible{outline:2px solid var(--sf-accent);outline-offset:3px}
.st-key-appearance_control button [data-testid="stMarkdownContainer"]{position:absolute!important;
width:1px!important;height:1px!important;padding:0!important;margin:-1px!important;overflow:hidden!important;
clip-path:inset(50%)!important;white-space:nowrap!important;border:0!important}
@media(prefers-reduced-motion:reduce){.st-key-appearance_control button{transition:none}}
.overview-hero p{color:var(--sf-text-secondary);font-size:14px;max-width:750px;margin-bottom:0}
@media(max-width:1100px){.stMain [data-testid="stHorizontalBlock"]{flex-wrap:wrap}.stMain [data-testid="stColumn"]{flex:1 1 15rem!important;min-width:0}}
@media(max-width:700px){.brand{display:block}.brand span{display:block}.stMain [data-testid="stColumn"]{flex-basis:100%!important}}
</style>'''
