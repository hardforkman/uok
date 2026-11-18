#!/usr/bin/env bash
# Universal Orchestrator Kit updater (kit 1.0.0).
#
# Updates the kit from its GitHub repository with `git pull` (fast-forward only).
#
#   bash UNIVERSAL-ORCHESTRATOR-KIT/updater.sh            # update
#   bash UNIVERSAL-ORCHESTRATOR-KIT/updater.sh --check    # show incoming commits, change nothing
#   bash UNIVERSAL-ORCHESTRATOR-KIT/updater.sh --no-refresh  # update the kit only
#
# Source of the update, in order of precedence:
#   1. $UOK_REPO           e.g. UOK_REPO=https://github.com/<owner>/UNIVERSAL-ORCHESTRATOR-KIT.git
#   2. the kit repo's existing `origin` remote
# Works wherever the kit lives (cloned into a project, or the shared ~/.uok location):
# the script updates the copy it sits in.
#
# The kit folder is the single source: projects read core/, protocols/, templates/ from it
# directly. Each project also holds installed copies (G1 hook, agents, launcher skill,
# policy). After a successful update this script runs `uok refresh`, which re-applies the
# kit to every project recorded by `uok init` (additive, user policy kept, backups made,
# same mode/models as installed). Restart the agent sessions afterwards.
set -euo pipefail

KIT_DIR="$(cd "$(dirname "$0")" && pwd -P)"   # -P: resolve symlinks like git does
CHECK=0
REFRESH=1
for arg in "$@"; do
    case "$arg" in
        --check) CHECK=1 ;;
        --no-refresh) REFRESH=0 ;;
        *) echo "updater: unknown option: $arg (use --check or --no-refresh)" >&2; exit 2 ;;
    esac
done

die() { echo "updater: $*" >&2; exit 1; }
note() { echo "updater: $*"; }

command -v git >/dev/null 2>&1 || die "git is required but not installed"

TOP="$(git -C "$KIT_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$TOP" ] || die "this kit copy is not a git repository (it was copied as a folder). \
Re-clone it from the GitHub repository instead: git clone <repo-url> UNIVERSAL-ORCHESTRATOR-KIT"
[ "$TOP" = "$KIT_DIR" ] || die "the kit folder is inside another git repository ($TOP), \
so git pull would update that project, not the kit. Update the kit by re-cloning, or keep the \
kit as its own repository and run this script there."

# Uncommitted local edits are never clobbered silently.
if [ -n "$(git -C "$KIT_DIR" status --porcelain)" ]; then
    git -C "$KIT_DIR" status --short
    die "the kit working tree has local changes (see above). Commit or stash them first."
fi

if [ -n "${UOK_REPO:-}" ]; then
    if git -C "$KIT_DIR" remote get-url uok-update >/dev/null 2>&1; then
        git -C "$KIT_DIR" remote set-url uok-update "$UOK_REPO"
    else
        git -C "$KIT_DIR" remote add uok-update "$UOK_REPO"
    fi
    REMOTE=uok-update
else
    git -C "$KIT_DIR" remote get-url origin >/dev/null 2>&1 \
        || die "no origin remote and no UOK_REPO set. Publish the kit to GitHub, or run:
UOK_REPO=https://github.com/<owner>/UNIVERSAL-ORCHESTRATOR-KIT.git bash $0"
    REMOTE=origin
fi

BRANCH="$(git -C "$KIT_DIR" rev-parse --abbrev-ref HEAD)"
note "fetching $REMOTE ($BRANCH)…"
git -C "$KIT_DIR" fetch "$REMOTE" "$BRANCH"

INCOMING="$(git -C "$KIT_DIR" rev-list --count HEAD.."refs/remotes/$REMOTE/$BRANCH")"
if [ "$INCOMING" -eq 0 ]; then
    note "already up to date ($(git -C "$KIT_DIR" rev-parse --short HEAD))."
    exit 0
fi

git -C "$KIT_DIR" log --oneline HEAD.."refs/remotes/$REMOTE/$BRANCH" | head -20
if [ "$CHECK" -eq 1 ]; then
    note "--check: $INCOMING commit(s) available, nothing changed."
    exit 0
fi

if ! git -C "$KIT_DIR" merge --ff-only "refs/remotes/$REMOTE/$BRANCH"; then
    die "local branch diverged from $REMOTE/$BRANCH. Resolve manually:
git -C \"$KIT_DIR\" rebase $REMOTE/$BRANCH"
fi
note "updated to $(git -C "$KIT_DIR" rev-parse --short HEAD)."
if [ "$REFRESH" -eq 1 ]; then
    command -v python3 >/dev/null 2>&1 || die "python3 is required to refresh projects (re-run later: python3 \"$KIT_DIR/uok\" refresh)"
    python3 "$KIT_DIR/uok" refresh
else
    note "projects not refreshed (--no-refresh). Run: python3 \"$KIT_DIR/uok\" refresh"
fi
