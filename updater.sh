#!/usr/bin/env bash
# Universal Orchestrator Kit updater (kit 1.0.0).
#
# Updates the kit from its GitHub repository (fast-forward only, never rewrites history).
#
#   bash UNIVERSAL-ORCHESTRATOR-KIT/updater.sh            # update to the latest RELEASE (tag vX.Y.Z)
#   bash UNIVERSAL-ORCHESTRATOR-KIT/updater.sh --edge     # follow the main branch instead (unreleased)
#   bash UNIVERSAL-ORCHESTRATOR-KIT/updater.sh --check    # show what would come, change nothing
#   bash UNIVERSAL-ORCHESTRATOR-KIT/updater.sh --no-refresh  # update the kit only
#
# Releases are the default on purpose: the update also rewrites the G1 hook, agents and policy in
# every project (`uok refresh`), so only deliberately released versions should reach them.
#
# Source of the update, in order of precedence:
#   1. $UOK_REPO           e.g. UOK_REPO=https://github.com/<owner>/UNIVERSAL-ORCHESTRATOR-KIT.git
#   2. the kit repo's existing `origin` remote
# Works wherever the kit lives (cloned into a project, or the shared ~/.uok location):
# the script updates the copy it sits in. A non-git kit copy (release zip, Finder copy)
# is repaired automatically: the folder is preserved as <kit>.backup-<ts> and replaced
# by a fresh clone of the publish repository (UOK_REPO or the canonical default).
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
EDGE=0
for arg in "$@"; do
    case "$arg" in
        --check) CHECK=1 ;;
        --no-refresh) REFRESH=0 ;;
        --edge) EDGE=1 ;;
        *) echo "updater: unknown option: $arg (use --check, --edge or --no-refresh)" >&2; exit 2 ;;
    esac
done

die() { echo "updater: $*" >&2; exit 1; }
note() { echo "updater: $*"; }

command -v git >/dev/null 2>&1 || die "git is required but not installed"

TOP="$(git -C "$KIT_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$TOP" ]; then
    # Self-repair (kit 1.2.1): this kit copy was unpacked or copied without .git (a release
    # zip, a Finder copy). No git history can be lost in such a folder, but a user may have
    # edited files in it - so the whole folder is MOVED ASIDE (never deleted) and replaced
    # by a fresh clone of the canonical publish repository. Fully reversible by hand.
    REPAIR_SRC="${UOK_REPO:-https://github.com/hardforkman/uok.git}"
    REPAIR_TS="$(date +%Y%m%d-%H%M%S)"
    note "this kit copy is not a git repository (copied as a folder); repairing automatically:"
    note "  fresh clone from: $REPAIR_SRC"
    note "  the current folder is preserved as: $KIT_DIR.backup-$REPAIR_TS"
    mv "$KIT_DIR" "$KIT_DIR.backup-$REPAIR_TS" \
        || die "could not move the old folder aside; repair manually: git clone <repo-url> <kit-dir>"
    if ! git clone --quiet "$REPAIR_SRC" "$KIT_DIR"; then
        mv "$KIT_DIR.backup-$REPAIR_TS" "$KIT_DIR"
        die "automatic repair failed (network?); the original folder was restored. \
Repair manually: git clone <repo-url> <kit-dir>"
    fi
    TOP="$(git -C "$KIT_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
    note "repaired: $KIT_DIR is now a git clone; continue with the update below."
fi
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
[ "$BRANCH" != "HEAD" ] || die "the kit is on a detached HEAD. Check out its branch first: git -C \"$KIT_DIR\" checkout main"

if [ "$EDGE" -eq 1 ]; then
    note "fetching $REMOTE ($BRANCH, unreleased)..."
    git -C "$KIT_DIR" fetch "$REMOTE" "$BRANCH"
    TARGET="refs/remotes/$REMOTE/$BRANCH"
    LABEL="$REMOTE/$BRANCH"
else
    note "fetching $REMOTE (releases)..."
    git -C "$KIT_DIR" fetch "$REMOTE" --tags
    TAG="$(git -C "$KIT_DIR" tag --list 'v[0-9]*' --sort=-v:refname | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | head -1 || true)"
    [ -n "$TAG" ] || die "no release tags (vX.Y.Z) found in $REMOTE. Use --edge to follow the $BRANCH branch."
    TARGET="refs/tags/$TAG^{commit}"
    LABEL="release $TAG"
fi

INCOMING="$(git -C "$KIT_DIR" rev-list --count HEAD.."$TARGET")"
if [ "$INCOMING" -eq 0 ]; then
    note "already up to date: at or ahead of $LABEL ($(git -C "$KIT_DIR" rev-parse --short HEAD))."
    exit 0
fi

note "$LABEL: $INCOMING commit(s) to apply:"
git -C "$KIT_DIR" log --oneline HEAD.."$TARGET" | head -20
if [ "$CHECK" -eq 1 ]; then
    note "--check: nothing changed."
    exit 0
fi

if ! git -C "$KIT_DIR" merge --ff-only "$TARGET"; then
    die "local branch diverged from $LABEL. Resolve manually:
git -C \"$KIT_DIR\" rebase $LABEL"
fi
VERSION_NOW="$(cat "$KIT_DIR/VERSION" 2>/dev/null || true)"
note "updated to $LABEL${VERSION_NOW:+ (kit $VERSION_NOW)} at $(git -C "$KIT_DIR" rev-parse --short HEAD)."
if [ "$REFRESH" -eq 1 ]; then
    command -v python3 >/dev/null 2>&1 || die "python3 is required to refresh projects (re-run later: python3 \"$KIT_DIR/uok\" refresh)"
    python3 "$KIT_DIR/uok" refresh
else
    note "projects not refreshed (--no-refresh). Run: python3 \"$KIT_DIR/uok\" refresh"
fi
