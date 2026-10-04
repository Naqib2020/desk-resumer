#!/usr/bin/env bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
APP="$DIR/apps/macos-menubar/DeskResumer.app"

if [ ! -d "$APP" ]; then
    echo "Compiling DeskResumer.app first..."
    "$DIR/apps/macos-menubar/build-macos.sh"
fi

open "$APP"
echo "⚡ DeskResumer Native Menu Bar App is now running in your top macOS menu bar!"
