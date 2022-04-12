import main

import json
from pathlib import Path
from unittest.mock import MagicMock
from datetime import datetime

from paho.mqtt.client import MQTTMessage
from brefv.envelope import Envelope
from pyais.messages import NMEAMessage


def test_from_mqtt():

    envelope = Envelope(
        sent_at=datetime.utcnow().isoformat(),
        message="IUFJVkRNLDEsMSwsQSwxM3U9UjFQMDAwUG5McEpRMFNKODNsPDIwODBRLDAqNUY=",
    ).json()

    msg = MQTTMessage()

    msg.payload = envelope.encode()

    result = main.from_mqtt(msg)

    assert result == b"!AIVDM,1,1,,A,13u=R1P000PnLpJQ0SJ83l<2080Q,0*5F"


def test_assemble_messages():
    first = (
        b"!AIVDM,2,1,1,A,53uElH000001<UDB2205<dPthlDr22222222221S1p6334wo031km21C,0*6E"
    )
    second = b"!AIVDM,2,2,1,A,PUDQh0000000000,2*6D"

    assert main.assemble_messages(first) is None

    res = main.assemble_messages(second)
    assert res is not None

    assert res == NMEAMessage.assemble_from_iterable(
        [NMEAMessage(first), NMEAMessage(second)]
    )


def test_decode(pinned):
    msg = NMEAMessage(b"!AIVDM,1,1,,A,13u=R1P000PnLpJQ0SJ83l<2080Q,0*5F")

    res = main.decode(msg)

    assert res.asdict(enum_as_int=True) == pinned


def test_to_brefv(pinned):
    msg = NMEAMessage(b"!AIVDM,1,1,,A,13u=R1P000PnLpJQ0SJ83l<2080Q,0*5F")

    res = main.decode(msg)

    env, mmsi, type = main.to_brefv(res)

    assert env.message == pinned
    assert mmsi == pinned
    assert type == pinned
