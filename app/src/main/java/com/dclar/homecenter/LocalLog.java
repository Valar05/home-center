package com.dclar.homecenter;

import android.content.Context;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

final class LocalLog {
    private static final Object LOCK = new Object();
    private static File logDir;

    private LocalLog() {
    }

    static void init(Context context) {
        if (context == null) {
            return;
        }
        File base = context.getExternalFilesDir(null);
        if (base == null) {
            base = context.getFilesDir();
        }
        synchronized (LOCK) {
            logDir = new File(base, "logs");
            if (!logDir.exists()) {
                logDir.mkdirs();
            }
        }
        info("app", "log_init path=" + currentLogPath());
    }

    static String currentLogPath() {
        synchronized (LOCK) {
            File dir = logDir;
            if (dir == null) {
                return "logs/not-initialized";
            }
            return new File(dir, dateStamp() + ".log").getAbsolutePath();
        }
    }

    static void info(String area, String message) {
        write("INFO", area, message, null);
    }

    static void warn(String area, String message) {
        write("WARN", area, message, null);
    }

    static void error(String area, String message, Exception ex) {
        write("ERROR", area, message, ex);
    }

    private static void write(String level, String area, String message, Exception ex) {
        synchronized (LOCK) {
            if (logDir == null) {
                return;
            }
            String line = logLine(level, area, message, ex);
            writePrivateFallback(line);
        }
    }

    private static String logLine(String level, String area, String message, Exception ex) {
        StringBuilder builder = new StringBuilder();
        builder.append(timeStamp())
                .append(" ")
                .append(level)
                .append(" ")
                .append(safe(area))
                .append(" ")
                .append(safe(message));
        if (ex != null) {
            builder.append(" exception=")
                    .append(ex.getClass().getSimpleName())
                    .append(" message=")
                    .append(safe(ex.getMessage()));
        }
        builder.append("\n");
        return builder.toString();
    }

    private static void writePrivateFallback(String line) {
        if (!logDir.exists()) {
            logDir.mkdirs();
        }
        File file = new File(logDir, dateStamp() + ".log");
        try (FileWriter writer = new FileWriter(file, true)) {
            writer.write(line);
        } catch (IOException ignored) {
        }
    }

    private static String dateStamp() {
        return new SimpleDateFormat("yyyy-MM-dd", Locale.US).format(new Date());
    }

    private static String timeStamp() {
        return new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSZ", Locale.US).format(new Date());
    }

    private static String safe(String value) {
        if (value == null) {
            return "";
        }
        return value.replace('\n', ' ').replace('\r', ' ').replaceAll("\\s+", " ").trim();
    }
}
