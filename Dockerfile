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
RUN uv pip install gunicorn
COPY arxiv-auth/src ./src


FROM python:3.11.8-bookworm AS runner

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src ./src
RUN useradd --create-home e-prints
USER e-prints

ENV PATH="/app/.venv/bin:$PATH"
ENV APPLICATION_ROOT="/"
ENV PYTHONPATH="/app/src"

EXPOSE 8000
CMD ["gunicorn",\
    "--bind", ":8000",\
    "--workers", "5",\
    "--threads", "10",\
    "--timeout", "60",\
    "accounts.factory:create_web_app()"]
