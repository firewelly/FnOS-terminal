#!/bin/bash
set -e

FPK_DIR="bash_fpk"
MANIFEST="$FPK_DIR/manifest"
APP_TGZ="$FPK_DIR/app.tgz"
OUTPUT="bash.fpk"

VERSION=$(grep "^version" "$MANIFEST" | cut -d= -f2 | tr -d ' ')
MAJOR=$(echo $VERSION | cut -d. -f1)
MINOR=$(echo $VERSION | cut -d. -f2)
PATCH=$(echo $VERSION | cut -d. -f3)

BASE_MAJOR=2
BASE_MINOR=3
BASE_PATCH=0

if [ "$MAJOR" -lt "$BASE_MAJOR" ] || \
   { [ "$MAJOR" -eq "$BASE_MAJOR" ] && [ "$MINOR" -lt "$BASE_MINOR" ]; } || \
   { [ "$MAJOR" -eq "$BASE_MAJOR" ] && [ "$MINOR" -eq "$BASE_MINOR" ] && [ "$PATCH" -lt "$BASE_PATCH" ]; }; then
    NEW_VERSION="$BASE_MAJOR.$BASE_MINOR.$BASE_PATCH"
else
    PATCH=$((PATCH + 1))
    NEW_VERSION="$MAJOR.$MINOR.$PATCH"
fi

echo "版本: $VERSION -> $NEW_VERSION"

sed -i "s/^version.*=.*$/version         = $NEW_VERSION/" "$MANIFEST"

rm -f "$APP_TGZ"
tar czf "$APP_TGZ" -C bash_app .

CHECKSUM=$(sha256sum "$APP_TGZ" | cut -d' ' -f1)
sed -i "s/^checksum.*=.*$/checksum        = $CHECKSUM/" "$MANIFEST"

rm -f "$OUTPUT"
tar czf "$OUTPUT" -C "$FPK_DIR" .

echo "完成: $OUTPUT (v$NEW_VERSION)"
ls -la "$OUTPUT"
