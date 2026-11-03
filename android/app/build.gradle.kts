// Read Pāli Aloud for Android: Kotlin user interface + the desktop app's Python code
// (pali_tts.py: language detection, Aksharamukha, Microsoft voices) run by Chaquopy.
import java.util.Base64

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.chaquo.python")
}

// One version for all platforms: APP_VERSION in pali_tts.py
val repoRoot = rootProject.projectDir.parentFile
val appVersion = Regex("""^APP_VERSION = "(.+)"""", RegexOption.MULTILINE)
    .find(repoRoot.resolve("pali_tts.py").readText())!!.groupValues[1]
// Every CI build gets a higher number, so a new APK installs over the old one
val buildNumber = (System.getenv("GITHUB_RUN_NUMBER") ?: "0").toInt()

// Private release key from GitHub secrets if set; otherwise the testing key in this
// folder (public: fine for testing, replace before publishing on Google Play).
val releaseKeystore: File? = System.getenv("ANDROID_KEYSTORE_BASE64")?.takeIf { it.isNotBlank() }?.let {
    val f = layout.buildDirectory.file("release.keystore").get().asFile
    f.parentFile.mkdirs()
    f.writeBytes(Base64.getMimeDecoder().decode(it))
    f
}

android {
    namespace = "org.sasanarakkha.readpalialoud"
    compileSdk = 35

    defaultConfig {
        applicationId = "org.sasanarakkha.readpalialoud"
        minSdk = 24
        targetSdk = 35
        versionCode = 1000 + buildNumber
        versionName = appVersion
        ndk {
            // phones (64- and 32-bit ARM) + the x86_64 emulator used by CI
            abiFilters += listOf("arm64-v8a", "armeabi-v7a", "x86_64")
        }
    }

    signingConfigs {
        create("app") {
            if (releaseKeystore != null) {
                storeFile = releaseKeystore
                storePassword = System.getenv("ANDROID_KEYSTORE_PASSWORD")
                keyAlias = System.getenv("ANDROID_KEY_ALIAS")
                keyPassword = System.getenv("ANDROID_KEY_PASSWORD")
            } else {
                storeFile = file("testing.keystore")
                storePassword = "readpali"
                keyAlias = "testing"
                keyPassword = "readpali"
            }
        }
    }

    buildTypes {
        getByName("release") {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("app")
        }
        getByName("debug") {
            signingConfig = signingConfigs.getByName("app")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        buildConfig = true
    }
}

// pali_tts.py (the desktop app) is shared: copied into the app's Python files at build time
val corePython = layout.buildDirectory.dir("generated/pycore")
val copyCore = tasks.register<Copy>("copyPaliCore") {
    from(repoRoot.resolve("pali_tts.py"))
    into(corePython)
}
tasks.named("preBuild") { dependsOn(copyCore) }

chaquopy {
    defaultConfig {
        version = "3.12"
        pip {
            // Exact list of packages, all pure Python (see requirements.txt)
            options("--no-deps")
            install("-r", "requirements.txt")
        }
    }
    sourceSets {
        getByName("main") {
            srcDir(corePython.get().asFile)
        }
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.activity:activity-ktx:1.9.3")
    implementation("com.google.android.material:material:1.12.0")
}
