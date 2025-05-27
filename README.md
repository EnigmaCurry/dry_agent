# dry_agent

`dry_agent` is a containerized workstation environment to remotely
manage Docker servers and containers. The workstation includes a
webapp GUI, SSH access, and an AI agent for the
[d.rymcg.tech](https://github.com/EnigmaCurry/d.rymcg.tech)
self-hosted Docker platform. `dry_agent` provides a central location
to manage all of your remote Docker contexts and services, and gives
you a persistent tool that you can log into from anywhere.

This software is in development and is unstable Alpha. See
[LICENSE.TXT](LICENSE.TXT), especially about the notice that this
software has no warranty. This is experimental security software that
you use at your own risk.

## Use `dry_agent` as your Docker Workstation

Within the [d.rymcg.tech](https://github.com/EnigmaCurry/d.rymcg.tech)
Docker framework, there are two main machine roles that make up your
control plane:

 * Servers - these are dedicated machines that _only_ run Docker
   containers. You treat these machines as cattle (not pets). You
   _almost never_ need to log in to the shell on a server. You will
   always remotely control these machines via (root) SSH context, from
   a workstation.

 * Workstation - these are secure machines that control your entire
   fleet or subdivision thereof. This is where you run `d.rymcg.tech`
   and/or `docker` commands _from_. Workstation machines do not run
   Docker containers themselves, but they control remote Docker
   servers that do. The workstation is the system where all of your
   declarative service config files are stored and edited. The
   workstation is the only interface you use to install services, and
   it is where you do all of your admin tasks across your fleet. One
   workstation typically controls several remote server contexts.

`dry_agent` serves the role of the Workstation, and because it's a
Podman container, it can be embedded within any other Linux host or
server.

## Features

 * `dry_agent` does not run your service containers directly -- it
   only controls _remote_ Docker servers over SSH.

 * `dry_agent` can be installed on any machine that has Podman -- it
   does not require Docker itself.

 * `dry_agent` can be installed locally for private use (localhost
   and/or SSH forward), or to a server for wider area (authenticated)
   access.

 * `dry_agent` uses Podman rootless, so it does not require root
   access to run. However, it _will_ have root access to the _remotely
   managed_ Docker servers, so the security of `dry_agent` is still
   critical!

 * `dry_agent` offers both a web application with embedded terminal
   _and_ an SSH service. It is fully usable by either method.
   
 * `dry_agent` is designed for a single admin user with remote access.
   You may log in from anywhere (according to `PUBLIC_SUBNET`), but it
   will enforce a single active session. All existing sessions are
   invalidated (logged out) whenever a new session logs in.

 * `dry_agent` has minimal host dependencies, with a
   [Makefile](Makefile) to consolidate configuration and installation
   tasks. To further improve the CLI ergonomics, a Bash function
   wrapper is included.

## Requirements

 * To serve as a `dry_agent` host, any Linux machine (or VM) may be
   used, as long as the following packages are installed:
   
   * `podman`
   * `make`
   * `sed`
   * `gawk`
   * `coreutils`
   * `gettext`
   * `xdg-utils`
   
 * You will also need one or more remote servers (or VMs) for
   `dry_agent` to manage. `dry_agent` can install Docker on them for
   you, so you just need to spin up some fresh Debian VMs to get
   started.

## Install host dependencies

### Fedora

```
sudo dnf update
sudo dnf install -y git make podman sed gawk coreutils gettext xdg-utils bash-completion
```

### Arch Linux

```
sudo pacman -Syu --noconfirm
sudo pacman -S --noconfirm git make podman sed gawk coreutils gettext xdg-utils bash-completion
```

### Debian / Ubuntu

```
sudo apt update
sudo apt install -y git make podman sed gawk coreutils gettext xdg-utils bash-completion
```

## Install dry_agent

### Create a dedicated user account for dry_agent

If you are managing production Docker servers, it is highly
recommended that you install `dry_agent` on a secure machine in a
_dedicated_ user account (i.e. Not your normal user account
[UID=1000], and definitely not root [UID=1]). Rootless Podman offers a
lot of security advantages, but only if you do your part and practice
user isolation for services. This is especially important for
protecting the data volumes where `dry_agent` stores things like SSH
keys.

#### User creation (Fedora)

As root, create the dedicated `dry_agent` user and enable systemd
lingering:

```
sudo adduser dry_agent
sudo loginctl enable-linger dry_agent
```

Enter the shell for the user:

```
sudo su -l dry_agent
```

Follow the rest of the steps in the shell of the `dry_agent` user.

### Clone repository

```
git clone \
  https://github.com/EnigmaCurry/dry_agent \
  ${HOME}/dry_agent
```

It does not matter where you clone this to, but by convention for
dedicated user accounts, we stick it directly in their home directory.

```
cd ~/dry_agent
```

### Configure

```
make config
```

Answer the questions to create your own `.env` file to configure your
instance of `dry_agent`. For each question, you may press Enter to use
the existing/default value. Your `.env` file is derived from the
[.env-dist](.env-dist) template, and its existance is ignored by
[.gitignore](.gitignore).

### Install

```
make install
```

### Two factor auth (TOTP)

```
make get-totp
```

This will print a QR code you must scan with your mobile authenticator
app (e.g. [Aegis](https://getaegis.app/)).

### Get the URL

```
make get-url
```

(If you have access to a web browser running in the same user account
as `dry_agent`, you may also run `make open` to directly open the
app.)

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

One of the main drawbacks of `make` commands are that you always need
to be in the same directory as the `Makefile` (Or, you need to specify
the directory with `-C`). 

You may want to set up this more ergonomic Bash function wrapper that
you can use from any directory. Add this to your `~/.bashrc` (or
`~/.bashrc.local` if you do it like EnigmaCurry).

```
## Create dry_agent CLI utility function with Bash completion:
DRY_AGENT_ALIAS=dry
DRY_AGENT_ROOT=${HOME}/dry_agent
eval "$(make -sC ${DRY_AGENT_ROOT} dry_agent_alias)"
dry_agent_alias $DRY_AGENT_ALIAS
unset dry_agent_alias DRY_AGENT_ROOT DRY_AGENT_ALIAS
```

You may choose whatever alias you want for the wrapper command. In the
example, `DRY_AGENT_ALIAS=dry`. You'll also need to point to the
directory where you cloned to: `DRY_AGENT_ROOT=~/dry_agent`.

Restart your shell, and you can now use the alias `dry` (from any
directory) instead of `make`. It includes the same Tab completion as
`make`.

```
## E.g., with the `dry` wrapper:
dry config
dry install
dry get-url
dry help
```

## Instant Message interface

You can access the agent from an instant message chat client (Matrix
and Discord supported). 

Enable this with the following env vars:

 * `MATRIX_HOMESERVER` - if not blank, the agent will try to connect
   to the given Matrix homeserver.
 * `MATRIX_USER` - the Matrix username the bot should connect as
 * `MATRIX_PASSWORD` - the Matrix password of the bot.
 * `DISCORD_TOKEN` - if not blank, the agent will try to connect to
   Discord with the given API token.
 * `BOT_FRIEND_IDS` - This is a list of Friend IDs that are the only
   trusted entitites that the bot will talk to. (e.g.,
   `BOT_FRIEND_IDS=@user:example.com,...`)

TODO: as of now, the only thing you can ask the bot for is to log you
in.

 * Ask "log me in" and the bot will give you a fresh login link
   (logging you out of your existing session). You can use this link
   to log in from any device, but you will also need your TOTP
   authenticator for secondary auth.

## Security

The default configuration ([.env-dist](.env-dist)) only allows to
connect via localhost. This is accomplished by the setting
`PUBLIC_SUBNET=127.0.0.1/32`. If you want to allow other hosts to
connect, you can put your desired subnet CIDR here. To allow all
networks, set `PUBLIC_SUBNET=0.0.0.0/0`. The default port is set by
`PUBLIC_PORT=8123`. 

The backend app is technically available to localhost at port
`APP_LOCALHOST_PORT` (35123), however this port is protected with
mTLS, and cannot be used except by other containers that have a signed
key. The existence of this port should be treated as an implementation
detail/consequence of Traefik host networking. All public access must
route through Traefik from `PUBLIC_SUBNET` to `PUBLIC_HOST` on
`PUBLIC_PORT` (8123).

The TLS certificate is self-signed by a local CA (Step-CA), and by
default it is certified for a period of 100 years. The CN for the
certificate is set by `PUBLIC_HOST`, which defaults to `localhost`. If
you are opening up the service to other hosts, you should set a valid
DNS name instead. Because the cert is self-signed, the _first_ time
you access the app you will need to instruct your browser to trust the
certificate. It is _not_ recommended for you to install the root CA
into your browser trust store (given a 100 year default expiration,
this would just be reckless). The intention is that you should just
pin the cert once (per browser) after verifying it manually.

To log in, the client is required to provide the one-time-use login
token. The token is only retrieved via `make get-url` or via the
configured Matrix or Discord chat bot. The token is also viewable
inside the workstation filesystem at `/app/current_token.txt`. Your
browser session will store the cookie so you will stay logged in
indefinitely. The session only allows one login. If you ask for a
fresh login link, all existing session cookies will become invalid
(logged out).

In addition to the preshared login token, you must also pass two
factor authentication with your authenticator (TOTP) device. This
second phase of authentication is controlled by a separate auth
container, outside the view of the app container.

There is an SSH server built in which is an alternative to using the
webapp. The SSH server listens only on localhost at
`SSH_LOCALHOST_PORT` (35222) and Traefik proxies this port to
`PUBLIC_SUBNET` on port `PUBLIC_SSH_PORT` (2225) for wider area
(authenticated) access.

[LiteLLM](https://github.com/BerriAI/litellm/) is deployed to proxy
between LLM service APIs (e.g. OpenAI, LM Studio). Only LiteLLM has
access to your API keys. The app Python code does not need to pass any
credentials, and so it is not made privy to them.

### Development mode

```
make dev
```

Dev mode does the following:

 * The local [app](app) source directory is bind mounted inside the
container (`/app/app`).

 * FastAPI is set to reload automatically on source file
changes (`--reload`). 

 * Vite rebuilds Svelte Kit app on source file changes.

 * The auth token is staticly set to
`correct-horse-battery-staple-this-is-for-dev-mode-only`, which is
**insecure**, but by keeping the token static makes it so you don't
have to log in again after the app reloads. TOTP secondary auth is
still required though.

 * Only in dev mode are you allowed to log in via multiple devices
   simultaneously.

 * Your workstation (tmux) sessions are unaffected by app reloads.

Dev mode is set to only run in your shell foreground (it adds the
docker arg `--rm`). To quit, press Ctrl-C several times. If you
run `make install` it will disable development mode and go back into
production mode in the background.
