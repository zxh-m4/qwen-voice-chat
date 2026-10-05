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

> 本项目在 **v1.3.0** 版 SDK 上验证通过;官方页面会更新最新版,如遇接口变化请对照调整。

### 文件校验(SHA-256)

下载后建议核对哈希,确认与已验证的 v1.3.0 文件一致
(Windows 下:`certutil -hashfile 文件名 SHA256`):

| 文件 | SHA-256 |
|---|---|
| `AoqClientSdk-release.aar` | `52b9463fdd1f6f5a43a27ccaf25df58bcc887224b0652d45353745a32dadb0ab` |
| `arm64-v8a/libPluginOpus.so` | `d662eb2142bcb8123e85857be78555349152826f77589c5f46e8c6b2ea4389d2` |
| `armeabi-v7a/libPluginOpus.so` | `1b5df515c1b3905fd4723554eb06fe6b4bad6bbc5a5d9cb524529d1d9f99e8c2` |

> 若哈希不一致,说明官方页面已更新文件版本——接口如有变化请对照调整;
> Gradle 发行版本身的完整性由 wrapper 的 `distributionSha256Sum` 自动校验(已配置)。

然后在仓库的 `android/` 目录下构建即可:

```bash
./gradlew assembleOfficialDebug        # Windows 用: gradlew.bat assembleOfficialDebug
```

> 构建工具(Gradle 8.14)由仓库自带的 wrapper 自动获取,无需另行安装;
> 默认经国内镜像下载,如访问不畅可把 `gradle/wrapper/gradle-wrapper.properties`
> 里的 `distributionUrl` 改回官方源 `https://services.gradle.org/distributions/`。
