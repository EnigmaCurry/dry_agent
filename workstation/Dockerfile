FROM debian:12

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        apache2-utils \
        apt-utils \
        bash \
        bsdmainutils \
        build-essential \
        ca-certificates \
        curl \
        emacs-nox \
        gettext \
        git \
        gpg \
        inotify-tools \
        jq \
        less \
        moreutils \
        openssl \
        ssh \
        sshfs \
        w3m \
        wireguard \
        wget \
        xdg-utils && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://get.docker.com | sh
RUN cd $(mktemp -d) && \
    wget -O step-cli.deb \
      https://dl.smallstep.com/cli/docs-cli-install/latest/step-cli_$(dpkg --print-architecture).deb && \
    dpkg -i step-cli.deb && \
    rm -f step-cli.deb

VOLUME /root
WORKDIR /root

ADD _config/reconfigure_d.rymcg.tech /usr/local/bin/
