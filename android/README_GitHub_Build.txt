Building the Android APK via GitHub Actions
===========================================

GitHub Actions runs the build on a free Linux server in the cloud.
No Docker, no Linux machine needed. First build ~20-30 min.
Subsequent builds ~5-10 min (downloads are cached).

════════════════════════════════════════════════════════════════
ONE-TIME SETUP
════════════════════════════════════════════════════════════════

── 1. Create a free GitHub account ──────────────────────────────
  Go to https://github.com and sign up (free).

── 2. Create a new repository ───────────────────────────────────
  Click the + button (top right) -> New repository
  Name: pali-tts  (or anything you like)
  Visibility: Private  (recommended — keeps your files private)
  Click "Create repository"

── 3. Upload the files ──────────────────────────────────────────
  On the new repo page, click "uploading an existing file".
  Upload these files maintaining their folder structure:

    android/main.py
    android/buildozer.spec
    .github/workflows/build_android.yml

  Commit message: "Add Android Kivy app"
  Click "Commit changes".

════════════════════════════════════════════════════════════════
BUILDING THE APK
════════════════════════════════════════════════════════════════

── Every time you want to build ─────────────────────────────────

  1. Go to your GitHub repo in a browser
  2. Click the "Actions" tab
  3. Click "Build Android APK" in the left sidebar
  4. Click the "Run workflow" button (top right of the table)
  5. Click the green "Run workflow" button in the popup
  6. Wait 20-30 minutes (first time) or 5-10 minutes (cached)

── Download the APK ─────────────────────────────────────────────

  1. In the Actions tab, click the completed workflow run
  2. Scroll to the bottom -> "Artifacts" section
  3. Click "PaliTTS-android" to download a zip file
  4. Unzip it — inside is the APK file

── Install on your Android device ───────────────────────────────

  Transfer the APK to the phone (email it, Google Drive, USB cable)
  Tap it on the phone to install.

  First time: Android may ask you to allow "Install from unknown
  sources" — go to Settings and enable it for your file manager app.

════════════════════════════════════════════════════════════════
WHEN YOU UPDATE THE APP
════════════════════════════════════════════════════════════════

  1. Edit android/main.py on GitHub (click the file, then the
     pencil icon to edit directly in the browser)
  2. Commit the change
  3. The build starts automatically (or trigger it manually)
  4. Download and install the new APK

════════════════════════════════════════════════════════════════
FREE TIER LIMITS
════════════════════════════════════════════════════════════════

  GitHub Actions free tier:
    • 2,000 minutes/month for private repos
    • Unlimited minutes for public repos
    • First build ~30 min, cached builds ~10 min
    • Well within the free limit for occasional builds
