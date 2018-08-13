# arxiv/authenticator

FROM arxiv/base:latest

WORKDIR /opt/arxiv/

RUN yum install -y which mysql mysql-devel
ADD Pipfile Pipfile.lock /opt/arxiv/
RUN pip install -U pip pipenv
ENV LC_ALL en_US.utf-8
ENV LANG en_US.utf-8
RUN pipenv install

ENV PATH "/opt/arxiv:${PATH}"

ADD wsgi.py /opt/arxiv/
ADD authenticator/ /opt/arxiv/authenticator/

EXPOSE 8000

ENTRYPOINT ["pipenv", "run", "uwsgi"]
CMD ["--http-socket", ":8000", \
     "-M", \
     "-t 3000", \
     "--manage-script-name", \
     "--processes", "8", \
     "--threads", "1", \
     "--async", "100", \
     "--ugreen", \
     "--mount", "/authenticator=wsgi.py", \
     "--logformat", "%(addr) %(addr) - %(user_id)|%(session_id) [%(rtime)] [%(uagent)] \"%(method) %(uri) %(proto)\" %(status) %(size) %(micros) %(ttfb)"]
