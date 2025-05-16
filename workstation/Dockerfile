FROM debian:12

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    apache2-utils \
    apt-utils \
    bash \
    bash-completion \
    bsdmainutils \
    build-essential \
    ca-certificates \
    curl \
    dnsutils \
    emacs-nox \
    gettext \
    git \
    gpg \
    inotify-tools \
    iputils-ping \
    iproute2 \
    jq \
    less \
    moreutils \
    neofetch \
    netcat-openbsd \
    nmap \
    locales \
    openssl \
    ssh \
    sshfs \
    tmux \
    w3m \
    wireguard \
    wget \
    whois \
    xdg-utils

RUN curl -sSL https://get.docker.com | sh
RUN cd $(mktemp -d) && \
    wget -O step-cli.deb \
      https://dl.smallstep.com/cli/docs-cli-install/latest/step-cli_$(dpkg --print-architecture).deb && \
    dpkg -i step-cli.deb && \
    rm -f step-cli.deb

WORKDIR /root

RUN mkdir -p /root/.config && \
    git clone https://github.com/EnigmaCurry/d.rymcg.tech.git \
    ~/git/vendor/enigmacurry/d.rymcg.tech
RUN YES=yes ~/git/vendor/enigmacurry/d.rymcg.tech/_scripts/install_script-wizard

ADD git-prompt.sh /root/.config/git-prompt.sh
COPY bashrc /root/.bashrc
COPY tmux.conf /root/.tmux.conf

VOLUME /root
