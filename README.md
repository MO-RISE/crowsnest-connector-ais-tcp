# crowsnest-processor-ais-decode

A processing microservice within the crowsnest ecosystem which accepts raw AIS messages as input and produces AIS messages in json struct format.

The microservice:
1. Subscribes to the crowsnest mqtt broker and expects incoming envelopes according to the following format:
   ```json
   {
       "sent_at": ...,
       "message": "IUFJVkRNLDEsMSwsQSwxM3U9UjFQMDAwUG5McEpRMFNKODNsPDIwODBRLDAqNUY="    # base64-encoded AIS message
   }
   ```
2. Assembles multiline messages and decodes to json structs according to the format defined by pyais, see [here](https://github.com/M0r13n/pyais/blob/master/pyais/messages.py#L511-L1326)
3. Publishes jsonified AIS messages to the same crowsnest mqtt broker on the topic format ```.../{mmsi}/{message_type}``` according to the following format:
   ```json
   {
       "sent_at": ...,
       "message": "{jsonified AIS messages}"
   }
   ```


## Development setup
To setup the development environment:

    python3 -m venv venv
    source ven/bin/activate

Install everything thats needed for development:

    pip install -r requirements_dev.txt

In addition, code for `brefv` must be generated using the following commands:

    mkdir brefv
    datamodel-codegen --input brefv-spec/envelope.json --input-file-type jsonschema --output brefv/envelope.py
    datamodel-codegen --input brefv-spec/messages --input-file-type jsonschema  --reuse-model --output brefv/messages

To run the linters:

    black main.py tests
    pylint main.py

To run the tests:

    python -m pytest --verbose tests

## License
Apache 2.0, see [LICENSE](./LICENSE)