SHELL := /bin/bash

.PHONY: help # Show this help screen
help:
	@grep -h '^.PHONY: .* #' Makefile | sed 's/\.PHONY: \(.*\) # \(.*\)/make \1 \t- \2/' | expand -t20

.PHONY: deps
deps:
	@echo "🔍 Checking for required tools..."
	@missing=0; \
	for cmd in podman envsubst sed awk expand yq; do \
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

.PHONY: config # Interactively generate the .env file from .env-dist
config: deps
	@if [ ! -f .env-dist ]; then \
		echo "❌ Missing .env-dist template file."; \
		exit 1; \
	fi
	@if [ -f .env ]; then \
		echo "⚠️  .env already exists. Skipping creation. Run 'make clean' if you wish to delete it."; \
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

secret.yaml: deps secret.template.yaml config
	@echo "Generating secret.yaml from template..."
	@set -a; \
	source .env; \
	envsubst < secret.template.yaml > secret.yaml

.PHONY: install # Install the pod
install: deps secret.yaml expect-images
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
		for vol in $$(yq '.spec.volumes[] | select(.persistentVolumeClaim) | .persistentVolumeClaim.claimName' deployment.yaml); do \
			echo "🧹 Removing volume $$vol..."; \
			podman volume rm $$vol || true; \
		done \
	else \
		echo "❌ Aborted."; \
	fi

clean:
	rm -f secret.yaml .env

.PHONY: build
build: deps
	podman build -t localhost/enigmacurry/hushcrumbs https://github.com/enigmacurry/hushcrumbs.git
	podman build -t localhost/enigmacurry/workstation workstation

expect-images:
	@missing=0; \
	for img in localhost/enigmacurry/hushcrumbs localhost/enigmacurry/workstation; do \
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
