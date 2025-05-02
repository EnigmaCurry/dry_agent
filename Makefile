SHELL := /bin/bash

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
	@if [ ! -f .env-dist ]; then \
		echo "❌ Missing .env-dist template file."; \
		exit 1; \
	fi; \
	[ -f .env ] && cp .env .env.bak || touch .env.bak; \
	echo "🛠️  Generating .env interactively (using existing values as defaults if present)..."; \
	touch .env; \
	awk ' \
		BEGIN { \
			comment = ""; \
			while ((getline line < ".env.bak") > 0) { \
				if (line ~ /^[A-Za-z_][A-Za-z0-9_]*=/) { \
					split(line, kv, "="); \
					existing[kv[1]] = substr(line, index(line, "=") + 1); \
				} \
			} \
		} \
		/^\s*#/ { comment = (comment ? comment ORS : "") $$0; next } \
		/^\s*$$/ { comment = ""; next } \
		/^[A-Za-z_][A-Za-z0-9_]*=/ { \
			split($$0, parts, "="); \
			var=parts[1]; \
			def=substr($$0, index($$0, "=") + 1); \
			if (var in existing) def = existing[var]; \
			if (comment) print "\n" comment; \
			printf "> %s [%s]: ", var, def; \
			getline input < "/dev/tty"; \
			if (input == "") input = def; \
			print var "=" input >> ".env"; \
			comment = ""; \
		} \
	' .env-dist; \
	rm -f .env.bak; \
	echo -e "\n✅ .env file configured successfully."

.PHONY: install # Install the containers
install: deps expect-config build uninstall
	@set -a; \
	source .env; \
	podman run --name dry-agent-app -d \
	       --label project=dry-agent \
           --hostname "dry-agent-$$(head /dev/urandom | tr -dc 'a-f0-9' | head -c8)" \
           -v dry-agent-workstation-data:/root \
           -e PUBLIC_HOST=$${PUBLIC_HOST} \
           -e PUBLIC_PORT=$${PUBLIC_PORT}  \
           -e OPENAI_API_KEY=$${OPENAI_API_KEY} \
           -p 127.0.0.1:$${APP_LOCALHOST_PORT}:8001 \
	       -p 127.0.0.1:$${SSH_LOCALHOST_PORT}:22 \
	       localhost/dry-agent/app; \
	podman run --name dry-agent-proxy --label project=dry-agent -d \
	       -v dry-agent-traefik-certs:/certs \
	       -e PUBLIC_SUBNET=$${PUBLIC_SUBNET} \
	       -e PUBLIC_HOST=$${PUBLIC_HOST} \
	       -e PUBLIC_PORT=$${PUBLIC_PORT} \
	       -e PUBLIC_SSH_PORT=$${PUBLIC_SSH_PORT} \
	       -e APP_LOCALHOST_PORT=$${APP_LOCALHOST_PORT} \
	       -e SSH_LOCALHOST_PORT=$${SSH_LOCALHOST_PORT} \
	       -e TLS_EXPIRES=$${TLS_EXPIRES} \
	       --network host \
	       localhost/dry-agent/traefik;
	@echo
	@sleep 2; \
	if ! podman exec dry-agent-app test -f /root/dry_agent/database/dry_agent.db; then \
	    echo "Database not found, running migration..."; \
	    make --no-print-directory migrate-db; \
	else \
	    echo "Database already exists."; \
	fi
	@echo
	@podman ps --filter "label=project=dry-agent"

.PHONY: uninstall # Remove the containers (but keep the volumes)
uninstall:
	podman rm -f dry-agent-app
	podman rm -f dry-agent-proxy

.PHONY: destroy # Remove the containers AND delete its volumes
destroy: deps uninstall
	podman volume rm -f dry-agent-workstation-data
	podman volume rm -f dry-agent-hushcrumbs-data
	podman volume rm -f dry-agent-traefik-certs

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
	podman build -t localhost/dry-agent/workstation workstation
	podman build -t localhost/dry-agent/traefik traefik
	podman build -t localhost/dry-agent/app app

expect-images:
	@missing=0; \
	for img in localhost/dry-agent/hushcrumbs localhost/dry-agent/workstation; do \
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

.PHONY: start # Start the containers (must be installed already)
start:
	podman start dry-agent-app dry-agent-proxy

.PHONY: stop # Stop the pod
stop:
	podman stop dry-agent-app dry-agent-proxy

.PHONY: get-url # Get the webapp authentication URL
get-url:
	@podman exec -it dry-agent-app python app/get_token.py
	@echo

.PHONY: open # Open the web app
open:
	@token_url=$$(podman exec -it dry-agent-app python app/get_token.py | grep '^http'); \
	xdg-open $$token_url

.PHONY: shell # Exec into the workstation container
shell:
	podman exec -it -w /root/git/vendor/enigmacurry/d.rymcg.tech dry-agent-app /bin/bash

.PHONY: traefik-shell # Exec into the traefik container
traefik-shell:
	podman exec -it dry-agent-proxy /bin/sh

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
