from concurrent.futures import ThreadPoolExecutor

from decision_lock.config import Settings
from decision_lock.deployment import DemoBudget, session_settings


def test_public_histories_are_separate_and_stable_per_session():
    first, second = {}, {}
    settings = Settings(app_mode="public_demo")
    a = session_settings(settings, first)
    b = session_settings(settings, second)
    assert a.database_path != b.database_path
    assert session_settings(settings, first).database_path == a.database_path
    first["demo_storage"].cleanup()
    second["demo_storage"].cleanup()


def test_local_history_path_is_preserved():
    settings = Settings()
    state = {}
    assert session_settings(settings, state) == settings
    assert not state


def test_demo_budget_reserves_atomically():
    budget = DemoBudget(5)
    with ThreadPoolExecutor(max_workers=10) as pool:
        accepted = list(pool.map(lambda _: budget.reserve(), range(30)))
    assert sum(accepted) == 5
    assert not budget.reserve()
