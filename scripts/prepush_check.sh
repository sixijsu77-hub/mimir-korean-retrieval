#!/usr/bin/env bash
# Pre-push check. Fails if tracked content or commit messages contain anything
# that must not be published. Run before every push.
#
# Usage: bash scripts/prepush_check.sh

set -uo pipefail
cd "$(git rev-parse --show-toplevel)" || exit 2

FAIL=0
pass() { printf '  PASS  %s\n' "$1"; }
fail() { printf '  FAIL  %s\n' "$1"; FAIL=1; }

TRACKED=$(git ls-files)
SELF="scripts/prepush_check.sh"
SCAN=$(echo "$TRACKED" | grep -v "^${SELF}$" || true)
# Scope: the commits this push would publish, not what the remote already has.
MSGS=$(git log --format='%H %s%n%b' HEAD 2>/dev/null || true)
DENYLIST="_local/denylist.txt"

SECRET_RE='sk-[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{30,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,}|AKIA[0-9A-Z]{16}|BEGIN [A-Z ]*PRIVATE KEY|xox[baprs]-[A-Za-z0-9-]{10,}'
PATH_RE='/home/[a-z0-9_-]+|/Users/[A-Za-z0-9_-]+|C:\\\\Users\\\\'
NET_RE='\b(10\.[0-9]{1,3}|192\.168|172\.(1[6-9]|2[0-9]|3[01]))\.[0-9]{1,3}\.[0-9]{1,3}\b|\.internal\b|\.corp\b|\.lan\b'
MAIL_RE='[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
SESSION_RE='claude\.ai/code/session|Claude-Session|Co-Authored-By'

printf '=== Pre-push check: %s tracked files, %s commits ===\n\n' \
  "$(echo "$TRACKED" | wc -l)" "$(git rev-list --count HEAD 2>/dev/null || echo 0)"

printf '[1] Filenames\n'
BAD=$(echo "$TRACKED" | grep -E '(^|/)(CLAUDE\.md|CLAUDE\.local\.md|prompt\.txt|\.env|\.netrc|\.git-credentials)$|\.(key|pem|p12|pfx)$|credentials.*\.json$' || true)
[ -n "$BAD" ] && fail "$BAD" || pass "clean"

printf '\n[2] Denylist — tracked content\n'
if [ ! -f "$DENYLIST" ]; then
  fail "missing $DENYLIST"
else
  H=0
  while IFS= read -r t; do
    [ -z "$t" ] && continue
    case "$t" in \#*) continue ;; esac
    F=$(echo "$TRACKED" | xargs -r grep -I -l -i -E -- "$t" 2>/dev/null || true)
    [ -n "$F" ] && { fail "$(echo "$F" | tr '\n' ' ')"; H=1; }
  done < "$DENYLIST"
  [ "$H" = "0" ] && pass "clean"
fi

printf '\n[3] Denylist — commit messages\n'
if [ -f "$DENYLIST" ]; then
  H=0
  while IFS= read -r t; do
    [ -z "$t" ] && continue
    case "$t" in \#*) continue ;; esac
    M=$(echo "$MSGS" | grep -i -E -- "$t" || true)
    [ -n "$M" ] && { fail "$(echo "$M" | head -3)"; H=1; }
  done < "$DENYLIST"
  [ "$H" = "0" ] && pass "clean"
fi

printf '\n[4] Credentials\n'
S=$(echo "$SCAN" | xargs -r grep -I -n -E "$SECRET_RE" 2>/dev/null || true)
S2=$(echo "$MSGS" | grep -E "$SECRET_RE" || true)
[ -n "$S$S2" ] && fail "$S$S2" || pass "clean"

printf '\n[5] Local paths\n'
P=$(echo "$SCAN" | xargs -r grep -I -n -E "$PATH_RE" 2>/dev/null || true)
P2=$(echo "$MSGS" | grep -E "$PATH_RE" || true)
[ -n "$P$P2" ] && fail "$P$P2" || pass "clean"

printf '\n[6] Private hosts and addresses\n'
N=$(echo "$SCAN" | xargs -r grep -I -n -E "$NET_RE" 2>/dev/null || true)
N2=$(echo "$MSGS" | grep -E "$NET_RE" || true)
[ -n "$N$N2" ] && fail "$N$N2" || pass "clean"

printf '\n[7] Email addresses\n'
M=$(echo "$SCAN" | xargs -r grep -I -n -E "$MAIL_RE" 2>/dev/null \
  | grep -v 'users\.noreply\.github\.com' | grep -v 'example\.\(com\|org\)' || true)
M2=$(echo "$MSGS" | grep -E "$MAIL_RE" | grep -v 'users\.noreply\.github\.com' || true)
[ -n "$M$M2" ] && fail "$M$M2" || pass "clean"

printf '\n[7b] Session and tool trailers\n'
T=$(echo "$MSGS" | grep -E "$SESSION_RE" || true)
[ -n "$T" ] && fail "$T" || pass "clean"

printf '\n[8] Commit identity\n'
CFG=$(git config user.email || echo "")
case "$CFG" in
  *users.noreply.github.com) pass "$CFG" ;;
  *) fail "user.email=$CFG" ;;
esac
NR=$(git log --format='%ae%n%ce' HEAD | sort -u | grep -v 'users\.noreply\.github\.com' || true)
[ -n "$NR" ] && fail "$NR" || pass "history clean"

printf '\n[9] Commit message length\n'
LONG=$(git log --format='%H %s' HEAD | while read -r h s; do
  n=$(git log -1 --format='%B' "$h" | grep -c . )
  [ "$n" -gt 12 ] && echo "$(echo "$h" | cut -c1-7) ${n} lines"
done)
[ -n "$LONG" ] && fail "$LONG" || pass "all <= 12 lines"

printf '\n[10] Large files (> 5 MB)\n'
BIG=$(echo "$TRACKED" | xargs -r du -k 2>/dev/null | awk '$1 > 5120 {print $1" KB  "$2}' || true)
[ -n "$BIG" ] && fail "$BIG" || pass "clean"

printf '\n[11] Tracked but ignored\n'
IGN=$(git ls-files --cached --ignored --exclude-standard || true)
[ -n "$IGN" ] && fail "$IGN" || pass "clean"

printf '\n=== '
[ "$FAIL" = "0" ] && printf 'PASS ===\n' || printf 'FAIL — do not push ===\n'
exit "$FAIL"
