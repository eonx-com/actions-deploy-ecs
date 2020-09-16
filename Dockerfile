FROM python:3.8

COPY ./entrypoint.sh /opt/deploy/entrypoint.sh
COPY ./src/ /opt/deploy/
RUN chmod +x /opt/deploy/entrypoint.sh

ENTRYPOINT ["/opt/deploy/entrypoint.sh"]
