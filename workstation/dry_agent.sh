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
confirm() {
    local default=$1; local prompt=$2; local question=${3:-". Proceed?"}
    check_var default prompt question
    if [[ $default == "y" || $default == "yes" || $default == "true" ]]; then
        dflt="Y/n"
    else
        dflt="y/N"
    fi
    read -e -p "${prompt}${question} (${dflt}): " answer
    answer=${answer:-${default}}

    if [[ ${answer,,} == "y" || ${answer,,} == "yes" || ${answer,,} == "true" ]]; then
        return 0
    else
        fault "Not proceeding."
    fi
}
build() {
    echo "Building the container..."
    check_deps podman
    podman build -t ${CONTAINER} .
}

run() {
    check_deps podman
    check_var CONTAINER VOLUME
    if [[ -z "$@" ]]; then
        fault "No command specified to run."
    fi
    podman run --rm -it \
        --name "${CONTAINER}" \
        --hostname "${CONTAINER}" \
        -v "${VOLUME}:/root" \
        "${CONTAINER}" \
        $@
}


context() {
    run reconfigure_d.rymcg.tech
}

destroy() {
    echo
    check_deps podman
    check_var CONTAINER VOLUME
    debug_var CONTAINER
    debug_var VOLUME
    confirm no "This will destroy the agent container and all of its data"
    podman rm -f ${CONTAINER}
    podman volume rm -f ${VOLUME}
}

help() {
    echo "Usage: $0 <command>"
    echo
    echo "Commands:"
    echo "  build     Build the container image"
    echo "  context   Setup Docker context and d.rymcg.tech"
    echo "  shell     Run the container shell"
    echo "  destroy   Destroy the agent container"
    echo "  run       Run an arbitrary command in the agent container"
    echo "  help      Show this help message"
    exit 0
}

main() {
    case "$1" in
        build)
            build
            ;;
        context)
            context
            ;;
        shell)
            run bash
            ;;
        destroy)
            destroy
            ;;
        run)
            shift
            run $@
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
