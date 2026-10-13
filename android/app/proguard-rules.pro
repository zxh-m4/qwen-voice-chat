# 应用自己的 R8 规则。
#
# AOQ SDK 的混淆规则随 AAR 自带(app/libs/AoqClientSdk-release.aar -> proguard.txt),
# 由 AGP 自动合并,已覆盖 com.alibaba.aoq.clientsdk.** / com.aoq.** 的 keep
# 以及 native 方法名保留。这里只补两处兜底,不重复 SDK 已有的规则。

# 崩溃日志/日志文件里的类名保持可读(只有十几个小类,体积影响可忽略)
-keepnames class com.zxh.rtchat.** { *; }

# 回调接口由 SDK 侧调用,方法名保留便于排查
-keep interface com.zxh.rtchat.AoqChatManager$ChatListener { *; }
