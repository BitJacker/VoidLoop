import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
os.environ["VOIDLOOP_HOME"] = tempfile.mkdtemp(prefix="voidloop_tests_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture(scope="session")
def screen():
    pygame.display.init()
    pygame.font.init()
    return pygame.display.set_mode((1280, 720))


@pytest.fixture()
def app(screen):
    from VoidLoop.app import App
    a = App(headless=True, lang="en", no_audio=True)
    yield a
    pygame.event.clear()


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: long-running integration tests")
