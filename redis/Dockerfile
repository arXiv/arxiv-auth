FROM redis

COPY redis-7000.conf /usr/local/etc/redis/7000/redis.conf
COPY redis-7001.conf /usr/local/etc/redis/7001/redis.conf
COPY redis-7002.conf /usr/local/etc/redis/7002/redis.conf

CMD redis-server /usr/local/etc/redis/7000/redis.conf & redis-server /usr/local/etc/redis/7001/redis.conf & redis-server /usr/local/etc/redis/7002/redis.conf
