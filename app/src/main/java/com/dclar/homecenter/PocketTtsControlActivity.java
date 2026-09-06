package com.dclar.homecenter;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.TextUtils;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class PocketTtsControlActivity extends Activity {
    private static final String SERVICE_BASE = "http://localhost:10205";
    private static final int COLOR_BACKGROUND = Color.parseColor("#121212");
    private static final int COLOR_SURFACE = Color.parseColor("#242424");
    private static final int COLOR_TEXT = Color.WHITE;
    private static final int COLOR_SECONDARY = Color.parseColor("#C7C7C7");
    private static final int COLOR_GOOD = Color.parseColor("#8BC34A");
    private static final int COLOR_ACTION = Color.parseColor("#6AA9FF");
    private static final int COLOR_BAD = Color.parseColor("#E57373");

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final Handler main = new Handler(Looper.getMainLooper());
    private EditText textInput;
    private TextView stateView;
    private TextView receiptView;
    private Button doctorButton;
    private Button speakButton;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setTitle("Pocket TTS");
        buildUi();
        runDoctor();
    }

    private void buildUi() {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(COLOR_BACKGROUND);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(18), dp(18), dp(28));
        root.setBackgroundColor(COLOR_BACKGROUND);
        scroll.addView(root, new ScrollView.LayoutParams(
                ScrollView.LayoutParams.MATCH_PARENT,
                ScrollView.LayoutParams.WRAP_CONTENT));

        TextView title = new TextView(this);
        title.setText("Pocket TTS");
        title.setTextSize(28);
        title.setTextColor(COLOR_TEXT);
        title.setGravity(Gravity.START);
        root.addView(title, matchWrap());

        TextView subtitle = new TextView(this);
        subtitle.setText("Local Pocket engine → Home Center playback → verified completion");
        subtitle.setTextSize(14);
        subtitle.setTextColor(COLOR_SECONDARY);
        subtitle.setPadding(0, dp(4), 0, dp(18));
        root.addView(subtitle, matchWrap());

        stateView = new TextView(this);
        stateView.setText("Checking localhost service…");
        stateView.setTextSize(17);
        stateView.setTextColor(COLOR_SECONDARY);
        stateView.setPadding(dp(14), dp(14), dp(14), dp(14));
        stateView.setBackgroundColor(COLOR_SURFACE);
        stateView.setContentDescription("Pocket TTS status");
        root.addView(stateView, matchWrap());

        textInput = new EditText(this);
        textInput.setHint("What should Pocket TTS say?");
        textInput.setHintTextColor(COLOR_SECONDARY);
        textInput.setTextColor(COLOR_TEXT);
        textInput.setText("Pocket TTS resurrection canary. The deterministic voice lane is alive.");
        textInput.setMinLines(3);
        textInput.setMaxLines(8);
        textInput.setGravity(Gravity.TOP | Gravity.START);
        textInput.setPadding(dp(14), dp(14), dp(14), dp(14));
        textInput.setBackgroundColor(COLOR_SURFACE);
        textInput.setContentDescription("Text for Pocket TTS to speak");
        LinearLayout.LayoutParams inputParams = matchWrap();
        inputParams.setMargins(0, dp(18), 0, dp(12));
        root.addView(textInput, inputParams);

        doctorButton = new Button(this);
        doctorButton.setText("DOCTOR");
        doctorButton.setTextSize(18);
        doctorButton.setAllCaps(false);
        doctorButton.setTextColor(Color.BLACK);
        doctorButton.setBackgroundColor(COLOR_GOOD);
        doctorButton.setContentDescription("Check Pocket TTS engine, Home Center playback, and localhost service");
        doctorButton.setOnClickListener(v -> runDoctor());
        root.addView(doctorButton, matchHeight(dp(60)));

        speakButton = new Button(this);
        speakButton.setText("SPEAK");
        speakButton.setTextSize(22);
        speakButton.setAllCaps(false);
        speakButton.setTextColor(Color.BLACK);
        speakButton.setBackgroundColor(COLOR_ACTION);
        speakButton.setContentDescription("Speak this text with Pocket TTS and verify playback completion");
        speakButton.setOnClickListener(v -> runSpeak());
        LinearLayout.LayoutParams speakParams = matchHeight(dp(72));
        speakParams.setMargins(0, dp(10), 0, dp(18));
        root.addView(speakButton, speakParams);

        TextView receiptTitle = new TextView(this);
        receiptTitle.setText("Receipt");
        receiptTitle.setTextSize(16);
        receiptTitle.setTextColor(COLOR_TEXT);
        root.addView(receiptTitle, matchWrap());

        receiptView = new TextView(this);
        receiptView.setText("No receipt yet.");
        receiptView.setTextSize(12);
        receiptView.setTextColor(COLOR_SECONDARY);
        receiptView.setTextIsSelectable(true);
        receiptView.setPadding(dp(12), dp(12), dp(12), dp(12));
        receiptView.setBackgroundColor(COLOR_SURFACE);
        receiptView.setContentDescription("Pocket TTS machine receipt");
        root.addView(receiptView, matchWrap());

        setContentView(scroll);
    }

    private void runDoctor() {
        setBusy(true, "Checking Pocket TTS…");
        executor.execute(() -> {
            try {
                HttpResult result = request("GET", SERVICE_BASE + "/health", null, 12000);
                JSONObject body = result.json;
                main.post(() -> renderResult("Doctor", result.code, body));
            } catch (Exception error) {
                main.post(() -> renderLocalFailure("F040_LOCAL_SERVICE_DOWN", error));
            }
        });
    }

    private void runSpeak() {
        String text = textInput == null ? "" : textInput.getText().toString().trim();
        if (TextUtils.isEmpty(text)) {
            stateView.setText("F041_BAD_REQUEST — enter text first.");
            stateView.setTextColor(COLOR_BAD);
            return;
        }
        setBusy(true, "Speaking and waiting for playback completion…");
        executor.execute(() -> {
            try {
                JSONObject payload = new JSONObject().put("text", text);
                HttpResult result = request("POST", SERVICE_BASE + "/speak", payload.toString(), 390000);
                main.post(() -> renderResult("Speak", result.code, result.json));
            } catch (Exception error) {
                main.post(() -> renderLocalFailure("F052_SPEECH_TIMEOUT", error));
            }
        });
    }

    private void renderResult(String action, int httpCode, JSONObject body) {
        boolean ok = body != null && body.optBoolean("ok", false);
        boolean playback = body != null && body.optBoolean("playbackVerified", false);
        String faultCode = body == null ? "F050_DOCTOR_FAILED" : body.optString("faultCode", ok ? "OK" : "F050_DOCTOR_FAILED");
        String detail = body == null ? "No JSON response" : body.optString("detail", "");
        if ("Speak".equals(action) && ok && !playback) {
            ok = false;
            faultCode = "F060_PLAYBACK_UNVERIFIED";
            detail = "Speech returned success without playbackVerified=true";
        }
        stateView.setText(action + ": " + faultCode + (detail.isEmpty() ? "" : " — " + detail));
        stateView.setTextColor(ok ? COLOR_GOOD : COLOR_BAD);
        try {
            receiptView.setText(body == null ? "{}" : body.toString(2));
        } catch (Exception ignored) {
            receiptView.setText(body == null ? "{}" : body.toString());
        }
        setBusy(false, null);
    }

    private void renderLocalFailure(String faultCode, Exception error) {
        stateView.setText(faultCode + " — " + shortMessage(error == null ? "unknown error" : error.getMessage()));
        stateView.setTextColor(COLOR_BAD);
        receiptView.setText("{\"ok\":false,\"faultCode\":\"" + faultCode + "\"}");
        setBusy(false, null);
    }

    private void setBusy(boolean busy, String message) {
        if (doctorButton != null) doctorButton.setEnabled(!busy);
        if (speakButton != null) speakButton.setEnabled(!busy);
        if (busy && stateView != null && message != null) {
            stateView.setText(message);
            stateView.setTextColor(COLOR_SECONDARY);
        }
    }

    private HttpResult request(String method, String endpoint, String jsonBody, int timeoutMs) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) new URL(endpoint).openConnection();
        connection.setRequestMethod(method);
        connection.setConnectTimeout(Math.min(timeoutMs, 5000));
        connection.setReadTimeout(timeoutMs);
        connection.setRequestProperty("Accept", "application/json");
        connection.setUseCaches(false);
        if (jsonBody != null) {
            byte[] bytes = jsonBody.getBytes(StandardCharsets.UTF_8);
            connection.setDoOutput(true);
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            connection.setFixedLengthStreamingMode(bytes.length);
            try (OutputStream output = connection.getOutputStream()) {
                output.write(bytes);
            }
        }
        int code = connection.getResponseCode();
        InputStream input = code >= 400 ? connection.getErrorStream() : connection.getInputStream();
        String raw = input == null ? "{}" : new String(readAll(input), StandardCharsets.UTF_8);
        connection.disconnect();
        return new HttpResult(code, new JSONObject(raw.isEmpty() ? "{}" : raw));
    }

    private byte[] readAll(InputStream input) throws Exception {
        try (InputStream source = input; ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192];
            int read;
            while ((read = source.read(buffer)) != -1) output.write(buffer, 0, read);
            return output.toByteArray();
        }
    }

    private String shortMessage(String value) {
        String clean = value == null ? "" : value.replaceAll("\\s+", " ").trim();
        return clean.length() > 240 ? clean.substring(0, 240) + "…" : clean;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
    }

    private LinearLayout.LayoutParams matchHeight(int height) {
        return new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                height);
    }

    @Override
    protected void onDestroy() {
        executor.shutdownNow();
        super.onDestroy();
    }

    private static final class HttpResult {
        final int code;
        final JSONObject json;
        HttpResult(int code, JSONObject json) {
            this.code = code;
            this.json = json;
        }
    }
}
