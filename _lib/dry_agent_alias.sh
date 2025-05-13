#!/usr/bin/env bash

# NB: this file is NOT sourced by the user's .bashrc
# Instead, the user should exec the _stdout_ of this script.
# e.g., `make bash-function; dry_agent_alias dry;`

# starting from the _lib directory, get the root path for dry_agent:
DRY_AGENT_GIT=$(realpath $(dirname ${BASH_SOURCE})/..)

## Output the bash function definition that the user should exec:
## Be careful to escape all $ vars except for DRY_AGENT_GIT
cat <<EOF
## Create bash functional alias for dry_agent:
dry_agent_alias() {
    ## Set the dry_agent command alias you want to use:
    local DRY_AGENT_ALIAS=\$1
    dry_agent() {
        ## Set the directory where the dry_agent git repository was cloned to:
        make --no-print-directory -C $DRY_AGENT_GIT "\$@"
    }
    eval "\$(declare -f dry_agent | sed "1s/dry_agent/\$DRY_AGENT_ALIAS/")"
    unset dry_agent
    ## dry_agent inherits the tab completion of make:
    if [[ -n \$PS1 && -f /usr/share/bash-completion/bash_completion ]]; then
        source /usr/share/bash-completion/bash_completion
        source /usr/share/bash-completion/completions/make
        complete -F \$(complete -p make | grep -oP '(?<=-F )[^ ]+' ) \$DRY_AGENT_ALIAS
    fi
}
EOF
