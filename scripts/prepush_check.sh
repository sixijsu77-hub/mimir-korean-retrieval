#!/usr/bin/env bash
# Pre-push safety check for a public repository.
#
# Scans the files git would actually publish (tracked files only) and fails on
# anything that must not leave this machine. Run before every push.
#
# Project-specific forbidden terms (organisation names, sibling project names)
# are read from _local/forbidden-terms.txt, which is gitignored — listing them
# in this script would publish the very strings it is meant to catch. Each line
# is an extended regex, so short Latin terms can be anchored with \b to avoid
# matching inside unrelated words.
#
# Usage: bash scripts/prepush_check.sh

set -uo pipefail
cd "$(git rev-parse --show-toplevel)" || exit 2

FAIL=0
pass() { printf '  PASS  %s\n' "$1"; }
fail() { printf '  FAIL  %s\n' "$1"; FAIL=1; }
note() { printf '  NOTE  %s\n' "$1"; }

TRACKED=$(git ls-files)
SELF="scripts/prepush_check.sh"
# This script states the patterns it searches for, so scanning it with them
# reports itself. Content checks [3]-[6] therefore skip it; it is short enough
# to review by eye, and checks [1], [2], [8] and [9] still cover it.
SCAN=$(echo "$TRACKED" | grep -v "^${SELF}$" || true)
printf '=== Pre-push check: %s tracked files ===\n\n' "$(echo "$TRACKED" | wc -l)"

# 1. Files that must never be tracked, even if someone forces them in.
printf '[1] Forbidden filenames\n'
BAD_NAMES=$(echo "$TRACKED" | grep -E '(^|/)(CLAUDE\.md|CLAUDE\.local\.md|prompt\.txt|\.env|\.netrc|\.git-credentials)$|\.(key|pem|p12|pfx)$|credentials.*\.json$' || true)
if [ -n "$BAD_NAMES" ]; then fail "tracked: $BAD_NAMES"; else pass "none tracked"; fi

# 2. Project-specific forbidden terms, kept out of this script on purpose.
printf '\n[2] Forbidden terms (from _local/forbidden-terms.txt)\n'
TERMS_FILE="_local/forbidden-terms.txt"
if [ ! -f "$TERMS_FILE" ]; then
  fail "missing $TERMS_FILE — cannot check organisation or sibling-project names"
else
  HITS=0
  while IFS= read -r term; do
    [ -z "$term" ] && continue
    case "$term" in \#*) continue ;; esac
    FOUND=$(echo "$TRACKED" | xargs -r grep -I -l -i -E -- "$term" 2>/dev/null || true)
    if [ -n "$FOUND" ]; then fail "term matched in: $(echo "$FOUND" | tr '\n' ' ')"; HITS=1; fi
  done < "$TERMS_FILE"
  [ "$HITS" = "0" ] && pass "no forbidden term matched"
fi

# 3. Credentials and tokens.
printf '\n[3] Credential patterns\n'
SECRETS=$(echo "$SCAN" | xargs -r grep -I -n -E \
  'sk-[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{30,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,}|AKIA[0-9A-Z]{16}|BEGIN [A-Z ]*PRIVATE KEY|xox[baprs]-[A-Za-z0-9-]{10,}' \
  2>/dev/null || true)
if [ -n "$SECRETS" ]; then fail "$SECRETS"; else pass "no key or token pattern"; fi

# 4. Absolute local paths reveal machine layout and usernames.
printf '\n[4] Absolute local paths\n'
PATHS=$(echo "$SCAN" | xargs -r grep -I -n -E '/home/[a-z0-9_-]+|/Users/[A-Za-z0-9_-]+|C:\\\\Users\\\\' 2>/dev/null || true)
if [ -n "$PATHS" ]; then fail "$PATHS"; else pass "no absolute home path"; fi

# 5. Internal network addresses.
printf '\n[5] Internal hosts and private IPs\n'
NET=$(echo "$SCAN" | xargs -r grep -I -n -E \
  '\b(10\.[0-9]{1,3}|192\.168|172\.(1[6-9]|2[0-9]|3[01]))\.[0-9]{1,3}\.[0-9]{1,3}\b|\.internal\b|\.corp\b|\.lan\b' \
  2>/dev/null || true)
if [ -n "$NET" ]; then fail "$NET"; else pass "no private address"; fi

# 6. Email addresses other than the GitHub noreply one.
printf '\n[6] Email addresses\n'
MAIL=$(echo "$SCAN" | xargs -r grep -I -n -E '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' 2>/dev/null \
  | grep -v 'users\.noreply\.github\.com' | grep -v 'example\.\(com\|org\)' || true)
if [ -n "$MAIL" ]; then fail "$MAIL"; else pass "no bare email address"; fi

# 7. Commit identity must be the noreply address, in history as well as config.
printf '\n[7] Commit identity\n'
CFG=$(git config user.email || echo "")
case "$CFG" in
  *users.noreply.github.com) pass "user.email = $CFG" ;;
  "") fail "user.email is unset" ;;
  *) fail "user.email = $CFG (expected a GitHub noreply address)" ;;
esac
NONREPLY=$(git log --all --format='%ae%n%ce' | sort -u | grep -v 'users\.noreply\.github\.com' || true)
if [ -n "$NONREPLY" ]; then fail "history contains: $NONREPLY"; else pass "all commits use noreply"; fi

# 8. Large files bloat history permanently once pushed.
printf '\n[8] Large tracked files (> 5 MB)\n'
BIG=$(echo "$TRACKED" | xargs -r du -k 2>/dev/null | awk '$1 > 5120 {print $1" KB  "$2}' || true)
if [ -n "$BIG" ]; then fail "$BIG"; else pass "none over 5 MB"; fi

# 9. Files that .gitignore would exclude but which are tracked anyway.
printf '\n[9] Tracked files that .gitignore excludes\n'
IGN=$(git ls-files --cached --ignored --exclude-standard || true)
if [ -n "$IGN" ]; then fail "$IGN"; else pass "none"; fi

printf '\n=== Result: '
if [ "$FAIL" = "0" ]; then printf 'PASS — safe to push ===\n'; else printf 'FAIL — do not push ===\n'; fi
note "Tracked files only; untracked files are never pushed."
note "Content checks [3]-[6] skip ${SELF} — it contains the patterns themselves."
exit "$FAIL"
