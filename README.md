# dry_agent

`dry_agent` is a containerized workstation and webapp GUI for the
[d.rymcg.tech](https://github.com/EnigmaCurry/d.rymcg.tech)
self-hosted Docker platform. `dry_agent` provides a central location
to manage all of your remote Docker contexts and services.

This software is in development and is pre-alpha.

## Features

 * `dry_agent` is a Podman containerized workstation designed to
   manage _remote_ Docker hosts. It does not require Docker itself.

 * `dry_agent` can be installed either to a workstation (localhost) or
   to a server (for use by authenticated remote browser clients).

 * `dry_agent` uses Podman rootless, it does not require root access.

 * `dry_agent` offers both a web application with embedded terminal
   _and_ an SSH service. It is fully usable by either method.

 * `dry_agent` has minimal host dependencies, with a
   [Makefile](Makefile) to wrap all configuration and installation
   tasks.

## Requirements

 * A Linux machine with the following packages installed:
   
   * `podman`
   * `make`
   * `sed`
   * `gawk`
   * `coreutils`
   * `gettext`
   * `xdg-utils`
   
 * One or more remote Docker servers (or VMs) for `dry_agent` to
   manage.

## Install host dependencies

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

## Install dry_agent

### Clone repository

```
git clone https://github.com/EnigmaCurry/dry_agent
cd dry_agent
```

### Configure

```
make config
```

Answer the questions to create the `.env` file. For each question you
may press Enter to use the existing/default value.

### Install

```
make install
```

### Two factor auth (TOTP)

```
make get-totp
```

This will print a QR code you must scan with your mobile authenticator
app (e.g. Aegis).

### Open

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

### Authorize SSH service

As an alternative to using the webapp, you may wish to connect
directly to the `dry_agent` workstation via SSH:

Authorize your SSH key:

```
make ssh-authorize
```

Paste your SSH public key into the prompt.

You can SSH into the container as the user `root` on port `2225`
(`PUBLIC_SSH_PORT`).

## `dry_agent` shell function

`make` requires a bit too much boilerplate for quick CLI usage. One of
the main drawbacks of `make` is that you always need to be in the same
directory as the `Makefile` (Or specify the directory with `-C`). You
can set up a Bash function wrapper for more ergonomic usage.

You may choose whatever alias you want for the command. For example,
you might choose `dry`.

Add this to your `~/.bashrc` (or `~/.bashrc.local` if you do it like
EnigmaCurry).

```
## Create dry_agent CLI utility function with Bash completion:
DRY_AGENT_ALIAS=dry
DRY_AGENT_ROOT=~/git/vendor/enigmacurry/dry_agent
eval "$(make -sC ${DRY_AGENT_ROOT} dry_agent_alias)"
dry_agent_alias $DRY_AGENT_ALIAS
unset dry_agent_alias DRY_AGENT_ROOT DRY_AGENT_ALIAS
```

Restart your shell, and you can now use `dry` instead `make`, and you
can you do this from any directory, and with the same Tab completion
of `make`. 

```
## E.g.,
dry install
dry help
```

## Security

The default configuration ([.env-dist](.env-dist)) only allows to
connect via localhost. This is accomplished by the setting
`PUBLIC_SUBNET=127.0.0.1/32`. If you want to allow other hosts to
connect, you can put your desired subnet CIDR here. To allow all
networks, set `PUBLIC_SUBNET=0.0.0.0/0`. The default port is set by
`PUBLIC_PORT=8123`. 

The app is technically available to localhost at port
`APP_LOCALHOST_PORT` (35123), however this port requires mTLS, and
cannot be used except by other containers that have a key. All public
access must go through Traefik on `PUBLIC_SUBNET` at `PUBLIC_HOST` on
`PUBLIC_PORT` (8123).

The TLS certificate is self-signed by a local CA (Step-CA), and by
default is certified for a period of 100 years. The CN for the
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
you must retrieve a new token. When a new token is used, the client
cookies are invalidated and your existing sessions are logged out.

In addition to the preshared login token, you must also pass two
factor authentication with your authenticator (TOTP) device.

There is an SSH server built in which is an alternative to using the
webapp. The SSH server listens on localhost at `SSH_LOCALHOST_PORT`
(35222) and Traefik proxies this port to `PUBLIC_SUBNET` on port
`PUBLIC_SSH_PORT` (2225).

### Development

```
make dev
```

(This target is simply a shortcut for `make install open logs`.)
