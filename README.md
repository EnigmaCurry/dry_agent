# dry_agent

dry\_agent is a webapp GUI for the
[d.rymcg.tech](https://github.com/EnigmaCurry/d.rymcg.tech)
self-hosted Docker platform. Once you install dry\_agent on your
workstation, you can manage Docker Compose services on any of your
remote servers and/or VMs. Use dry\_agent via localhost, or open up a
port/tunnel to access it remotely. Secure authentication is provided
by a one-time-use login token.

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

## Configure

On your workstation:

```
make config
```

## Install

On your workstation:

```
make install
```

## Open

On your workstation:

```
make open
```

(Your default browser will automatically open via `xdg-open`)

If you are connecting remotely, retrieve the authentication URL to
manually copy it instead:

```
make get-token
```
