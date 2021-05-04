How to deploy:

1. Copy env_values.txt.example to env_values.txt and set JWT_SECRET and the DB URI.
2. source config.sh
3. ./redis.sh
4. ./setupCompute.sh
5. ./setup-lb.sh
6. Then check the setup in GCP
