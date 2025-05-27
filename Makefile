SHELL := /bin/bash

CONTAINERS := \
	dry-agent-app \
	dry-agent-frontend \
	dry-agent-auth \
	dry-agent-bot \
	dry-agent-litellm \
	dry-agent-proxy

DATA_VOLUMES := \
	dry-agent-workstation-data \
	dry-agent-auth-token \
	dry-agent-auth-secret \
	dry-agent-bot-data

CERT_VOLUMES := \
	dry-agent-certs-CA \
	dry-agent-certs-traefik \
	dry-agent-certs-app \
	dry-agent-certs-frontend \
	dry-agent-certs-auth \
	dry-agent-certs-bot

ALL_VOLUMES := $(DATA_VOLUMES) $(CERT_VOLUMES)

PODS := dry-agent

DOTENV := ./_lib/dotenv.sh

## Prod defaults as daemon with no app volume and no extra uvicorn args:
## Dev mode overrides these:
DEPLOYMENT ?= "production"
APP_DOCKER_ARGS ?= "-d"
APP_VOLUME_ARG ?=
FRONTEND_VOLUME_ARG ?=
UVICORN_ARGS_EXTRA ?=

.PHONY: help # Show this help screen
help:
	@grep -h '^.PHONY: .* #' Makefile | sed 's/\.PHONY: \(.*\) # \(.*\)/make \1 \t- \2/' | expand -t20

.PHONY: deps
deps:
	@echo "🔍 Checking for required tools..."
	@missing=0; \
	for cmd in podman envsubst sed awk expand xdg-open; do \
		if command -v $$cmd >/dev/null 2>&1; then \
			echo "✅ $$cmd is installed"; \
		else \
			echo "❌ $$cmd is missing"; \
			missing=1; \
		fi; \
	done; \
	if [ $$missing -ne 0 ]; then \
		echo "🚨 One or more dependencies are missing. Please install them."; \
		exit 1; \
	else \
		echo "🎉 All dependencies are satisfied."; \
	fi

.PHONY: expect-config
expect-config:
	@if [ ! -f .env ]; then \
		echo "❌ Missing .env config file. Run 'make config'."; \
		exit 1; \
	fi

.PHONY: config
config: deps
	@# --- safety & sanity checks -----------------------------------------
	@if [[ "$$UID" == "1000" ]]; then \
	    echo; \
	    echo "WARNING: detected UID=1000."; \
	    echo "NOTICE: It is recommended to install dry_agent in a dedicated secondary user account."; \
	    echo; \
	fi
	@if [ ! -f .env-dist ]; then \
	    echo "❌  Missing .env-dist template file."; \
	    exit 1; \
	fi

	@# --- ensure a writable .env exists (creates it if missing) ----------
	@$(DOTENV) -f .env set >/dev/null

	@echo "🛠️  Generating .env interactively (saving after each answer)…"

	@trap 'echo; echo "⏹  Aborted – existing .env left unchanged."; exit 130' INT ; \
	\
	comment=""; \
	while IFS= read -r line || [ -n "$$line" ]; do \
	    case "$$line" in \
	        "#"* )  comment=$${comment:+$$comment$$'\n'}"$$line"; continue ;; \
	        ""    )  comment=""; continue ;; \
	    esac; \
	    key=$${line%%=*}; \
	    default=$${line#*=}; \
	    existing=`$(DOTENV) -f .env get "$$key" 2>/dev/null || true`; \
	    def=$${existing:-$$default}; \
	    if [ -n "$$comment" ]; then printf '\n%s\n' "$$comment"; fi; \
	    printf '> %s [%s]: ' "$$key" "$$def"; \
	    read -r input < /dev/tty || { echo; exit 130; }; \
	    [ -z "$$input" ] && input="$$def"; \
	    $(DOTENV) -f .env set "$$key=$$input" >/dev/null; \
	    comment=""; \
	done < .env-dist

	@echo "✅  .env file configured successfully."


.PHONY: install # Install the containers
install: deps expect-config build uninstall ca
	@echo "🏃 Spawning containers..."
	@set -a; \
	source .env; \
	podman pod create --name dry-agent \
        --hostname "dry-agent-$$(head /dev/urandom | tr -dc 'a-f0-9' | head -c8)" \
		--label project=dry-agent \
		--publish 127.0.0.1:$${APP_LOCALHOST_PORT}:8001 \
		--publish 127.0.0.1:$${AUTH_LOCALHOST_PORT}:8002 \
		--publish 127.0.0.1:$${FRONTEND_LOCALHOST_PORT}:8003 \
		--publish 127.0.0.1:$${SSH_LOCALHOST_PORT}:22 &&  \
	$(MAKE) --no-print-directory install-app &&  \
	podman run --pod dry-agent --name dry-agent-auth -d \
	       --label project=dry-agent \
	       -v dry-agent-auth-secret:/data/secret \
	       -v dry-agent-auth-token:/data/token \
	       -v dry-agent-certs-auth:/certs \
	       -e PUBLIC_HOST=$${PUBLIC_HOST} \
           -e PUBLIC_PORT=$${PUBLIC_PORT}  \
	       localhost/dry-agent/auth &&  \
	podman run --pod dry-agent --name dry-agent-bot -d \
	       --label project=dry-agent \
	       -v dry-agent-bot-data:/data \
	       -v dry-agent-certs-bot:/certs \
	       -e PUBLIC_HOST=$${PUBLIC_HOST} \
           -e PUBLIC_PORT=$${PUBLIC_PORT}  \
	       -e MATRIX_HOMESERVER=$${MATRIX_HOMESERVER} \
	       -e MATRIX_USER=$${MATRIX_USER} \
	       -e MATRIX_PASSWORD=$${MATRIX_PASSWORD} \
	       -e DISCORD_TOKEN=$${DISCORD_TOKEN} \
	       -e BOT_FRIEND_IDS=$${BOT_FRIEND_IDS} \
	       localhost/dry-agent/bot &&  \
	podman run --pod dry-agent --name dry-agent-litellm -d \
	       --label project=dry-agent \
           -e OPENAI_API_KEY=$${OPENAI_API_KEY} \
	       -e OPENAI_BASE_URL=$${OPENAI_BASE_URL} \
	       -e OPENAI_MODEL_ASSISTANT=$${OPENAI_MODEL_ASSISTANT} \
	       -e OPENAI_MODEL_LITE=$${OPENAI_MODEL_LITE} \
	       -e OPENAI_BASE_URL=$${OPENAI_BASE_URL} \
	       localhost/dry-agent/litellm &&  \
	podman run --name dry-agent-proxy --label project=dry-agent -d \
	       -v dry-agent-certs-traefik:/certs \
	       -e PUBLIC_SUBNET=$${PUBLIC_SUBNET} \
	       -e PUBLIC_HOST=$${PUBLIC_HOST} \
	       -e PUBLIC_PORT=$${PUBLIC_PORT} \
	       -e PUBLIC_SSH_PORT=$${PUBLIC_SSH_PORT} \
	       -e APP_LOCALHOST_PORT=$${APP_LOCALHOST_PORT} \
	       -e FRONTEND_LOCALHOST_PORT=$${FRONTEND_LOCALHOST_PORT} \
	       -e AUTH_LOCALHOST_PORT=$${AUTH_LOCALHOST_PORT} \
	       -e SSH_LOCALHOST_PORT=$${SSH_LOCALHOST_PORT} \
	       -e TRAEFIK_LOG_LEVEL=$${TRAEFIK_LOG_LEVEL} \
	       --network host \
	       localhost/dry-agent/traefik
	@echo
	@sleep 2;
	$(MAKE) --no-print-directory migrate
	@echo
	@podman ps --filter "label=project=dry-agent"

.PHONY: migrate
migrate:
	@if ! podman exec dry-agent-app test -f /root/dry_agent/database/dry_agent.db; then \
	    echo "🔧 Migrating database…"; \
	    make --no-print-directory migrate-db; \
	else \
	    echo "✔️ Database already in place."; \
	fi

.PHONY: install-app
install-app:
	@stdbuf -oL podman run --pod dry-agent --name dry-agent-app $(APP_DOCKER_ARGS) \
		--label project=dry-agent \
		-v dry-agent-workstation-data:/root \
		-v dry-agent-auth-token:/data/token \
		-v dry-agent-certs-app:/certs \
		$(APP_VOLUME_ARG) \
	    -e DEPLOYMENT=${DEPLOYMENT} \
		-e PUBLIC_HOST=$${PUBLIC_HOST} \
		-e PUBLIC_PORT=$${PUBLIC_PORT} \
		-e LOG_LEVEL=$${APP_LOG_LEVEL} \
	    -e UVICORN_ARGS_EXTRA="$(UVICORN_ARGS_EXTRA)" \
		-e OPENAI_BASE_URL="http://127.0.0.1:4000" \
		localhost/dry-agent/app & \
	stdbuf -oL podman run --pod dry-agent --name dry-agent-frontend $(APP_DOCKER_ARGS) \
		--label project=dry-agent \
	    -e DEPLOYMENT=${DEPLOYMENT} \
	    -v dry-agent-certs-frontend:/certs \
		$(FRONTEND_VOLUME_ARG) \
		"localhost/dry-agent/frontend:${DEPLOYMENT}" & \
	wait


.PHONY: ca # Make StepCA mTLS authority for Traefik backend
ca:
	podman build -t localhost/dry-agent/ca ca
	@set -ax; \
	source .env; \
    podman run --rm -it \
     -v dry-agent-certs-CA:/certs/CA \
	 -v dry-agent-certs-traefik:/certs/traefik \
	 -v dry-agent-certs-app:/certs/app \
	 -v dry-agent-certs-frontend:/certs/frontend \
	 -v dry-agent-certs-auth:/certs/auth \
	 -v dry-agent-certs-bot:/certs/bot \
	 -e PUBLIC_HOST=$${PUBLIC_HOST} \
	 -e TLS_EXPIRES=$${TLS_EXPIRES} \
	localhost/dry-agent/ca

.PHONY: ca-destroy # Destroy CA and all certs
ca-destroy:
	@echo "🚮 Removing certificate volumes..."
	@for v in $(CERT_VOLUMES); do \
	  podman volume rm -f $$v 2>/dev/null || true; \
	done

.PHONY: uninstall # Remove the containers (but keep the volumes)
uninstall:
	@echo "🗑 Removing containers..."
	@for c in $(CONTAINERS); do \
	  podman rm -f $$c 2>/dev/null || true; \
	done
	@echo "☠️  Removing pod..."
	@for p in $(PODS); do \
	  podman pod rm -f $$p 2>/dev/null || true; \
	done

.PHONY: destroy # Remove the containers AND delete its volumes
destroy: deps uninstall
	@echo "🚮 Removing volumes..."
	@for v in $(ALL_VOLUMES); do \
	  podman volume rm -f $$v 2>/dev/null || true; \
	done

clean:
	rm -f .env

.PHONY: build
build: deps
	if [ ! -d .hushcrumbs ]; then \
		git clone https://github.com/enigmacurry/hushcrumbs.git .hushcrumbs; \
	else \
		cd .hushcrumbs && git pull; \
	fi
	podman build -t localhost/dry-agent/hushcrumbs .hushcrumbs
	podman build -t localhost/dry-agent/litellm litellm
	podman build -t localhost/dry-agent/workstation workstation
	podman build -t localhost/dry-agent/traefik traefik
	podman build -t localhost/dry-agent/auth auth
	podman build -t localhost/dry-agent/bot bot
	podman build -t localhost/dry-agent/app app
	podman build --build-arg NGINX_CONF=nginx.conf -t "localhost/dry-agent/frontend:production" frontend
	podman build --build-arg NGINX_CONF=nginx.development.conf -t "localhost/dry-agent/frontend:development" frontend

expect-images:
	@missing=0; \
	for img in localhost/dry-agent/hushcrumbs localhost/dry-agent/workstation \
               localhost/dry-agent/traefik localhost/dry-agent/auth \
	           localhost/dry-agent/bot localhost/dry-agent/ca \
               localhost/dry-agent/app; do \
		if ! podman image exists $$img; then \
			echo "❌ Missing image: $$img"; \
			missing=1; \
		else \
			echo "✅ Found image: $$img"; \
		fi; \
	done; \
	if [ $$missing -eq 1 ]; then \
		echo "💥 One or more required images are missing."; \
		echo "👉️ You need to run: make build"; \
		exit 1; \
	fi


.PHONY: status # Show the status of the pod
status:
	@podman ps --filter "label=project=dry-agent"


.PHONY: logs # Show the app logs
logs:
	podman logs -f dry-agent-app

.PHONY: traefik-logs # Show the traefik logs
traefik-logs:
	podman logs -f dry-agent-proxy

.PHONY: frontend-logs # Show the frontend logs
frontend-logs:
	podman logs -f dry-agent-frontend

.PHONY: auth-logs # Show the auth logs
auth-logs:
	podman logs -f dry-agent-auth

.PHONY: bot-logs # Show the bot logs
bot-logs:
	podman logs -f dry-agent-bot

.PHONY: litellm-logs # Show the llm logs
litellm-logs:
	podman logs -f dry-agent-litellm

.PHONY: start # Start the containers (must be installed already)
start:
	podman start dry-agent-app dry-agent-proxy

.PHONY: stop # Stop the pod
stop:
	podman stop dry-agent-app dry-agent-proxy

.PHONY: get-url # Get the webapp authentication URL
get-url:
	@podman exec -it dry-agent-app python app/get_token.py

.PHONY: get-totp # Get the TOTP setup QR code
get-totp:
	@podman exec -it dry-agent-auth python main.py --qr
	@echo

.PHONY: open # Open the web app
open:
	@token_url=$$(podman exec -it dry-agent-app python app/get_token.py | grep '^http') && \
	xdg-open $$token_url

.PHONY: shell # Exec into the workstation container
shell:
	podman exec -it -w /root/git/vendor/enigmacurry/d.rymcg.tech dry-agent-app /bin/bash

.PHONY: frontend-shell # Exec into the frontend container
frontend-shell:
	podman exec -it dry-agent-frontend /bin/sh

.PHONY: traefik-shell # Exec into the traefik container
traefik-shell:
	podman exec -it dry-agent-proxy /bin/sh

.PHONY: bot-shell # Exec into the bot container
bot-shell:
	podman exec -it dry-agent-bot /bin/bash

.PHONY: auth-shell # Exec into the auth container
auth-shell:
	podman exec -it dry-agent-auth /bin/bash

.PHONY: litellm-shell # Exec into the litellm container
litellm-shell:
	podman exec -it dry-agent-litellm /bin/sh

.PHONY: ssh-authorize # Authorize a SSH public key
ssh-authorize:
	@echo "Paste your SSH public key to authorize access to dry_agent:"
	@read -r sshkey && \
	if [ -z "$$sshkey" ]; then \
		echo "Error: No key entered."; exit 1; \
	else \
		podman exec -i -w /root/git/vendor/enigmacurry/d.rymcg.tech dry-agent-app sh -c '\
			mkdir -p $$HOME/.ssh && \
			touch $$HOME/.ssh/authorized_keys && \
			chmod 700 $$HOME/.ssh && \
			chmod 600 $$HOME/.ssh/authorized_keys && \
			read -r key && grep -qxF "$$key" $$HOME/.ssh/authorized_keys || echo "$$key" >> $$HOME/.ssh/authorized_keys' <<< "$$sshkey" && \
		echo "✅ SSH key successfully authorized."; \
	fi

.PHONY: migrate-db # Run database migrations
migrate-db:
	podman exec -i -w /app/app dry-agent-app python -m alembic upgrade head

.PHONY: dev # Run development loop
dev:
	@podman rm -f dry-agent-app
	@podman rm -f dry-agent-frontend
	@set -a; \
	source .env; \
	$(MAKE) --no-print-directory install-app \
	    DEPLOYMENT="development" \
	    APP_DOCKER_ARGS="--rm" \
		APP_VOLUME_ARG="-v ./app/app:/app/app:Z" \
		FRONTEND_VOLUME_ARG="-v ./frontend:/app/frontend:Z" \
		UVICORN_ARGS_EXTRA="--reload"

.PHONY: dry_agent_alias # Create a Bash function for dry_agent's Makefile
dry_agent_alias:
	@_lib/dry_agent_alias.sh
