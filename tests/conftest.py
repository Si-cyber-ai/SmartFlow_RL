"""Use ordinary workspace dirs: host sandbox denies pytest's private-mode dirs."""
from pathlib import Path
import uuid
import pytest


@pytest.fixture(autouse=True)
def component_registry_for_app_test(monkeypatch):
    """AppTest 1.55 mocks the v2 registry; use the real registry for serialization.

    This does not simulate browser JS or bypass the component's Python renderer.
    """
    from unittest.mock import MagicMock
    import streamlit.testing.v1.app_test as app_test
    from streamlit.components.v2.component_manager import BidiComponentManager
    from streamlit.components.v2 import component
    from streamlit.runtime import Runtime
    manager = BidiComponentManager()
    def runtime_mock(*args, **kwargs):
        runtime = MagicMock(*args, **kwargs)
        runtime.bidi_component_registry = manager
        saved = Runtime._instance
        Runtime._instance = runtime
        try:
            from smartflow.table_component import _CSS
            if manager.get('smartflow_table') is None:
                component('smartflow_table', html='<div class="sf-grid"></div>', css=_CSS,
                          js=(Path(__file__).resolve().parents[1] / 'smartflow/table_component.js').read_text(encoding='utf-8'))
        finally:
            Runtime._instance = saved
        return runtime
    monkeypatch.setattr(app_test, 'MagicMock', runtime_mock)


@pytest.fixture
def tmp_path():
    path = Path(__file__).resolve().parents[1] / 'test-artifacts' / uuid.uuid4().hex
    path.mkdir(parents=True)
    return path
