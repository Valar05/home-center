package com.homecenter.fortresscockpit;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.app.PendingIntent;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Typeface;
import android.os.Build;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.concurrent.atomic.AtomicInteger;

public final class MainActivity extends Activity implements CommandResultReceiver.Listener {
    private static final String TERMUX_PACKAGE = "com.termux";
    private static final String TERMUX_SERVICE = "com.termux.app.RunCommandService";
    private static final String ACTION_RUN = "com.termux.RUN_COMMAND";
    private static final String EXTRA_PATH = "com.termux.RUN_COMMAND_PATH";
    private static final String EXTRA_ARGS = "com.termux.RUN_COMMAND_ARGUMENTS";
    private static final String EXTRA_WORKDIR = "com.termux.RUN_COMMAND_WORKDIR";
    private static final String EXTRA_BACKGROUND = "com.termux.RUN_COMMAND_BACKGROUND";
    private static final String EXTRA_PENDING = "com.termux.RUN_COMMAND_PENDING_INTENT";
    private static final String TERMUX_HOME = "/data/data/com.termux/files/home";
    private static final String REPO = "/storage/emulated/0/Documents/GodotProjects/home-center";
    private static final String PYTHON = "/data/data/com.termux/files/usr/bin/python";
    private static final String COMPILER = REPO + "/tools/fortress_prompt.py";
    private static final String RUN_PERMISSION = "com.termux.permission.RUN_COMMAND";
    private static final int CATALOG_REQUEST = 41;
    private static final AtomicInteger NEXT_REQUEST = new AtomicInteger(1000);

    private LinearLayout controls;
    private TextView title;
    private TextView subtitle;
    private TextView output;
    private EditText prompt;

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        setContentView(buildUi());
        restoreLastOutput();
        ensurePermissionThenRefresh();
    }

    @Override protected void onResume() {
        super.onResume();
        CommandResultReceiver.setListener(this);
    }

    @Override protected void onPause() {
        CommandResultReceiver.setListener(null);
        super.onPause();
    }

    private View buildUi() {
        ScrollView scroll = new ScrollView(this);
        LinearLayout root = column();
        root.setPadding(dp(20), dp(20), dp(20), dp(48));
        scroll.addView(root);

        title = text("Fortress Cockpit", 28, true);
        subtitle = text("Loading deterministic controls…", 16, false);
        root.addView(title);
        root.addView(subtitle);

        LinearLayout toolbar = row();
        Button refresh = button("Refresh controls");
        refresh.setContentDescription("Reload Fortress controls from configuration");
        refresh.setOnClickListener(v -> refreshCatalog());
        Button terminal = button("Raw Termux");
        terminal.setContentDescription("Open the underlying Termux terminal escape hatch");
        terminal.setOnClickListener(v -> openTermux());
        toolbar.addView(refresh, weight());
        toolbar.addView(terminal, weight());
        root.addView(toolbar);

        TextView promptLabel = text("Prompt", 18, true);
        root.addView(promptLabel);
        prompt = new EditText(this);
        prompt.setTextSize(18);
        prompt.setMinHeight(dp(56));
        prompt.setSingleLine(true);
        prompt.setHint("fortress status");
        prompt.setContentDescription("Deterministic Fortress command prompt");
        prompt.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);
        root.addView(prompt);

        Button run = button("Run deterministic prompt");
        run.setMinHeight(dp(56));
        run.setOnClickListener(v -> runPrompt(prompt.getText().toString()));
        root.addView(run);

        controls = column();
        root.addView(controls);

        TextView outputLabel = text("Receipt", 18, true);
        root.addView(outputLabel);
        output = text("No command receipt yet.", 15, false);
        output.setTypeface(Typeface.MONOSPACE);
        output.setTextIsSelectable(true);
        output.setContentDescription("Latest command receipt");
        output.setPadding(dp(12), dp(12), dp(12), dp(12));
        root.addView(output);
        return scroll;
    }

    private void ensurePermissionThenRefresh() {
        if (Build.VERSION.SDK_INT >= 23 && checkSelfPermission(RUN_PERMISSION) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{RUN_PERMISSION}, 77);
        } else {
            refreshCatalog();
        }
    }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grants) {
        super.onRequestPermissionsResult(requestCode, permissions, grants);
        if (requestCode == 77 && grants.length > 0 && grants[0] == PackageManager.PERMISSION_GRANTED) refreshCatalog();
        else showReceipt("BLOCKED: grant ‘Run commands in Termux environment’ to Fortress Cockpit.");
    }

    private void refreshCatalog() {
        showReceipt("Loading controls from Fortress config…");
        runTermux(CATALOG_REQUEST, new String[]{COMPILER, "--catalog-json"});
    }

    private void runPrompt(String raw) {
        String value = raw == null ? "" : raw.trim();
        if (value.isEmpty()) {
            prompt.setError("Type a deterministic command");
            return;
        }
        rememberPrompt(value);
        runTermux(NEXT_REQUEST.getAndIncrement(), new String[]{COMPILER, value});
    }

    private void runTermux(int requestId, String[] args) {
        Intent resultIntent = new Intent(this, CommandResultReceiver.class).putExtra("request_id", requestId);
        int flags = PendingIntent.FLAG_ONE_SHOT | PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= 31) flags |= PendingIntent.FLAG_MUTABLE;
        PendingIntent callback = PendingIntent.getBroadcast(this, requestId, resultIntent, flags);

        Intent command = new Intent();
        command.setClassName(TERMUX_PACKAGE, TERMUX_SERVICE);
        command.setAction(ACTION_RUN);
        command.putExtra(EXTRA_PATH, PYTHON);
        command.putExtra(EXTRA_ARGS, args);
        command.putExtra(EXTRA_WORKDIR, REPO);
        command.putExtra(EXTRA_BACKGROUND, true);
        command.putExtra(EXTRA_PENDING, callback);
        try {
            startService(command);
        } catch (Exception e) {
            showReceipt("BLOCKED: Termux bridge unavailable. Ensure Termux is installed, Cockpit has RUN_COMMAND permission, and allow-external-apps=true.\n\n" + e);
        }
    }

    @Override public void onCommandResult(int requestId, String stdout, String stderr, int exitCode, String error) {
        runOnUiThread(() -> {
            if (requestId == CATALOG_REQUEST) {
                if (exitCode == 0) renderCatalog(stdout);
                else showReceipt(formatReceipt(stdout, stderr, exitCode, error));
                return;
            }
            showReceipt(formatReceipt(stdout, stderr, exitCode, error));
        });
    }

    private void renderCatalog(String raw) {
        try {
            JSONObject catalog = new JSONObject(raw.trim());
            title.setText(catalog.optString("title", "Fortress Cockpit"));
            subtitle.setText(catalog.optString("subtitle", "Deterministic phone command center"));
            controls.removeAllViews();
            JSONArray items = catalog.getJSONArray("items");
            String group = null;
            for (int i = 0; i < items.length(); i++) {
                JSONObject item = items.getJSONObject(i);
                String nextGroup = item.optString("group", "Commands");
                if (!nextGroup.equals(group)) {
                    group = nextGroup;
                    TextView header = text(group, 20, true);
                    header.setPadding(0, dp(22), 0, dp(6));
                    controls.addView(header);
                }
                Button control = button(item.optString("label", item.optString("prompt", "Command")));
                String description = item.optString("description", "");
                control.setContentDescription(description.isEmpty() ? control.getText() : control.getText() + ". " + description);
                control.setMinHeight(dp(item.optBoolean("prominent", false) ? 64 : 54));
                String command = item.getString("prompt");
                boolean destructive = item.optBoolean("destructive", false);
                control.setOnClickListener(v -> {
                    prompt.setText(command);
                    if (destructive) confirmThenRun(command);
                    else runPrompt(command);
                });
                controls.addView(control);
                if (!description.isEmpty()) controls.addView(text(description, 14, false));
            }
            showReceipt("Controls loaded from Fortress config: " + items.length() + " actions.");
        } catch (Exception e) {
            showReceipt("BLOCKED: invalid Fortress catalog.\n" + e + "\n\nRaw:\n" + raw);
        }
    }

    private void confirmThenRun(String command) {
        new AlertDialog.Builder(this)
            .setTitle("Confirm command")
            .setMessage(command)
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Run", (d, w) -> runPrompt(command))
            .show();
    }

    private String formatReceipt(String stdout, String stderr, int exitCode, String error) {
        StringBuilder b = new StringBuilder("exit ").append(exitCode).append('\n');
        if (error != null && !error.isEmpty()) b.append("bridge: ").append(error).append('\n');
        if (stdout != null && !stdout.isEmpty()) b.append("\n").append(stdout.trim()).append('\n');
        if (stderr != null && !stderr.isEmpty()) b.append("\nstderr:\n").append(stderr.trim()).append('\n');
        return b.toString().trim();
    }

    private void showReceipt(String value) {
        output.setText(value);
        getSharedPreferences("cockpit", MODE_PRIVATE).edit().putString("last_output", value).apply();
    }

    private void restoreLastOutput() {
        String saved = getSharedPreferences("cockpit", MODE_PRIVATE).getString("last_output", "No command receipt yet.");
        output.setText(saved);
        String lastPrompt = getSharedPreferences("cockpit", MODE_PRIVATE).getString("last_prompt", "");
        prompt.setText(lastPrompt);
    }

    private void rememberPrompt(String value) {
        getSharedPreferences("cockpit", MODE_PRIVATE).edit().putString("last_prompt", value).apply();
    }

    private void openTermux() {
        Intent launch = getPackageManager().getLaunchIntentForPackage(TERMUX_PACKAGE);
        if (launch != null) startActivity(launch);
        else showReceipt("BLOCKED: Termux is not installed.");
    }

    private LinearLayout column() {
        LinearLayout v = new LinearLayout(this);
        v.setOrientation(LinearLayout.VERTICAL);
        return v;
    }

    private LinearLayout row() {
        LinearLayout h = new LinearLayout(this);
        h.setOrientation(LinearLayout.HORIZONTAL);
        h.setGravity(Gravity.CENTER_VERTICAL);
        return h;
    }

    private TextView text(String value, int sp, boolean bold) {
        TextView t = new TextView(this);
        t.setText(value);
        t.setTextSize(sp);
        if (bold) t.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        t.setPadding(0, dp(6), 0, dp(6));
        return t;
    }

    private Button button(String value) {
        Button b = new Button(this);
        b.setText(value);
        b.setAllCaps(false);
        b.setTextSize(16);
        b.setMinHeight(dp(52));
        return b;
    }

    private LinearLayout.LayoutParams weight() {
        return new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
    }

    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }
}
