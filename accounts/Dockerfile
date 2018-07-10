# arxiv/accounts

FROM arxiv/base:latest

WORKDIR /opt/arxiv/

RUN yum install -y which
ADD Pipfile Pipfile.lock /opt/arxiv/
RUN pip install -U pip pipenv
ENV LC_ALL en_US.utf-8
ENV LANG en_US.utf-8
RUN pipenv install

ENV PATH "/opt/arxiv:${PATH}"

ADD wsgi.py uwsgi.ini /opt/arxiv/
ADD accounts/ /opt/arxiv/accounts/

EXPOSE 8000

CMD pipenv run uwsgi --ini uwsgi.ini
