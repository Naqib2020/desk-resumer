#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "🔨 Compiling DeskResumer Native macOS Menu Bar App with Apple swiftc..."
APP_BUNDLE="DeskResumer.app"
CONTENTS="$APP_BUNDLE/Contents"
MACOS="$CONTENTS/MacOS"

mkdir -p "$MACOS"
mkdir -p "$CONTENTS/Resources"

cp Info.plist "$CONTENTS/Info.plist"

swiftc -O -target arm64-apple-macosx13.0 -parse-as-library DeskResumerApp.swift -o "$MACOS/DeskResumer"

echo "✅ DeskResumer.app compiled successfully!"
