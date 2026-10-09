import pytest

pytest_plugins = ["tests.stubs_external"]


@pytest.fixture(autouse=True)
def _relax_throttling(settings):
    settings.REST_FRAMEWORK = {
        **settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_RATES": {
            "anon": "10000/min",
            "user": "10000/min",
            "auth": "10000/min",
        },
    }
