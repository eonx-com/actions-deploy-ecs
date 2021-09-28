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
RUN curl -s https://api.github.com/repos/docker/compose/releases/latest \
      | grep browser_download_url \
      | grep docker-compose-linux-amd64 \
      | cut -d '"' -f 4 \
      | wget -qi -; \
    chmod +x docker-compose-linux-amd64; \
    mv docker-compose-linux-amd64 /usr/local/bin/docker-compose;


COPY ./entrypoint.sh /opt/deploy/entrypoint.sh
COPY ./src/ /opt/deploy/
RUN chmod +x /opt/deploy/entrypoint.sh

ENTRYPOINT ["/opt/deploy/entrypoint.sh"]
