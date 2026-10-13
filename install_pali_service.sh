#!/bin/bash
# The macOS installer lives in "Install Pali TTS.command" (the file shipped in the DMG).
exec bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/Install Pali TTS.command" "$@"
