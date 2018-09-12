# arxiv/submission-gateway

FROM arxiv/base

ADD nginx.repo /etc/yum.repos.d/nginx.repo
RUN yum -y install nginx
ADD etc/nginx.conf /etc/nginx/conf.d/submit.conf

EXPOSE 8000

CMD nginx && tail -f /var/log/nginx/access.log
