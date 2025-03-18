#!/bin/bash
set -e

# Create ssh key:
SSH_KEY=${HOME}/.ssh/id_ed25519
if [[ ! -f ${SSH_KEY} ]]; then
    ssh-keygen -q -N '' -t ed25519 -f ${SSH_KEY}
fi

exec "$@"
