from base64 import b64encode
from datetime import datetime
import time
import json
from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

from brefv.envelope import Envelope
from paho.mqtt import publish
from paho.mqtt.client import Client
from pyais.messages import JSONEncoder as BytesJSONEncoder


@contextmanager
def subscriber(callback, topic):
    c = Client()
    c.on_message = callback
    c.connect("localhost")
    c.subscribe(topic, qos=2)
    c.loop_start()
    yield
    c.loop_stop()
    del c


@pytest.mark.xfail
def test_mqtt_setup(compose):

    mock = MagicMock()

    with subscriber(mock, "TEST/#"):
        publish.single("TEST", "TEST", qos=2)
        publish.single("TEST", "TEST", qos=2)
        publish.single("TEST", "TEST", qos=2)

    assert mock.call_count == 3


def test_all_parts(compose, pinned):

    mock = MagicMock()

    with subscriber(mock, "OUTPUT/#"):
        with open("tests/ais_log.txt") as f:
            for line in f.readlines():
                env = Envelope(
                    sent_at=datetime.utcnow().isoformat(),
                    message=b64encode(line.strip().encode()),
                )
                publish.single("INPUT", env.json(), qos=2)
                time.sleep(0.01)

        time.sleep(1)

    assert mock.call_count == pinned

    received_envelopes = [
        Envelope.parse_raw(args[2].payload) for args, kwargs in mock.call_args_list
    ]

    msgs = [env.message for env in received_envelopes]

    # Workaround for https://github.com/freol35241/pytest-pinned/issues/10
    msgs = json.loads(json.dumps(msgs, cls=BytesJSONEncoder))

    assert msgs == pinned
