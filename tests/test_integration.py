from base64 import b64encode
from datetime import datetime
import time
import json
import threading
from contextlib import contextmanager
from unittest.mock import MagicMock

from brefv.envelope import Envelope
from paho.mqtt import subscribe, publish


@contextmanager
def subscriber(*args, **kwargs):
    t = threading.Thread(target=subscribe.callback, args=args, kwargs=kwargs)
    t.setDaemon(True)
    t.start()
    time.sleep(0.1)
    yield


def test_all_parts(broker, app, pinned):

    mock = MagicMock()

    with subscriber(mock, "OUTPUT/#"):
        with open("tests/ais_log.txt") as f:
            for line in f.readlines():
                env = Envelope(
                    sent_at=datetime.utcnow().isoformat(),
                    message=b64encode(line.strip().encode()),
                )
                publish.single("INPUT", env.json())
                time.sleep(0.01)

        time.sleep(2)

    assert mock.called
    assert mock.call_count == pinned

    received_envelopes = [
        Envelope.parse_raw(args[2].payload) for args, kwargs in mock.call_args_list
    ]

    assert [env.message for env in received_envelopes] == pinned
