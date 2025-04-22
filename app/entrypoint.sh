#!/bin/bash
set -e

# Create SSH dirs if needed
mkdir -p ${HOME}/.ssh
chmod 700 ${HOME}/.ssh

# Create ssh keypair if missing
SSH_KEY=${HOME}/.ssh/id_ed25519
if [[ ! -f ${SSH_KEY} ]]; then
    echo "[entrypoint] Generating SSH keypair..."
    ssh-keygen -q -N '' -t ed25519 -f ${SSH_KEY}
fi

# Authorize the public key ONLY if not already present
PUBKEY_CONTENT=$(cat "${SSH_KEY}.pub")
AUTHORIZED_KEYS_FILE="${HOME}/.ssh/authorized_keys"

touch "${AUTHORIZED_KEYS_FILE}"
chmod 600 "${AUTHORIZED_KEYS_FILE}"

if ! grep -Fxq "${PUBKEY_CONTENT}" "${AUTHORIZED_KEYS_FILE}"; then
    echo "${PUBKEY_CONTENT}" >> "${AUTHORIZED_KEYS_FILE}"
    echo "[entrypoint] Public key added to authorized_keys."
fi

# Harden SSH server config
echo "[entrypoint] Hardening SSH configuration..."
cat >/etc/ssh/sshd_config <<EOF
PasswordAuthentication no
ChallengeResponseAuthentication no
UsePAM no
PermitRootLogin prohibit-password
PermitEmptyPasswords no
X11Forwarding no
AllowTcpForwarding yes
Subsystem sftp internal-sftp
Port 22
EOF

# Ensure SSHD runtime dir exists
mkdir -p /var/run/sshd

# Start Supervisor
exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf
