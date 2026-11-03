#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Keep the Terminal window open on failure so the error can be read
trap 'echo ""; echo "Installation FAILED (see the message above)."; read -rp "Press Enter to close this window..." _' ERR

echo "=== Pali TTS - macOS Installer ==="
echo ""

# ── 0. Install scope ─────────────────────────────────────────────────────────
echo "Install for:"
echo "  1) Just me       (no password needed)  [default]"
echo "  2) All users     (requires admin password)"
echo ""
read -rp "Enter 1 or 2: " scope
scope="${scope:-1}"
echo ""

APP_NAME="Read Pāli Aloud"
if [ "$scope" = "2" ]; then
    APP_DIR="/Applications"
    SERVICES_BASE="/Library/Services"
    SUDO="sudo"
    echo "Installing for all users (will ask for password)..."
else
    # /Applications is writable for admin accounts; otherwise use ~/Applications
    if [ -w /Applications ]; then APP_DIR="/Applications"; else APP_DIR="$HOME/Applications"; fi
    SERVICES_BASE="$HOME/Library/Services"
    SUDO=""
    echo "Installing for current user..."
fi
APP="$APP_DIR/$APP_NAME.app"
echo ""

# ── 1. Pick the bundled Python runtime for this Mac's chip ──────────────────
# The DMG carries a self-contained Python (with Tkinter and all packages) for
# Apple Silicon and for Intel, so nothing has to be installed beforehand.
# hw.optional.arm64 is 1 on Apple Silicon even when Terminal runs under Rosetta.
if [ "$(sysctl -n hw.optional.arm64 2>/dev/null)" = "1" ]; then
    ARCH="arm64"
else
    ARCH="x86_64"
fi
BUNDLED="$SCRIPT_DIR/.runtime/$ARCH"
if [ ! -x "$BUNDLED/bin/python3" ]; then
    echo "Error: the bundled Python for $ARCH Macs is missing from this installer."
    echo "Please download PaliTTS-macOS.dmg again."
    false
fi

# ── 2. Build the app (Applications / Launchpad / Dock) ───────────────────────
# Python itself lives in Contents/MacOS so that macOS shows the app's name
# and icon in the Dock (not "python3.13"); its libraries go in Contents/lib.
STAGING=$(mktemp -d)
C="$STAGING/$APP_NAME.app/Contents"
mkdir -p "$C/MacOS" "$C/Resources"
echo "Building $APP_NAME.app ($ARCH) ..."
cp -pL "$BUNDLED/bin/python3" "$C/MacOS/python3"
ditto "$BUNDLED/lib" "$C/lib"
cp "$SCRIPT_DIR/pali_tts.py" "$C/Resources/pali_tts.py"
if [ -f "$SCRIPT_DIR/.assets/AppIcon.icns" ]; then
    cp "$SCRIPT_DIR/.assets/AppIcon.icns" "$C/Resources/AppIcon.icns"
fi
# Offline Pāli voice (Piper, Kannada male)
if [ -d "$SCRIPT_DIR/.assets/voices" ]; then
    ditto "$SCRIPT_DIR/.assets/voices" "$C/Resources/voices"
fi
VERSION=$(sed -n 's/^APP_VERSION = "\(.*\)"/\1/p' "$SCRIPT_DIR/pali_tts.py")

cat > "$C/MacOS/ReadPaliAloud" << 'LAUNCHER'
#!/bin/bash
# Started from Launchpad/Finder (no text) or by the Services menu (text on stdin)
DIR="$(cd "$(dirname "$0")" && pwd)"
if ! "$DIR/python3" -c 'import edge_tts' >/dev/null 2>&1; then
    osascript -e 'display alert "Read Pāli Aloud" message "The app is damaged. Please run the Pali TTS installer again."'
    exit 1
fi
exec "$DIR/python3" "$DIR/../Resources/pali_tts.py" "$@"
LAUNCHER
chmod +x "$C/MacOS/ReadPaliAloud"

cat > "$C/Info.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>$APP_NAME</string>
    <key>CFBundleDisplayName</key><string>$APP_NAME</string>
    <key>CFBundleIdentifier</key><string>org.sasanarakkha.readpalialoud</string>
    <key>CFBundleExecutable</key><string>ReadPaliAloud</string>
    <key>CFBundleIconFile</key><string>AppIcon</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleShortVersionString</key><string>$VERSION</string>
    <key>CFBundleVersion</key><string>$VERSION</string>
    <key>NSHumanReadableCopyright</key><string>© 2026 Āyasmā Paññādhammika · GNU AGPL 3.0 or later</string>
    <key>LSMinimumSystemVersion</key><string>10.15</string>
    <key>LSApplicationCategoryType</key><string>public.app-category.education</string>
    <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST

"$C/MacOS/python3" -c 'import edge_tts, certifi, tkinter' # sanity check
LAUNCHER_PATH="$APP/Contents/MacOS/ReadPaliAloud"
echo "Done."
echo ""

# ── 3. Stage the Services workflow ───────────────────────────────────────────
STAGE_WORKFLOW="$STAGING/Read Pali Aloud.workflow/Contents"
mkdir -p "$STAGE_WORKFLOW"

# ── 4. Stage Automator workflow ───────────────────────────────────────────────
cat > "$STAGE_WORKFLOW/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>NSServices</key>
    <array>
        <dict>
            <key>NSMenuItem</key>
            <dict>
                <key>default</key>
                <string>Read Pali Aloud</string>
            </dict>
            <key>NSMessage</key>
            <string>runWorkflowAsService</string>
            <key>NSPortName</key>
            <string>Read Pali Aloud</string>
            <key>NSSendTypes</key>
            <array>
                <string>NSStringPboardType</string>
            </array>
        </dict>
    </array>
</dict>
</plist>
PLIST

cat > "$STAGE_WORKFLOW/document.wflow" << WFLOW
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>AMApplicationBuild</key><string>521.2</string>
    <key>AMApplicationVersion</key><string>2.10</string>
    <key>AMDocumentVersion</key><string>2</string>
    <key>actions</key>
    <array>
        <dict>
            <key>action</key>
            <dict>
                <key>AMAccepts</key>
                <dict>
                    <key>Container</key><string>List</string>
                    <key>Optional</key><true/>
                    <key>Types</key>
                    <array><string>com.apple.cocoa.string</string></array>
                </dict>
                <key>AMActionVersion</key><string>2.0.3</string>
                <key>AMApplication</key><array><string>Terminal</string></array>
                <key>AMParameterProperties</key>
                <dict>
                    <key>COMMAND_STRING</key><dict/>
                    <key>CheckedForUserDefaultShell</key><dict/>
                    <key>inputMethod</key><dict/>
                    <key>shell</key><dict/>
                    <key>source</key><dict/>
                </dict>
                <key>AMProvides</key>
                <dict>
                    <key>Container</key><string>List</string>
                    <key>Types</key>
                    <array><string>com.apple.cocoa.string</string></array>
                </dict>
                <key>ActionBundlePath</key>
                <string>/System/Library/Automator/Run Shell Script.action</string>
                <key>ActionName</key><string>Run Shell Script</string>
                <key>ActionParameters</key>
                <dict>
                    <key>COMMAND_STRING</key>
                    <string>"$LAUNCHER_PATH"</string>
                    <key>CheckedForUserDefaultShell</key><true/>
                    <key>inputMethod</key><integer>0</integer>
                    <key>shell</key><string>/bin/bash</string>
                    <key>source</key><string></string>
                </dict>
                <key>BundleIdentifier</key><string>com.apple.RunShellScript</string>
                <key>CFBundleVersion</key><string>2.0.3</string>
                <key>CanShowSelectedItemsWhenRun</key><false/>
                <key>CanShowWhenRun</key><true/>
                <key>Category</key><array><string>AMCategoryUtilities</string></array>
                <key>Class Name</key><string>RunShellScriptAction</string>
                <key>InputUUID</key><string>A1B2C3D4-E5F6-7890-ABCD-EF1234567890</string>
                <key>Keywords</key><array><string>Shell</string><string>Script</string></array>
                <key>OutputUUID</key><string>B2C3D4E5-F6A7-8901-BCDE-F01234567891</string>
                <key>UUID</key><string>C3D4E5F6-A7B8-9012-CDEF-012345678892</string>
                <key>UnlocalizedApplications</key><array><string>Automator</string></array>
                <key>arguments</key>
                <dict>
                    <key>0</key>
                    <dict>
                        <key>default value</key><integer>0</integer>
                        <key>name</key><string>inputMethod</string>
                        <key>required</key><string>0</string>
                        <key>type</key><string>0</string>
                        <key>uuid</key><string>0</string>
                    </dict>
                    <key>1</key>
                    <dict>
                        <key>default value</key><string></string>
                        <key>name</key><string>source</string>
                        <key>required</key><string>0</string>
                        <key>type</key><string>0</string>
                        <key>uuid</key><string>1</string>
                    </dict>
                </dict>
                <key>isViewVisible</key><true/>
                <key>location</key><string>309.000000:253.000000</string>
                <key>nibPath</key>
                <string>/System/Library/Automator/Run Shell Script.action/Contents/Resources/English.lproj/main.nib</string>
            </dict>
            <key>isViewVisible</key><true/>
        </dict>
    </array>
    <key>connectors</key><dict/>
    <key>workflowMetaData</key>
    <dict>
        <key>applicationBundleIDsByPath</key><dict/>
        <key>applicationPaths</key><array/>
        <key>inputTypeIdentifier</key><string>com.apple.Automator.text</string>
        <key>outputTypeIdentifier</key><string>com.apple.Automator.nothing</string>
        <key>presentationMode</key><integer>15</integer>
        <key>processesInput</key><integer>0</integer>
        <key>serviceInputTypeIdentifier</key><string>com.apple.Automator.text</string>
        <key>serviceOutputTypeIdentifier</key><string>com.apple.Automator.nothing</string>
        <key>serviceProcessesInput</key><integer>0</integer>
        <key>systemImageName</key><string>NSTouchBarAudioOutputVolumeHighTemplate</string>
        <key>useAutomaticInputType</key><false/>
        <key>workflowTypeIdentifier</key><string>com.apple.Automator.servicesMenu</string>
    </dict>
</dict>
</plist>
WFLOW

# ── 5. Remove old versions ────────────────────────────────────────────────────
for dir in "$HOME/Library/Services" "/Library/Services"; do
    for old in \
        "Read Pali Aloud (Slow)" \
        "Read Pali Aloud (1.5x)" \
        "Read Pali Aloud (2x)" \
        "Save Pali as MP3" \
        "Read Pali Aloud"; do
        rm -rf "${dir}/${old}.workflow" 2>/dev/null || true
    done
done
# Before version 2 the program lived in ~/Library/Scripts/PaliTTS
rm -rf "$HOME/Library/Scripts/PaliTTS" 2>/dev/null || true
if [ "$scope" = "2" ]; then sudo rm -rf "/Library/Scripts/PaliTTS"; fi

# ── 6. Copy staged files to final location ────────────────────────────────────
$SUDO mkdir -p "$APP_DIR" "$SERVICES_BASE"
$SUDO rm -rf "$APP" "$SERVICES_BASE/Read Pali Aloud.workflow"
$SUDO ditto "$STAGING/$APP_NAME.app" "$APP"
$SUDO ditto "$STAGING/Read Pali Aloud.workflow" "$SERVICES_BASE/Read Pali Aloud.workflow"
# Downloaded files are quarantined by macOS; clear that so the app can start
$SUDO xattr -dr com.apple.quarantine "$APP" "$SERVICES_BASE/Read Pali Aloud.workflow" 2>/dev/null || true
if [ "$scope" = "2" ]; then
    sudo chmod -R a+rX "$APP" "$SERVICES_BASE/Read Pali Aloud.workflow"
fi
rm -rf "$STAGING"
# Tell Launchpad/Finder about the app and its icon
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister \
    -f "$APP" 2>/dev/null || true
echo "Installed $APP"

# ── 7. Keyboard shortcut Shift-Command-Y, refresh Services menu ──────────────
# (@ = Command, $ = Shift; can be changed in System Settings → Keyboard →
#  Keyboard Shortcuts → Services → Text)
defaults write pbs NSServicesStatus -dict-add \
    '"(null) - Read Pali Aloud - runWorkflowAsService"' \
    '{ "enabled_context_menu" = 1; "enabled_services_menu" = 1; "key_equivalent" = "@$y"; }' \
    2>/dev/null || true
# Shift-Command-Y is also macOS's own "Make New Sticky Note" service: take the
# shortcut off that one (the Stickies service itself stays in the menu)
defaults write pbs NSServicesStatus -dict-add \
    '"com.apple.Stickies - Make Sticky - makeStickyFromTextService"' \
    '{ "key_equivalent" = ""; }' \
    2>/dev/null || true
/System/Library/CoreServices/pbs -flush 2>/dev/null || true
/System/Library/CoreServices/pbs -update 2>/dev/null || true

echo ""
echo "=== Done! ==="
echo ""
echo "Two ways to use it:"
echo "  • Select text -> press Shift-Command-Y"
echo "    (or right-click -> Services -> Read Pali Aloud)"
echo "  • Open \"$APP_NAME\" from Launchpad or Applications and paste text"
echo ""
echo "If the shortcut or menu item does not work yet, log out and back in."

read -p "Press Enter to close this window..."
