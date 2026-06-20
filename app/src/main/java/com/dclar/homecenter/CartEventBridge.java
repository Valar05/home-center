package com.dclar.homecenter;

import android.content.ContentResolver;
import android.content.ContentUris;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.MediaStore;

import org.json.JSONObject;

import java.io.File;
import java.io.FileWriter;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

final class CartEventBridge {
    static final String PUBLIC_EVENT_RELATIVE_PATH = Environment.DIRECTORY_DOWNLOADS + "/HomeCenter/cart-events/";
    private static final String TERMUX_RUN_COMMAND = "com.termux.RUN_COMMAND";
    private static final String TERMUX_PACKAGE = "com.termux";
    private static final String TERMUX_SH = "/data/data/com.termux/files/usr/bin/sh";
    private static final String WAKE_WORKDIR = "/storage/emulated/0/Documents/GodotProjects/home-center";
    private static final String WAKE_COMMAND = "cd " + WAKE_WORKDIR + " && python3 agent-tools/walmart-cart-agent/cart_event_wake.py";

    private CartEventBridge() {
    }

    static String currentEventPath() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            return "/storage/emulated/0/" + PUBLIC_EVENT_RELATIVE_PATH + dateStamp() + ".jsonl";
        }
        return "cart-events/" + dateStamp() + ".jsonl";
    }

    static void record(Context context, String event, JSONObject item) {
        if (context == null) {
            return;
        }
        JSONObject payload = payload(event, item);
        String line = payload.toString() + "\n";
        boolean written = writePublicEvent(context, line);
        if (!written) {
            writePrivateFallback(context, line);
        }
        wakeTermux(context, line);
    }

    private static JSONObject payload(String event, JSONObject item) {
        JSONObject obj = new JSONObject();
        try {
            obj.put("at", timeStamp());
            obj.put("event", event == null ? "" : event);
            obj.put("source", "home-center");
            obj.put("eventFile", currentEventPath());
            if (item != null) {
                obj.put("key", item.optString("key", ""));
                obj.put("item", item.optString("item", ""));
                obj.put("raw", item.optString("raw", ""));
                obj.put("status", item.optString("status", ""));
                obj.put("sku", item.optString("sku", ""));
                obj.put("productUrl", item.optString("productUrl", ""));
                obj.put("productName", item.optString("productName", ""));
                obj.put("brand", item.optString("brand", ""));
                obj.put("size", item.optString("size", ""));
                obj.put("quantity", item.optString("quantity", ""));
            }
        } catch (Exception ignored) {
        }
        return obj;
    }

    private static boolean writePublicEvent(Context context, String line) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
            return false;
        }
        try {
            Uri uri = findOrCreatePublicEventUri(context);
            if (uri == null) {
                return false;
            }
            ContentResolver resolver = context.getApplicationContext().getContentResolver();
            try (OutputStream stream = resolver.openOutputStream(uri, "wa")) {
                if (stream == null) {
                    return false;
                }
                stream.write(line.getBytes(StandardCharsets.UTF_8));
                return true;
            }
        } catch (Exception ex) {
            LocalLog.warn("cart_event", "public_write_failed " + safe(ex.getMessage()));
            return false;
        }
    }

    private static Uri findOrCreatePublicEventUri(Context context) {
        ContentResolver resolver = context.getApplicationContext().getContentResolver();
        Uri collection = MediaStore.Downloads.EXTERNAL_CONTENT_URI;
        String fileName = dateStamp() + ".jsonl";
        String[] projection = {MediaStore.Downloads._ID};
        String selection = MediaStore.Downloads.DISPLAY_NAME + "=? AND " + MediaStore.Downloads.RELATIVE_PATH + "=?";
        String[] args = {fileName, PUBLIC_EVENT_RELATIVE_PATH};
        try (Cursor cursor = resolver.query(collection, projection, selection, args, null)) {
            if (cursor != null && cursor.moveToFirst()) {
                return ContentUris.withAppendedId(collection, cursor.getLong(0));
            }
        }
        ContentValues values = new ContentValues();
        values.put(MediaStore.Downloads.DISPLAY_NAME, fileName);
        values.put(MediaStore.Downloads.MIME_TYPE, "application/x-ndjson");
        values.put(MediaStore.Downloads.RELATIVE_PATH, PUBLIC_EVENT_RELATIVE_PATH);
        return resolver.insert(collection, values);
    }

    private static void writePrivateFallback(Context context, String line) {
        try {
            File base = context.getExternalFilesDir(null);
            if (base == null) {
                base = context.getFilesDir();
            }
            File dir = new File(base, "cart-events");
            if (!dir.exists()) {
                dir.mkdirs();
            }
            try (FileWriter writer = new FileWriter(new File(dir, dateStamp() + ".jsonl"), true)) {
                writer.write(line);
            }
        } catch (Exception ex) {
            LocalLog.warn("cart_event", "private_write_failed " + safe(ex.getMessage()));
        }
    }

    private static void wakeTermux(Context context, String eventLine) {
        try {
            Intent intent = new Intent(TERMUX_RUN_COMMAND);
            intent.setPackage(TERMUX_PACKAGE);
            intent.putExtra("com.termux.RUN_COMMAND_PATH", TERMUX_SH);
            intent.putExtra("com.termux.RUN_COMMAND_ARGUMENTS", new String[]{"-lc", WAKE_COMMAND});
            intent.putExtra("com.termux.RUN_COMMAND_WORKDIR", WAKE_WORKDIR);
            intent.putExtra("com.termux.RUN_COMMAND_BACKGROUND", false);
            intent.putExtra("com.termux.RUN_COMMAND_SESSION_ACTION", "0");
            intent.putExtra("com.dclar.homecenter.CART_EVENT", eventLine);
            context.getApplicationContext().startService(intent);
            LocalLog.info("cart_event", "termux_wake_sent path=" + currentEventPath());
        } catch (Exception ex) {
            LocalLog.warn("cart_event", "termux_wake_failed " + safe(ex.getMessage()));
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
