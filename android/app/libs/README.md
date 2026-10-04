# 第三方 SDK 放置说明(本仓库不含二进制)

本项目使用阿里云百炼 **AOQ Client SDK**(闭源分发),为避免再分发问题,仓库不包含:

- `AoqClientSdk-release.aar`
- `libPluginOpus.so`(armeabi-v7a / arm64-v8a)

## 获取方式

1. 访问阿里云百炼官方文档「实时通话 SDK 下载」页面(搜"百炼 realtime SDK 下载");
2. 下载 Android 版:`AoqClientSdk-release.aar` 与 `libPluginOpus.zip`;
3. 放置到本目录:

```
app/libs/
├── AoqClientSdk-release.aar          (来自官方下载)
├── arm64-v8a/libPluginOpus.so        (解压 libPluginOpus.zip 得到)
└── armeabi-v7a/libPluginOpus.so
```

然后在仓库的 `android/` 目录下构建即可:

```bash
./gradlew assembleOfficialDebug        # Windows 用: gradlew.bat assembleOfficialDebug
```

> 构建工具(Gradle 8.14)由仓库自带的 wrapper 自动获取,无需另行安装;
> 默认经国内镜像下载,如访问不畅可把 `gradle/wrapper/gradle-wrapper.properties`
> 里的 `distributionUrl` 改回官方源 `https://services.gradle.org/distributions/`。
