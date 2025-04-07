# dry_agent

dry\_agent is a webapp GUI for the
[d.rymcg.tech](https://github.com/EnigmaCurry/d.rymcg.tech)
self-hosted Docker platform. Once you install dry\_agent on your
workstation, you can manage Docker Compose services on any of your
remote servers and/or VMs. Use dry\_agent via localhost, or open up a
port/tunnel to access it remotely.

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

## Security

dry_agent binds to `0.0.0.0:8123` by default, meaning it will be
served on all network interfaces on port 8123. If you wish to restrict
other machines from accessing dry_agent, be sure to apply appropriate
system firewall rules. (Unlike docker-compose, `podman play kube` has
no ability to restrict the network interfaces the application binds
to, so your firewall must serve this role instead.)

To login, the client is required to provide the one-time-use login
token. The token is only retrieved via `make open` (to login
automatically) and/or `make get-token` (to copy the URL manually). To
login again, you must retrieve a new token. When a new token used,
client cookies are invalidated and your existing sessions are logged
out.

dry\_agent serves HTTPS with a self-signed TLS certificate for the
given APP_HOST domain that you choose during `make config`. The
/first/ time you access the app you will need to instruct your browser
to trust the certificate.
