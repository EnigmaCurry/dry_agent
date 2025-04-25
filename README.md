# dry_agent

`dry_agent` is a webapp GUI for the
[d.rymcg.tech](https://github.com/EnigmaCurry/d.rymcg.tech)
self-hosted Docker platform. Once you install `dry_agent` on your
workstation, you can manage Docker Compose services on any of your
remote servers and/or VMs. 

This software is in development and is pre-alpha.

## Requirements

 * A Linux workstation with the following packages installed:
   
   * `podman`
   * `make`
   * `sed`
   * `gawk`
   * `coreutils`
   * `gettext`
   * `xdg-utils`
   
 * One or more remote Docker servers (or VMs) for dry_agent to manage.

Please notice: The dry_agent workstation does not require Docker. Only
the remote managed server(s) need Docker.

### Fedora dependencies

```
sudo dnf update
sudo dnf install -y git make podman sed gawk coreutils gettext xdg-utils bash-completion
```

### Arch Linux dependencies

```
sudo pacman -Syu --noconfirm
sudo pacman -S --noconfirm git make podman sed gawk coreutils gettext xdg-utils bash-completion
```

### Debian / Ubuntu dependencies

```
sudo apt update
sudo apt install -y git make podman sed gawk coreutils gettext xdg-utils bash-completion
```

## Clone repository

```
git clone https://github.com/EnigmaCurry/dry_agent
cd dry_agent
```

## Configure

```
make config
```

Answer the questions to create the `.env` file. For each question you
may press Enter to use the existing/default value.

## Install

```
make install
```

## Open

```
make open
```

(Your default browser will automatically open via `xdg-open`)

If you are running on a server, and you want to connect to it
remotely, retrieve the one-time-use authentication URL and manually
copy it:

```
make get-url
```

## Security

The default configuration ([.env-dist](.env-dist)) only allows to
connect via localhost. This is accomplished by the setting
`PUBLIC_SUBNET=127.0.0.1/32`. If you want to allow other hosts to
connect, you can put your desired subnet CIDR here. To allow all
networks, set `PUBLIC_SUBNET=0.0.0.0/0`. The default port is set by
`PUBLIC_PORT=8123`.

The TLS certificate is self-signed, and by default is certified for a
period of 10 years (`TLS_EXPIRES=3560` [days]). The CN for the
certificate is set by `PUBLIC_HOST`, which defaults to `localhost`. If
you are opening up the service to other hosts, you should set a valid
DNS name instead. Because the cert is self-signed, the _first_ time
you access the app you will need to instruct your browser to trust the
certificate.

To login, the client is required to provide the one-time-use login
token. The token is only retrieved via `make open` (to login
automatically) and/or `make get-url` (to copy the URL manually). The
token is also viewable inside the workstation filesystem at
`/app/current_token.txt`. Your browser session will store the cookie
so you will stay logged in indefinitely. To login with a new browser,
you must retrieve a new token. When a new token used, client cookies
are invalidated and your existing sessions are logged out.

