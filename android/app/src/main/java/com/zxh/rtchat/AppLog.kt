package com.zxh.rtchat

import android.content.Context
import android.util.Log
import java.io.File
import java.io.FileWriter
import java.io.PrintWriter
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * 文件日志:写入应用私有目录,无权限要求,可经 USB/文件管理器取出。
 * 路径:/storage/emulated/0/Android/data/com.zxh.rtchat/files/logs/中英对话日志.txt
 * 文件名特意用中文+txt:手机文件管理器直接搜"中英对话日志"即可找到,可直接点开预览。
 * 同时镜像到 logcat(TAG=AoqChat)。
 */
object AppLog {
    const val TAG = "AoqChat"
    private var writer: PrintWriter? = null

    @Synchronized
    fun init(context: Context) {
        if (writer != null) return
        try {
            val dir = File(context.getExternalFilesDir(null), "logs")
            dir.mkdirs()
            writer = PrintWriter(FileWriter(File(dir, "中英对话日志.txt"), true), true)
            w("========== 启动 ==========")
        } catch (e: Exception) {
            Log.e(TAG, "日志文件打开失败(降级仅logcat): ${e.message}")
        }
    }

    @Synchronized
    fun w(msg: String) {
        val ts = SimpleDateFormat("MM-dd HH:mm:ss.SSS", Locale.US).format(Date())
        val line = "$ts  $msg"
        Log.i(TAG, line)
        writer?.println(line)
    }

    fun e(msg: String, tr: Throwable? = null) {
        w("ERROR $msg${tr?.let { " | ${it.message}" } ?: ""}")
    }
}
