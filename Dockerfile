# arxiv/accounts

FROM 626657773168.dkr.ecr.us-east-1.amazonaws.com/arxiv/base:latest

ADD requirements/prod.txt /opt/arxiv/requirements.txt
RUN pip install -U pip && pip install -r /opt/arxiv/requirements.txt

ENV PATH "/opt/arxiv:${PATH}"

ADD wsgi.py /opt/arxiv/
ADD uwsgi.ini /opt/arxiv/uwsgi.ini
ADD accounts/ /opt/arxiv/accounts/

EXPOSE 8000

WORKDIR /opt/arxiv/
CMD uwsgi --ini uwsgi.ini
