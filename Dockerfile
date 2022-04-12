# The two-stage build is needed since libais is not available as a wheel and thus needs to be built
FROM python:3.8-slim-bullseye

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

WORKDIR /app

COPY brefv-spec/ brefv-spec/
RUN mkdir brefv && \
    datamodel-codegen --input brefv-spec/envelope.json --input-file-type jsonschema --output brefv/envelope.py && \
    datamodel-codegen --input brefv-spec/messages --input-file-type jsonschema  --reuse-model --output brefv/messages


COPY main.py main.py

CMD ["python3", "main.py"]