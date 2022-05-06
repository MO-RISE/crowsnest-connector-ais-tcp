import time
import pytest


@pytest.fixture(scope="session")
def compose(docker_ip, docker_services):
    """Stupid simple way of making sure everything is up and running"""
    time.sleep(10)
