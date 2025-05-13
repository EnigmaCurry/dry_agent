# dry_agent

`dry_agent` is a containerized workstation, webapp GUI, and AI agent
for the [d.rymcg.tech](https://github.com/EnigmaCurry/d.rymcg.tech)
self-hosted Docker platform. `dry_agent` provides a central location
to manage all of your remote Docker contexts and services.

This software is in development and is unstable Alpha.

## Use `dry_agent` as your Docker Workstation

Within the d.rymcg.tech framework, there are two machine roles:

 * Server - these are dedicated machines that _only_ run Docker
   containers. You treat these machines as cattle (not pets). You
   _almost never_ need to log in to the shell here. You will only
   remote control these machines via SSH context on a workstation.

 * Workstation - these are machines that you run `d.rymcg.tech` and/or
   `docker` commands _from_. Workstation hosts do not run Docker
   containers themselves, but they control remote Docker servers that
   do. The workstation is the system where all your service config
   files are stored and edited. The workstation is the only interface
   you use to install services, and it is where you do all of your
   admin tasks across your fleet. One workstation typically controls
   several remote server contexts.

`dry_agent` serves the role of the Workstation, and because its a
Podman container, it can be embedded within any other Linux host or
server.

 * `dry_agent` does not run your service containers directly -- it
   only controls _remote_ Docker servers over SSH.

 * `dry_agent` can be installed on any machine that has Podman -- it
   does not require Docker itself.

 * `dry_agent` containers can be installed locally for private use or
   to a server for wider (authenticated) access.

 * `dry_agent` uses Podman rootless, so it does not require root
   access to run. It _will_ have `root` access to your _remote_ Docker
   servers though, so the security of `dry_agent` is still critical!

 * `dry_agent` offers both a web application with embedded terminal
   _and_ an SSH service. It is fully usable by either method.

 * `dry_agent` has minimal host dependencies, with a
   [Makefile](Makefile) to wrap all configuration and installation
   tasks, as well as an ergonomic Bash function wrapper with tab
   completion.

## Requirements

 * To serve as a `dry_agent` host, any Linux machine may be used, with
   the following packages installed:
   
   * `podman`
   * `make`
   * `sed`
   * `gawk`
   * `coreutils`
   * `gettext`
   * `xdg-utils`
   
 * You will also need one or more remote Docker servers (or VMs) for
   `dry_agent` to manage.

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

### Create dry_agent user account

When managing production Docker servers, it is highly recommended that
you install `dry_agent` on a secure machine in a dedicated user
account (i.e. Not UID=1000 and definitely not UID=1). User isolation
of privileged systems is a critical layer of self defense.

#### User creation on Fedora

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

### Get the URL

```
make get-url
```

If the user account you're running in has a web browser, you can also
use `make open` to directly open the app.

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

One of the main drawbacks of `make` is that you always need to be in
the same directory as the `Makefile` (Or specify the directory with
`-C`). You may want to set up this more ergonomic Bash function
wrapper that you can use from any directory.

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

You may choose whatever alias you want for the wrapper command. For
example: `DRY_AGENT_ALIAS=dry`. You'll also need to point to the
directory where you cloned to:
`DRY_AGENT_GIT=~/git/vendor/enigmacurry/dry_agent`.

Restart your shell, and you can now use `dry` instead `make`, and you
can you do this from any directory, and with the same Tab completion
as `make`.

```
## E.g., with the `dry` wrapper:
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
