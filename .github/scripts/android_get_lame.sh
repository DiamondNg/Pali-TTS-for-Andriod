#!/bin/bash
# LAME 3.100 source (MP3 encoder, LGPL-2.0-or-later) for the Android app's MP3 export.
# Built by the NDK from android/app/src/main/cpp/CMakeLists.txt; not kept in git.
set -euo pipefail
DEST=android/app/src/main/cpp/lame-3.100
SHA=ddfe36cab873794038ae2c1210557ad34857a4b6bdc515785d1da9e175b1da1e
[ -f "$DEST/include/lame.h" ] && { echo "LAME already here"; exit 0; }
tmp=$(mktemp -d)
for url in https://downloads.sourceforge.net/project/lame/lame/3.100/lame-3.100.tar.gz \
           https://deb.debian.org/debian/pool/main/l/lame/lame_3.100.orig.tar.gz; do
    for try in 1 2 3; do
        if curl -fsSL --retry 2 -o "$tmp/lame.tgz" "$url" &&
           echo "$SHA  $tmp/lame.tgz" | sha256sum -c --quiet -; then
            tar xzf "$tmp/lame.tgz" -C android/app/src/main/cpp
            echo "LAME 3.100 from $url"
            exit 0
        fi
        sleep $((try * 5))
    done
done
echo "Could not download LAME 3.100" >&2
exit 1
