FROM python:3.11-bookworm

RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 0E98404D386FA1D9 6ED0E7B82643E131 F8D2585B8783D481 54404762BBB6E853 BDE6D2B9216EC7A8 ; exit 0

RUN apt-get update -y -o APT::Get::AllowUnauthenticated=true
RUN apt-get install -y --allow-unauthenticated --no-install-recommends build-essential gcc python3-dev default-libmysqlclient-dev pkg-config
RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/*

RUN apt-get update -y -o APT::Get::AllowUnauthenticated=true && \
    apt-get install -y --allow-unauthenticated --no-install-recommends build-essential gcc python3-dev default-libmysqlclient-dev pkg-config && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Setup venv and put into use. https://pythonspeed.com/articles/activate-virtualenv-dockerfile/
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV

# Every python thing after this is in the venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN python -m pip install -U pip

WORKDIR /opt/arxiv/
RUN pip install poetry

ADD poetry.lock /opt/arxiv/
ADD pyproject.toml /opt/arxiv/

RUN poetry config virtualenvs.create false && poetry install --no-dev --no-interaction --no-ansi
RUN pip uninstall -y poetry

ADD arxiv_oauth2 /opt/arxiv/arxiv_oauth2
ADD app-logging.conf /opt/arxiv/
ADD hypercorn-config.toml /opt/arxiv/

RUN pip install hypercorn

ENV WORKERS 8
ENV SQLALCHEMY_TRACK_MODIFICATIONS False
EXPOSE $PORT
CMD /opt/venv/bin/hypercorn --config hypercorn-config.toml --bind 0.0.0.0:$PORT --log-config app-logging.conf --workers $WORKERS "arxiv_oauth2.main:create_app()"
