package com.dclar.homecenter;

import android.content.ContentResolver;
import android.content.ContentUris;
import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.MediaStore;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

final class LocalLog {
    private static final Object LOCK = new Object();
    private static final String PUBLIC_LOG_RELATIVE_PATH = Environment.DIRECTORY_DOWNLOADS + "/HomeCenter/logs/";
    private static File logDir;
    private static Context appContext;

    private LocalLog() {
    }

    static void init(Context context) {
        if (context == null) {
            return;
        }
        appContext = context.getApplicationContext();
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
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            return "/storage/emulated/0/" + PUBLIC_LOG_RELATIVE_PATH + dateStamp() + ".txt";
        }
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
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q && writePublicLog(line)) {
                return;
            }
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

    private static boolean writePublicLog(String line) {
        if (appContext == null) {
            return false;
        }
        try {
            Uri uri = findOrCreatePublicLogUri();
            if (uri == null) {
                return false;
            }
            ContentResolver resolver = appContext.getContentResolver();
            try (OutputStream stream = resolver.openOutputStream(uri, "wa")) {
                if (stream == null) {
                    return false;
                }
                stream.write(line.getBytes(StandardCharsets.UTF_8));
                return true;
            }
        } catch (Exception ignored) {
            return false;
        }
    }

    private static Uri findOrCreatePublicLogUri() {
        ContentResolver resolver = appContext.getContentResolver();
        Uri collection = MediaStore.Downloads.EXTERNAL_CONTENT_URI;
        String fileName = dateStamp() + ".txt";
        String[] projection = {MediaStore.Downloads._ID};
        String selection = MediaStore.Downloads.DISPLAY_NAME + "=? AND " + MediaStore.Downloads.RELATIVE_PATH + "=?";
        String[] args = {fileName, PUBLIC_LOG_RELATIVE_PATH};
        try (Cursor cursor = resolver.query(collection, projection, selection, args, null)) {
            if (cursor != null && cursor.moveToFirst()) {
                long id = cursor.getLong(0);
                return ContentUris.withAppendedId(collection, id);
            }
        }

        ContentValues values = new ContentValues();
        values.put(MediaStore.Downloads.DISPLAY_NAME, fileName);
        values.put(MediaStore.Downloads.MIME_TYPE, "text/plain");
        values.put(MediaStore.Downloads.RELATIVE_PATH, PUBLIC_LOG_RELATIVE_PATH);
        return resolver.insert(collection, values);
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
