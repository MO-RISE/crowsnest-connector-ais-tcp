"""Main entrypoint for this application"""
import logging
import warnings
from base64 import b64decode, b64encode
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional

from streamz import Stream

import pydantic.json
from pyais.messages import ANY_MESSAGE, NMEAMessage
from pyais.exceptions import InvalidNMEAMessageException
from environs import Env

from paho.mqtt.client import MQTTMessage, Client as MQTT

from brefv.envelope import Envelope


# Reading config from environment variables
env = Env()

MQTT_BROKER_HOST = env("MQTT_BROKER_HOST")
MQTT_BROKER_PORT = env.int("MQTT_BROKER_PORT", 1883)
MQTT_CLIENT_ID = env("MQTT_CLIENT_ID", None)
MQTT_TRANSPORT = env("MQTT_TRANSPORT", "tcp")
MQTT_TLS = env.bool("MQTT_TLS", False)
MQTT_USER = env("MQTT_USER", None)
MQTT_PASSWORD = env("MQTT_PASSWORD", None)

MQTT_INPUT_TOPIC = env("MQTT_INPUT_TOPIC")
MQTT_OUTPUT_BASE_TOPIC = env("MQTT_OUTPUT_BASE_TOPIC")

LOG_LEVEL = env.log_level("LOG_LEVEL", logging.WARNING)


# Setup logger
logging.basicConfig(level=LOG_LEVEL)
logging.captureWarnings(True)
warnings.filterwarnings("once")
LOGGER = logging.getLogger("crowsnest-processor-ais-decode")

# Create mqtt client and confiure it according to configuration
mq = MQTT(client_id=MQTT_CLIENT_ID, transport=MQTT_TRANSPORT)
mq.username_pw_set(MQTT_USER, MQTT_PASSWORD)
if MQTT_TLS:
    mq.tls_set()

mq.enable_logger(LOGGER)

# Monkey-patch pydantics json handling of bytes
# pylint: disable=c-extension-no-member
pydantic.json.ENCODERS_BY_TYPE[bytes] = lambda x: b64encode(x).decode()


# Not empty filter
not_empty = lambda x: x is not None


### Processing functions


def from_mqtt(mqtt_message: MQTTMessage) -> bytes:
    """Parse a mqtt_message as a brefv envelope and b64decode"""
    LOGGER.debug("Received new mqtt message!")

    envelope: Envelope = Envelope.parse_raw(mqtt_message.payload)

    return b64decode(envelope.message)


buffer: Dict[Tuple[int, str], List[Optional[NMEAMessage]]] = {}


def assemble_messages(  # pylint: disable=inconsistent-return-statements
    line: bytes,
) -> NMEAMessage:
    """Assemble multiline NMEA messages"""
    LOGGER.debug("with content: %s", line)
    try:
        msg: NMEAMessage = NMEAMessage(line)
    except InvalidNMEAMessageException:
        # Be gentle and just skip invalid messages
        return None

    if msg.is_single:
        return msg

    # Instead of None use -1 as a seq_id
    seq_id = msg.seq_id
    if seq_id is None:
        seq_id = -1

    # seq_id and channel make a unique stream
    slot = (seq_id, msg.channel)

    if slot not in buffer:
        # Create a new array in the buffer that has enough space for all fragments
        buffer[slot] = [
            None,
        ] * max(msg.fragment_count, 0xFF)

    buffer[slot][msg.frag_num - 1] = msg
    msg_parts = buffer[slot][0 : msg.fragment_count]

    # Check if all fragments are found
    not_none_parts = [m for m in msg_parts if m is not None]
    if len(not_none_parts) == msg.fragment_count:
        del buffer[slot]
        return NMEAMessage.assemble_from_iterable(not_none_parts)


def decode(message: NMEAMessage) -> ANY_MESSAGE:
    """Decode the NMEAMessage into a AISMessage"""
    return message.decode()


def to_brefv(message: ANY_MESSAGE) -> Tuple[Envelope, int, int]:
    """From AISMessage to brefv envelope"""

    envelope = Envelope(
        sent_at=datetime.now(timezone.utc).isoformat(),
        message=message.asdict(enum_as_int=True),
    )

    return envelope, int(message.mmsi), int(message.msg_type)


def to_mqtt(envelope: Envelope, mmsi: int, message_type: int):
    """Publish an envelope to a mqtt topic"""

    topic = f"{MQTT_OUTPUT_BASE_TOPIC}/{mmsi}/{message_type}"
    payload = envelope.json()

    LOGGER.debug("Publishing on %s with payload: %s", topic, payload)
    try:
        mq.publish(
            topic,
            payload,
        )
    except Exception:  # pylint: disable=broad-except
        LOGGER.exception("Failed publishing to broker!")


if __name__ == "__main__":

    # Build pipeline
    LOGGER.info("Building pipeline...")
    source = Stream()
    pipe = (
        source.map(from_mqtt)
        .map(assemble_messages)
        .filter(not_empty)
        .map(decode)
        .map(to_brefv)
        .starmap(to_mqtt)
    )
    LOGGER.debug(list(source.downstreams))

    # Setting up callbacks
    mq.on_connect = lambda *_: mq.subscribe(MQTT_INPUT_TOPIC)
    mq.on_message = lambda client, userdata, message: source.emit(message)

    LOGGER.info("Connecting to MQTT broker...")
    mq.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT)

    # Data driven, lets just make sure to stay connected!
    mq.loop_forever()
