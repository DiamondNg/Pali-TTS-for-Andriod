#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

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

if [ "$scope" = "2" ]; then
    INSTALL_DIR="/Library/Scripts/PaliTTS"
    SERVICES_BASE="/Library/Services"
    echo "Installing for all users (will ask for password)..."
else
    INSTALL_DIR="$HOME/Library/Scripts/PaliTTS"
    SERVICES_BASE="$HOME/Library/Services"
    echo "Installing for current user..."
fi
echo ""

# ── 1. Locate python3 ────────────────────────────────────────────────────────
PYTHON3=""
for candidate in \
    "$(which python3 2>/dev/null)" \
    /opt/homebrew/bin/python3 \
    /usr/local/bin/python3 \
    /usr/bin/python3; do
    if [ -x "$candidate" ]; then
        PYTHON3="$candidate"
        break
    fi
done

if [ -z "$PYTHON3" ]; then
    echo "Error: python3 not found. Please install Python 3 first."
    exit 1
fi
echo "Python: $PYTHON3"

# ── 2. Install Python packages ───────────────────────────────────────────────
echo "Installing edge-tts..."
"$PYTHON3" -m pip install --quiet edge-tts
echo "Done."
echo ""

# ── 3. Stage all files in a temp directory ───────────────────────────────────
STAGING=$(mktemp -d)
STAGE_SCRIPTS="$STAGING/PaliTTS"
STAGE_WORKFLOW="$STAGING/Read Pali Aloud.workflow/Contents"
mkdir -p "$STAGE_SCRIPTS" "$STAGE_WORKFLOW"

cp "$SCRIPT_DIR/pali_tts.py" "$STAGE_SCRIPTS/pali_tts.py"

WRAPPER="$STAGE_SCRIPTS/run.sh"
FINAL_WRAPPER="$INSTALL_DIR/run.sh"
cat > "$WRAPPER" << WRAPPER_EOF
#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:\$PATH"
"$PYTHON3" "$INSTALL_DIR/pali_tts.py"
WRAPPER_EOF
chmod +x "$WRAPPER"

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
                    <string>bash "$FINAL_WRAPPER"</string>
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

# ── 5. Remove old Services from both locations ────────────────────────────────
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

# ── 6. Copy staged files to final location ────────────────────────────────────
if [ "$scope" = "2" ]; then
    sudo mkdir -p "$INSTALL_DIR" "$SERVICES_BASE"
    sudo cp -r "$STAGE_SCRIPTS/." "$INSTALL_DIR/"
    sudo chmod +x "$INSTALL_DIR/run.sh"
    sudo chmod -R a+rX "$INSTALL_DIR"
    sudo cp -r "$STAGING/Read Pali Aloud.workflow" "$SERVICES_BASE/"
    sudo chmod -R a+rX "$SERVICES_BASE/Read Pali Aloud.workflow"
else
    mkdir -p "$INSTALL_DIR" "$SERVICES_BASE"
    cp -r "$STAGE_SCRIPTS/." "$INSTALL_DIR/"
    cp -r "$STAGING/Read Pali Aloud.workflow" "$SERVICES_BASE/"
fi
rm -rf "$STAGING"
echo "Installed to $INSTALL_DIR"

# ── 7. Refresh Services menu ─────────────────────────────────────────────────
/System/Library/CoreServices/pbs -update 2>/dev/null || true

echo ""
echo "=== Done! ==="
echo ""
echo "Select any Pali text -> right-click -> Services -> Read Pali Aloud"
echo "A small window will appear to choose speed and download option."
if [ "$scope" = "2" ]; then
    echo ""
    echo "Note: each Mac user account needs Python + edge-tts installed to use this."
    echo "Other users can run 'pip install edge-tts' from their own Terminal."
fi
echo ""
echo "If the service does not appear yet, log out and back in."

read -p "Press Enter to close this window..."
