import java.io.FileInputStream
import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// 签名配置:读取 keystore/keystore.properties(不随仓库分发;缺失时回退 debug 签名,方便他人构建)
val keystorePropsFile = rootProject.file("keystore/keystore.properties")
val keystoreProps = Properties()
if (keystorePropsFile.exists()) {
    keystoreProps.load(FileInputStream(keystorePropsFile))
}

android {
    namespace = "com.zxh.rtchat"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.zxh.rtchat"
        minSdk = 21
        targetSdk = 35
        versionCode = 4
        versionName = "1.3"
        ndk {
            abiFilters += listOf("armeabi-v7a", "arm64-v8a")
        }
    }

    buildFeatures {
        buildConfig = true
    }
    flavorDimensions += "edition"
    productFlavors {
        create("official") {
            dimension = "edition"
            buildConfigField("String", "BUILTIN_KEY_ENC", "\"\"")
            buildConfigField("String", "BUILTIN_WS_ENC", "\"\"")
        }
        create("trial") {
            dimension = "edition"
            // ⚠️ 警告:请勿在此填入你自己的 API Key 后分发给他人 —— 那会让使用者的全部调用费用记在你的账号上,
            // 且密钥随 APK 分发存在泄露风险。开源发布的版本保持空串(与 official 等价)。
            // 确需"内置凭据的试用版"时,请自行评估风险并使用 SecretVault 加密后填入。
            buildConfigField("String", "BUILTIN_KEY_ENC", "\"\"")
            buildConfigField("String", "BUILTIN_WS_ENC", "\"\"")
        }
    }

    signingConfigs {
        create("release") {
            if (keystorePropsFile.exists()) {
                storeFile = rootProject.file("keystore/" + keystoreProps.getProperty("storeFileName"))
                storePassword = keystoreProps.getProperty("storePassword")
                keyAlias = keystoreProps.getProperty("keyAlias")
                keyPassword = keystoreProps.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = if (keystorePropsFile.exists()) {
                signingConfigs.getByName("release")
            } else {
                println("WARNING: keystore/keystore.properties not found — release build will be signed with the DEBUG key (NOT for distribution / 不可用于正式分发).")
                signingConfigs.getByName("debug")
            }
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    sourceSets {
        getByName("main") {
            jniLibs.srcDirs("libs")
        }
    }
    packaging {
        jniLibs {
            pickFirsts += "lib/*/*.so"
        }
    }
}

dependencies {
    implementation(fileTree(mapOf("dir" to "libs", "include" to listOf("*.aar"))))
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
}
