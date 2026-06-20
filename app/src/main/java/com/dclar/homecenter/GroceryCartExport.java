package com.dclar.homecenter;

import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Context;
import android.net.Uri;
import android.os.Environment;
import android.provider.MediaStore;

import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

final class GroceryCartExport {
    private static final String RELATIVE_PATH = Environment.DIRECTORY_DOWNLOADS + "/HomeCenter/cart-drafts/";

    private GroceryCartExport() {
    }

    static String writeDraft(Context context, String jsonText) {
        if (context == null || jsonText == null || jsonText.trim().isEmpty()) {
            return "";
        }
        String fileName = "cart-draft-" + stamp() + ".json";
        try {
            ContentResolver resolver = context.getContentResolver();
            ContentValues values = new ContentValues();
            values.put(MediaStore.Downloads.DISPLAY_NAME, fileName);
            values.put(MediaStore.Downloads.MIME_TYPE, "application/json");
            values.put(MediaStore.Downloads.RELATIVE_PATH, RELATIVE_PATH);
            Uri uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
            if (uri == null) {
                return "";
            }
            try (OutputStream stream = resolver.openOutputStream(uri, "w")) {
                if (stream == null) {
                    return "";
                }
                stream.write(jsonText.getBytes(StandardCharsets.UTF_8));
            }
            return "/storage/emulated/0/" + RELATIVE_PATH + fileName;
        } catch (Exception ex) {
            LocalLog.warn("cartDraftExport", "failed to write draft: " + ex.getMessage());
            return "";
        }
    }

    private static String stamp() {
        return new SimpleDateFormat("yyyyMMdd-HHmmss", Locale.US).format(new Date());
    }
}
