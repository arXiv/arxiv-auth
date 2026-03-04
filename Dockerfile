# arxiv/accounts for /login /logout and /become_user pages

FROM python:3.11.8-bookworm AS builder

ARG git_commit

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    LC_ALL=en_US.utf8 \
    LANG=en_US.utf8

WORKDIR /app

RUN apt-get -y install default-libmysqlclient-dev
RUN pip install -U pip uv
COPY arxiv-auth/uv.lock arxiv-auth/pyproject.toml ./
RUN uv sync --no-install-project --frozen --no-dev
COPY arxiv-auth/src ./src


FROM python:3.11.8-bookworm AS runner

WORKDIR /app
COPY --from=builder /app/.venv /.venv
COPY --from=builder /app/src ./src

RUN useradd --create-home e-prints
USER e-prints

ENV PATH="/.venv/bin:$PATH"
ENV APPLICATION_ROOT="/"

EXPOSE 8000
CMD ["uwsgi", "--ini", "/arxiv-auth/uwsgi.ini"]
