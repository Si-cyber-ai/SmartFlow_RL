"""Shared page identity and normal-flow headings, clear of Streamlit's toolbar."""
import streamlit as st

PAGE_DETAILS = {
    'Overview': ('Overview', 'Saved learning progress, demand presets and measured controller comparisons.'),
    'Live Traffic Simulation': ('Live Traffic Simulation', 'Observe real queues, safe signals and the current controller’s decisions.'),
    'Train RL Agent': ('Train RL Agent', 'Configure a new training run and inspect recorded learning.'),
    'Learning Analytics': ('Learning Analytics', 'Explore genuine episode metrics and learned Q-values.'),
    'Performance Comparison': ('Performance Comparison', 'Compare controllers on identical unseen traffic arrivals.'),
    'RL Explanation': ('How SmartFlow AI Learns', 'Understand the state, legal actions, rewards and Bellman updates.'),
    'Project Information': ('Project Information', 'Project architecture, editable team details, references and report downloads.'),
}


def page_header(page):
    title, description = PAGE_DETAILS[page]
    with st.container(key='page_heading'):
        st.markdown('<div class="brand"><strong>SmartFlow AI</strong><span>Intelligent Traffic Control</span></div>', unsafe_allow_html=True)
        st.header(title, anchor='page-title')
        st.caption(description)
