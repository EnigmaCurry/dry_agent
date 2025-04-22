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

.PHONY: config # Interactively generate the .env file from .env-dist
config: deps
	@if [ ! -f .env-dist ]; then \
		echo "❌ Missing .env-dist template file."; \
		exit 1; \
	fi
	@if [ -f .env ]; then \
		echo "⚠️  .env already exists. Skipping creation. Run 'make clean' if you wish to delete the config."; \
	else \
		echo "🛠️  Creating .env interactively from .env-dist..."; \
		touch .env; \
		awk ' \
			BEGIN { comment = "" } \
			/^\s*#/ { \
				comment = (comment ? comment ORS : "") $$0; \
				next; \
			} \
			/^\s*$$/ { comment = ""; next } \
			/^[A-Za-z_][A-Za-z0-9_]*=/ { \
				split($$0, parts, "="); \
				var=parts[1]; \
				def=substr($$0, index($$0, "=") + 1); \
				if (comment) print "\n" comment; \
				printf "> %s [%s]: ", var, def; \
				getline input < "/dev/tty"; \
				if (input == "") input = def; \
				print var "=" input >> ".env"; \
				comment = ""; \
			} \
		' .env-dist; \
		echo -e "\n✅ .env file created successfully."; \
	fi

.PHONY: secret.yaml
secret.yaml:
	@echo "Generating secret.yaml from template..."
	@set -a; \
	source .env; \
	envsubst < secret.template.yaml > secret.yaml

.PHONY: deployment.yaml
deployment.yaml:
	@echo "Generating deployment.yaml from template..."
	@set -a; \
	source .env; \
	envsubst < deployment.template.yaml > deployment.yaml

.PHONY: install # Install the pod
install: deps expect-config secret.yaml deployment.yaml build
	@podname=dry-agent; \
	echo "🔄 Reinstalling pod $$podname..."; \
	if podman pod exists $$podname; then \
		echo "⏹️  Bringing down existing pod..."; \
		podman play kube --down deployment.yaml || true; \
		sleep 1; \
	fi; \
	if podman pod exists $$podname; then \
		echo "❗ Pod $$podname still exists — removing manually..."; \
		podman pod rm -f $$podname; \
	fi;
	podman play kube secret.yaml
	podman play kube deployment.yaml
	@${MAKE} --no-print-directory status

.PHONY: uninstall # Remove the pod (but keep the volumes)
uninstall:
	podman pod rm -f dry-agent
	podman play kube --down secret.yaml

.PHONY: destroy # Remove the pod AND delete its volumes
destroy: deps uninstall
	@read -p "⚠️  This will permanently delete all volumes from dry-agent. Are you sure? [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		for vol in $$(podman run -i --rm docker.io/mikefarah/yq '.spec.volumes[] | select(.persistentVolumeClaim) | .persistentVolumeClaim.claimName' < deployment.yaml); do \
			echo "🧹 Removing volume $$vol..."; \
			podman volume rm $$vol || true; \
		done \
	else \
		echo "❌ Aborted."; \
	fi

clean:
	rm -f secret.yaml deployment.yaml .env

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
	podman pod ps --filter name=dry-agent

.PHONY: logs # Stream logs from the pod (press CTRL+C to stop)
logs:
	@podname=dry-agent; \
	infra_id=$$(podman pod inspect $$podname --format '{{.InfraContainerID}}'); \
	for c in $$(podman pod inspect $$podname --format '{{range .Containers}}{{.ID}}{{"\n"}}{{end}}'); do \
		if [ "$$c" != "$$infra_id" ]; then \
			name=$$(podman inspect --format '{{.Name}}' $$c | sed 's|/||'); \
			echo "▶ Streaming logs for $$name..."; \
			podman logs -f $$c | sed "s/^/[$$name] /" & \
		fi; \
	done; \
	wait

.PHONY: start # Start the pod (must be installed already)
start:
	@podname=dry-agent; \
	if podman pod exists $$podname; then \
		echo "▶ Starting pod $$podname..."; \
		podman pod start $$podname; \
	else \
		echo "❌ Pod '$$podname' does not exist."; \
		exit 1; \
	fi

.PHONY: stop # Stop the pod
stop:
	@podname=dry-agent; \
	if podman pod exists $$podname; then \
		echo "⏹️  Stopping pod $$podname..."; \
		podman pod stop $$podname; \
	else \
		echo "❌ Pod '$$podname' does not exist."; \
		exit 1; \
	fi

.PHONY: up # Run pod in foreground with logs; stop on Ctrl+C
up:
	@podname=dry-agent; \
	if ! podman pod exists $$podname; then \
		echo "❌ Pod '$$podname' does not exist. Run 'make install' first."; \
		exit 1; \
	fi; \
	echo "▶ Starting pod $$podname..."; \
	podman pod start $$podname; \
	infra_id=$$(podman pod inspect $$podname --format '{{.InfraContainerID}}'); \
	pids=""; \
	for c in $$(podman pod inspect $$podname --format '{{range .Containers}}{{.ID}}{{"\n"}}{{end}}'); do \
		if [ "$$c" != "$$infra_id" ]; then \
			name=$$(podman inspect --format '{{.Name}}' $$c | sed 's|/||'); \
			echo "▶ Streaming logs for $$name..."; \
			podman logs -f $$c | sed "s/^/[$$name] /" & \
			pids="$$pids $$!"; \
		fi; \
	done; \
	trap 'echo -e "\n⏹️  Stopping pod $$podname..."; podman pod stop $$podname' INT; \
	wait $$pids

.PHONY: get-token # Get the webapp authentication token
get-token:
	@podman exec -it dry-agent-app python app/get_token.py
	@echo

.PHONY: open # Open the web app
open:
	@token_url=$$(podman exec -it dry-agent-app python app/get_token.py | grep '^http'); \
	xdg-open $$token_url


.PHONY: shell # Exec into the workstation container
shell:
	podman exec -it -w /root/git/vendor/enigmacurry/d.rymcg.tech dry-agent-app /bin/bash

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
			read -r key && grep -qxF "$$key" $$HOME/.ssh/authorized_keys || echo "$$key" >> $$HOME/.ssh/authorized_keys' <<< "$$sshkey"; \
		echo "✅ SSH key successfully authorized."; \
	fi
