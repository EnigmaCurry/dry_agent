#!/bin/bash

set -e

CONTAINER=dry_agent
VOLUME=dry_agent

stderr(){ echo "$@" >/dev/stderr; }
error(){ stderr "Error: $@"; }
fault(){ test -n "$1" && error $1; stderr "Exiting."; exit 1; }
check_var(){
    local __missing=false
    local __vars="$@"
    for __var in ${__vars}; do
        if [[ -z "${!__var}" ]]; then
            error "${__var} variable is missing."
            __missing=true
        fi
    done
    if [[ ${__missing} == true ]]; then
        fault
    fi
}
check_num(){
    local var=$1
    check_var var
    if ! [[ ${!var} =~ ^[0-9]+$ ]] ; then
        fault "${var} is not a number: '${!var}'"
    fi
}
debug_var() {
    local var=$1
    check_var var
    stderr "## DEBUG: ${var}=${!var}"
}
check_deps() {
    missing=""
    for var in "$@"; do
        #echo -n "Looking for ${var} ... " >/dev/stderr
        if ! which "${var}" >/dev/null 2>&1; then
            echo "Missing! No ${var} found in PATH." >/dev/stderr
            missing="${missing} ${var}"
        else
            #echo found $(which "${var}")
            true
        fi
    done
    if [ -n "${missing}" ]; then
        exit 1
    fi
}

build() {
    echo "Building the container..."
    check_deps podman
    podman build -t ${CONTAINER} .
}

shell() {
    check_deps podman
    check_var CONTAINER VOLUME
    podman run --rm -it \
        --name "${CONTAINER}" \
        --hostname "${CONTAINER}" \
        -v "${VOLUME}:/root" \
        "${CONTAINER}"
}

config() {
    check_deps podman
    check_var CONTAINER VOLUME
    podman run --rm -it \
        --name "${CONTAINER}" \
        --hostname "${CONTAINER}" \
        -v "${VOLUME}:/root" \
        "${CONTAINER}" \
        reconfigure_d.rymcg.tech
}

help() {
    echo "Usage: $0 <command>"
    echo
    echo "Commands:"
    echo "  build     Build the container image"
    echo "  config    Configure d.rymcg.tech"
    echo "  shell     Run the container shell"
    echo "  help      Show this help message"
    exit 0
}

main() {
    case "$1" in
        build)
            build
            ;;
        config)
            config
            ;;
        shell)
            shell
            ;;
        help|--help|-h)
            help
            ;;
        *)
            echo "Error: Unknown command '$1'"
            help
            ;;
    esac
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
