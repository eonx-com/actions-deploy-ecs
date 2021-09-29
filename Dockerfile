FROM python:3.8-buster

ARG DEBIAN_FRONTEND=non-interactive
RUN apt update; \
    apt -y install apt-transport-https ca-certificates curl unzip gnupg2 software-properties-common --no-install-recommends; \
    curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add -; \
    add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/debian $(lsb_release -cs) stable"; \
    apt update; \
    apt -y install docker-ce docker-ce-cli containerd.io --no-install-recommends; \
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"; \
    unzip awscliv2.zip; \
    ./aws/install; \
    rm ./aws/install; \
    rm -rf /var/lib/apt/lists/*;
RUN wget -s https://github.com/docker/compose/releases/download/1.29.1/docker-compose-Linux-x86_64; \
    chmod +x docker-compose-Linux-x86_64; \
    mv docker-compose-Linux-x86_64 /usr/local/bin/docker-compose;


COPY ./entrypoint.sh /opt/deploy/entrypoint.sh
COPY ./src/ /opt/deploy/
RUN chmod +x /opt/deploy/entrypoint.sh

ENTRYPOINT ["/opt/deploy/entrypoint.sh"]
