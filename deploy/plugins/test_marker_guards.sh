#!/usr/bin/env bash
# Regression test for the install_plugin.sh marker guards.
#
# Each install step is guarded by a marker file under /jadawel/container_markers/
# so a container restart does not repeat it. The web-frontend runtime-setup guard
# was inverted (`-f` where the other three use `! -f`), which meant a plugin's
# web-frontend/runtime_setup.sh never ran on a fresh install and re-ran on every
# start once it had. See PATCHES.md (2026-09-05).
#
# The guard expressions are read out of install_plugin.sh rather than copied, so
# re-inverting one fails this test.
#
# Usage: deploy/plugins/test_marker_guards.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_SCRIPT="$SCRIPT_DIR/install_plugin.sh"
MARKER="$(mktemp -u)"
failures=0

# Pull a guard's condition out of install_plugin.sh by its marker variable name.
extract_guard() {
    local marker_var="$1" line
    line="$(grep -m1 -F "\$$marker_var\"" "$INSTALL_SCRIPT" | grep -F 'if [[')" || return 1
    # strip the leading `if [[` and the trailing `]]; then`, leaving the condition
    line="${line#*if \[\[ }"
    line="${line%% \]\]; then}"
    # point the condition at our temp marker instead of the container path
    echo "${line//\$$marker_var/\$MARKER}"
}

# assert <guard> <marker_exists> <runtime> <overwrite> <expected> <description>
assert_guard() {
    local guard="$1" marker="$2" runtime="$3" overwrite="$4" expected="$5" desc="$6"
    if [[ "$marker" == "present" ]]; then touch "$MARKER"; else rm -f "$MARKER"; fi

    local actual
    if eval "[[ $guard ]]"; then actual="run"; else actual="skip"; fi

    if [[ "$actual" == "$expected" ]]; then
        printf '  PASS  %s\n' "$desc"
    else
        printf '  FAIL  %s — expected %s, got %s\n' "$desc" "$expected" "$actual"
        failures=$((failures + 1))
    fi
}

for half in BACKEND WEBFRONTEND; do
    marker_var="${half}_RUNTIME_SETUP_MARKER"
    guard="$(extract_guard "$marker_var")"
    if [[ -z "$guard" ]]; then
        echo "  FAIL  could not find the guard for $marker_var in install_plugin.sh"
        failures=$((failures + 1))
        continue
    fi

    echo "$half runtime setup — $guard"
    assert_guard "$guard" absent  true  false run  "fresh install runs runtime_setup.sh"
    assert_guard "$guard" present true  false skip "an already-set-up container skips it"
    assert_guard "$guard" present true  true  run  "--overwrite forces it to run again"
    assert_guard "$guard" absent  false false skip "without --runtime it never runs"
    assert_guard "$guard" present false true  skip "--overwrite does not defeat the --runtime gate"
    echo
done

rm -f "$MARKER"

if [[ $failures -gt 0 ]]; then
    echo "FAILED: $failures assertion(s)"
    exit 1
fi
echo "All marker guard assertions passed."
