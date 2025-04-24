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
        tmux \
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

WORKDIR /root

RUN git clone https://github.com/EnigmaCurry/d.rymcg.tech.git \
    ~/git/vendor/enigmacurry/d.rymcg.tech
RUN YES=yes ~/git/vendor/enigmacurry/d.rymcg.tech/_scripts/install_script-wizard

COPY bashrc /root/.bashrc
VOLUME /root
