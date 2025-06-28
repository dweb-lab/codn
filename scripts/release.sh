#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -z "${1:-}" ]; then
  echo "Usage: ./scripts/release.sh <version> [--dry-run]"
  exit 1
fi

VERSION="$1"
TAG="v$VERSION"
DATE=$(date +"%Y-%m-%d")
REPO_URL="https://github.com/dweb-lab/codn"
DRY_RUN=${2:-}

# Detect OS for sed compatibility
if [[ "$OSTYPE" == "darwin"* ]]; then
  SED_INPLACE="sed -i ''"
else
  SED_INPLACE="sed -i"
fi

echo "🔍 Preparing release for version $VERSION (tag: $TAG) on $DATE"

# Check if tag already exists
if git tag | grep -q "^$TAG$"; then
  echo "❌ Tag $TAG already exists. Please choose a new version."
  exit 1
fi

# Determine previous version tag
PREV_TAG=$(git tag --sort=-v:refname | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | grep -v "^$TAG$" | head -n 1)
if [ -z "$PREV_TAG" ]; then
  echo "❌ Could not determine previous version tag."
  exit 1
fi

echo "📌 Comparing with previous version: $PREV_TAG"

# Step 1: Update version in source and config
echo "✏️ Updating version in source and config..."

$SED_INPLACE "s/^__version__ = \".*\"/__version__ = \"$VERSION\"/" codn/__init__.py
$SED_INPLACE "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml
$SED_INPLACE "0,/\"version\": \".*\"/s//\"version\": \"$VERSION\"/" uv.lock

# Step 2: Generate grouped changelog from git log
echo "📝 Generating grouped changelog from git log..."

RELEASE_NOTES_FILE="release-note-$VERSION.md"
TMP_CHANGELOG=$(mktemp)

git log "$PREV_TAG..HEAD" --pretty=format:"%s" |
awk '
  /^feat(\(.+\))?:/    { feats[++i] = substr($0, index($0,$2)); next }
  /^fix(\(.+\))?:/     { fixes[++j] = substr($0, index($0,$2)); next }
  /^docs(\(.+\))?:/    { docs[++k] = substr($0, index($0,$2)); next }
  /^chore(\(.+\))?:/   { chores[++l] = substr($0, index($0,$2)); next }
  /^refactor(\(.+\))?:/{ refactors[++m] = substr($0, index($0,$2)); next }
  { others[++n] = $0 }
  END {
    if (i) {
      print "### ✨ Features"
      for (a=1; a<=i; a++) print "- " feats[a]
      print ""
    }
    if (j) {
      print "### 🐛 Bug Fixes"
      for (a=1; a<=j; a++) print "- " fixes[a]
      print ""
    }
    if (k) {
      print "### 📝 Documentation"
      for (a=1; a<=k; a++) print "- " docs[a]
      print ""
    }
    if (l) {
      print "### 🔧 Chores"
      for (a=1; a<=l; a++) print "- " chores[a]
      print ""
    }
    if (m) {
      print "### 🔨 Refactoring"
      for (a=1; a<=m; a++) print "- " refactors[a]
      print ""
    }
    if (n) {
      print "### 📦 Other Changes"
      for (a=1; a<=n; a++) print "- " others[a]
      print ""
    }
  }
' > "$TMP_CHANGELOG"

cp "$TMP_CHANGELOG" "$RELEASE_NOTES_FILE"

# Step 3: Insert version notes into CHANGELOG.md after "## [Unreleased]"
echo "📘 Updating CHANGELOG.md..."

CHANGELOG_FILE="CHANGELOG.md"
TMP_NEW_SECTION=$(mktemp)

{
  echo "## [$VERSION] - $DATE"
  echo ""
  cat "$RELEASE_NOTES_FILE"
  echo ""
} > "$TMP_NEW_SECTION"

TMP_BODY=$(mktemp)
TMP_LINKS=$(mktemp)

# Separate body and footer links (footer starts at first [X.Y.Z]: or [Unreleased]: line)
LINK_LINE_NUM=$(grep -nE '^\[[^]]+\]: ' "$CHANGELOG_FILE" | head -n1 | cut -d: -f1)
if [ -z "$LINK_LINE_NUM" ]; then
  echo "❌ Could not locate footer link section."
  exit 1
fi

head -n $((LINK_LINE_NUM - 1)) "$CHANGELOG_FILE" > "$TMP_BODY"
tail -n +$LINK_LINE_NUM "$CHANGELOG_FILE" > "$TMP_LINKS"

# Insert version section under "## [Unreleased]"
TMP_BODY_UPDATED=$(mktemp)
awk -v newsection_file="$TMP_NEW_SECTION" '
  BEGIN {
    while ((getline line < newsection_file) > 0) {
      newsection_lines[++count] = line
    }
    close(newsection_file)
  }
  {
    print
    if ($0 ~ /^## \[Unreleased\]/ && !inserted) {
      for (i = 1; i <= count; i++) print newsection_lines[i]
      inserted = 1
    }
  }
' "$TMP_BODY" > "$TMP_BODY_UPDATED"

# Rebuild links: replace Unreleased, remove duplicate of this version
TMP_LINKS_UPDATED=$(mktemp)
grep -vE "^\[(Unreleased|$VERSION)\]:" "$TMP_LINKS" > "$TMP_LINKS_UPDATED"

{
  echo "[Unreleased]: $REPO_URL/compare/$TAG...HEAD"
  echo "[$VERSION]: $REPO_URL/compare/$PREV_TAG...$TAG"
  cat "$TMP_LINKS_UPDATED"
} > "$TMP_LINKS"

# Combine back
cat "$TMP_BODY_UPDATED" "$TMP_LINKS" > "$CHANGELOG_FILE"

# Clean up
rm "$TMP_NEW_SECTION" "$TMP_BODY" "$TMP_BODY_UPDATED" "$TMP_LINKS_UPDATED" "$TMP_CHANGELOG"

# Step 4: Show release notes
echo "🧾 Release notes for v$VERSION:"
echo "----"
cat "$RELEASE_NOTES_FILE"
echo "----"

if [ "$DRY_RUN" == "--dry-run" ]; then
  echo "✅ Dry-run mode. No changes committed or pushed."
  exit 0
fi

# Step 5: Commit and tag
echo "📦 Committing and tagging release..."
git add CHANGELOG.md codn/__init__.py pyproject.toml uv.lock
git commit -m "chore(release): prepare v$VERSION"
git tag "$TAG"

# Step 6: Push changes
echo "🚀 Pushing changes..."
git push origin main
git push origin "$TAG"

echo "✅ Released $TAG (compared with $PREV_TAG) successfully."
echo "📝 You can use $RELEASE_NOTES_FILE to publish a GitHub release."
