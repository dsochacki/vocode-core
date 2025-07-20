FROM vocodedev/vocode:latest

WORKDIR /code
COPY ./pyproject.toml /code/pyproject.toml
COPY ./poetry.lock /code/poetry.lock
RUN pip install --no-cache-dir --upgrade poetry
RUN poetry config virtualenvs.create false
RUN poetry install --only main --no-interaction --no-ansi
COPY main.py /code/main.py
COPY speller_agent.py /code/speller_agent.py
COPY agent_prompt.txt /code/agent_prompt.txt
COPY test.py /code/test.py

#CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--log-level", "debug"]
