# dry_agent

TODO - finish this doc

## Install

The agent can be run on any Linux machine. You will need the following:

 * Podman (to run the agent)
 * A remote Docker server with SSH access (running on a different machine)

### Deploy dry_agent container

Use the included `dry_agent` script:

#### Build podman container

```
./dry_agent build
```

#### Setup SSH context to your Docker server

```
./dry_agent context
```

Follow the prompts to setup the connection to your Docker SSH server.

#### Setup d.rymcg.tech

```
./dry_agent run d.rymcg.tech config
```

Follow the prompts to configure d.rymcg.tech. This creates
`/root/git/vendor/enigmacurry/d.rymcg.tech/.env_{CONTEXT}` /inside/
the container volume.

 * Choose the default options for most answers.
 * `ROOT_DOMAIN` this should be the base domain for your Docker services.
 
#### Configure Traefik

```
./dry_agent run d.rymcg.tech make traefik config
```

TODO: document the traefik config
