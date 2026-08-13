package com.dclar.homecenter;

import android.app.Notification;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.Build;
import android.os.Bundle;
import android.os.Parcelable;
import android.provider.Settings;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;

import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.FirebaseUser;
import com.google.firebase.firestore.DocumentReference;
import com.google.firebase.firestore.DocumentSnapshot;
import com.google.firebase.firestore.FieldValue;
import com.google.firebase.firestore.FirebaseFirestore;
import com.google.firebase.firestore.SetOptions;

import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.TimeZone;

public final class SmsCalendarNotificationListener extends NotificationListenerService {
    private static final String GOOGLE_MESSAGES_PACKAGE = "com.google.android.apps.messaging";
    private static final String SOURCE_TRANSPORT = "android_google_messages_notification";
    private static final String PREFS = "home_center";
    private static final String KEY_BUCKET_CODE = "bucket_code";
    private static final String KEY_TEXT_MINING_AUTHORIZED = "text_mining_authorized";

    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        if (sbn == null || !GOOGLE_MESSAGES_PACKAGE.equals(sbn.getPackageName())) return;
        Notification notification = sbn.getNotification();
        if (notification == null || (notification.flags & Notification.FLAG_GROUP_SUMMARY) != 0) return;

        NotificationMessage message = latestMessage(notification);
        if (message.body.isEmpty()) {
            LocalLog.info("smsCalendar.skip", "package=google_messages reason=empty bodyPersisted=false");
            return;
        }
        preserveThenClassify(sbn, message);
    }

    private void preserveThenClassify(StatusBarNotification sbn, NotificationMessage message) {
        SharedPreferences prefs = getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        if (!prefs.getBoolean(KEY_TEXT_MINING_AUTHORIZED, false)) {
            LocalLog.info("smsCalendar.drop", "reason=text_mining_not_authorized bodyPersisted=false");
            return;
        }
        FirebaseUser user = FirebaseAuth.getInstance().getCurrentUser();
        if (user == null) {
            LocalLog.info("smsCalendar.drop", "reason=not_signed_in bodyPersisted=false");
            return;
        }
        String bucketId = normalizeBucketId(prefs.getString(KEY_BUCKET_CODE, ""));
        if (bucketId.isEmpty()) {
            LocalLog.info("smsCalendar.drop", "reason=missing_household bodyPersisted=false");
            return;
        }

        long receivedAtMs = Math.max(1L, message.timestampMs > 0 ? message.timestampMs : sbn.getPostTime());
        String notificationKeyHash = SmsCalendarIngestionContract.sha256(sbn.getKey());
        String rawSourceReference = "notification:" + notificationKeyHash;
        String sourceMessageId = SmsCalendarIngestionContract.stableMessageId(
                SOURCE_TRANSPORT, notificationKeyHash, receivedAtMs);
        String recipientDeviceId = deviceIdentityHash();
        String sourceHash = SmsCalendarIngestionContract.immutableHash(sourceMessageId, message.sender,
                message.senderAddress, recipientDeviceId, message.body, receivedAtMs, SOURCE_TRANSPORT,
                rawSourceReference);
        String ingestionIdempotencyKey = SmsCalendarIngestionContract.ingestionIdempotencyKey(
                sourceMessageId, sourceHash);

        Map<String, Object> source = new HashMap<>();
        source.put("type", "android_notification");
        source.put("transport", SOURCE_TRANSPORT);
        source.put("packageName", sbn.getPackageName());
        source.put("rawSourceReference", rawSourceReference);
        source.put("rawSourceHash", SmsCalendarIngestionContract.sha256(
                sbn.getPackageName() + "\n" + notificationKeyHash + "\n" + receivedAtMs + "\n" + message.body));

        Map<String, Object> record = new HashMap<>();
        record.put("schemaVersion", "home-center.sms-calendar-intake.v2");
        record.put("messageId", sourceMessageId);
        record.put("sender", message.sender);
        record.put("senderAddress", SmsCalendarIngestionContract.normalizePhone(message.senderAddress));
        record.put("recipientDeviceId", recipientDeviceId);
        record.put("body", message.body);
        record.put("receivedAtMs", receivedAtMs);
        record.put("sourceTransport", SOURCE_TRANSPORT);
        record.put("sourceHash", sourceHash);
        record.put("immutableHash", sourceHash);
        record.put("ingestionIdempotencyKey", ingestionIdempotencyKey);
        record.put("source", source);
        record.put("status", "received");
        record.put("privacyScope", "sms_calendar_private");
        record.put("createdByUid", user.getUid());
        record.put("createdByEmail", user.getEmail() == null ? "" : user.getEmail().toLowerCase(Locale.US));
        record.put("preservedAtMs", System.currentTimeMillis());
        record.put("createdAtMs", System.currentTimeMillis());
        record.put("createdAt", FieldValue.serverTimestamp());
        record.put("updatedAtMs", System.currentTimeMillis());

        FirebaseFirestore db = FirebaseFirestore.getInstance();
        DocumentReference ref = db.collection("households").document(bucketId)
                .collection("smsCalendarIntake").document(sourceMessageId);
        db.runTransaction(transaction -> {
            DocumentSnapshot existing = transaction.get(ref);
            if (existing.exists()) {
                SmsCalendarIngestionContract.ReplayDecision decision =
                        SmsCalendarIngestionContract.replayDecision(existing.getString("immutableHash"), sourceHash);
                if (decision == SmsCalendarIngestionContract.ReplayDecision.CONFLICT) {
                    throw new IllegalStateException("SMS_INTAKE_IDEMPOTENCY_CONFLICT");
                }
                String existingStatus = existing.getString("status");
                boolean retryClassification = "received".equals(existingStatus) || "failed".equals(existingStatus);
                return retryClassification ? "attached_retry_classification" : "attached";
            }
            transaction.set(ref, record);
            return "created";
        }).addOnSuccessListener(action -> {
            LocalLog.info("smsCalendar.preserve", "messageId=" + sourceMessageId + " action=" + action
                    + " bodyPersisted=true");
            if (!"attached".equals(action)) {
                classifyPreservedRecord(ref, sourceMessageId, sourceHash, message, receivedAtMs);
            }
        }).addOnFailureListener(error -> {
            String reason = error != null && String.valueOf(error.getMessage()).contains("SMS_INTAKE_IDEMPOTENCY_CONFLICT")
                    ? "idempotency_conflict" : "firestore_error";
            LocalLog.error("smsCalendar.preserve", "messageId=" + sourceMessageId + " reason=" + reason
                    + " bodyPersisted=false", error);
        });
    }

    private void classifyPreservedRecord(DocumentReference ref, String messageId, String sourceHash,
                                           NotificationMessage message, long receivedAtMs) {
        SmsReminderClassifier.Result result = SmsReminderClassifier.classify(message.sender, message.body,
                receivedAtMs, TimeZone.getDefault().getID(), SmsReminderClassifier.DEFAULT_DURATION_MINUTES);
        Map<String, Object> derived = new HashMap<>();
        derived.put("classification", result.classificationMap());
        derived.put("status", result.candidate ? "proposal_ready" : "classified");
        derived.put("classifiedAtMs", System.currentTimeMillis());
        derived.put("updatedAtMs", System.currentTimeMillis());
        if (result.candidate) derived.put("proposal", result.proposalMap(messageId, sourceHash));
        ref.set(derived, SetOptions.merge())
                .addOnSuccessListener(ignored -> LocalLog.info("smsCalendar.classify",
                        "messageId=" + messageId + " classification=" + result.classification
                                + " proposalReady=" + result.candidate))
                .addOnFailureListener(error -> LocalLog.error("smsCalendar.classify",
                        "messageId=" + messageId + " classificationPersisted=false", error));
    }

    private NotificationMessage latestMessage(Notification notification) {
        Bundle extras = notification.extras == null ? new Bundle() : notification.extras;
        String fallbackSender = charSequence(extras.getCharSequence(Notification.EXTRA_TITLE));
        String fallbackBody = charSequence(extras.getCharSequence(Notification.EXTRA_TEXT));
        Parcelable[] bundles = extras.getParcelableArray(Notification.EXTRA_MESSAGES);
        if (bundles == null || bundles.length == 0) {
            return new NotificationMessage(fallbackSender, "", fallbackBody, 0L);
        }
        java.util.List<Notification.MessagingStyle.Message> messages =
                Notification.MessagingStyle.Message.getMessagesFromBundleArray(bundles);
        if (messages == null || messages.isEmpty()) {
            return new NotificationMessage(fallbackSender, "", fallbackBody, 0L);
        }
        Notification.MessagingStyle.Message latest = messages.get(messages.size() - 1);
        String sender = fallbackSender;
        String senderAddress = "";
        if (Build.VERSION.SDK_INT >= 28 && latest.getSenderPerson() != null) {
            sender = charSequence(latest.getSenderPerson().getName());
            senderAddress = safeSenderAddress(latest.getSenderPerson().getUri());
        } else if (latest.getSender() != null) {
            sender = charSequence(latest.getSender());
        }
        String body = charSequence(latest.getText());
        return new NotificationMessage(sender.isEmpty() ? fallbackSender : sender, senderAddress,
                body.isEmpty() ? fallbackBody : body, latest.getTimestamp());
    }

    private String deviceIdentityHash() {
        String androidId = Settings.Secure.getString(getContentResolver(), Settings.Secure.ANDROID_ID);
        if (androidId == null || androidId.trim().isEmpty()) return "";
        return "device_" + SmsCalendarIngestionContract.sha256(androidId).substring(0, 24);
    }

    private static String normalizeBucketId(String value) {
        if (value == null) return "";
        return value.trim().toLowerCase(Locale.US).replaceAll("[^a-z0-9_-]", "-").replaceAll("-+", "-");
    }

    private static String charSequence(CharSequence value) {
        return value == null ? "" : value.toString().trim();
    }

    private static String safeSenderAddress(String value) {
        String clean = value == null ? "" : value.trim();
        if (clean.toLowerCase(Locale.US).startsWith("tel:")) return clean.substring(4);
        return "";
    }

    private static final class NotificationMessage {
        final String sender;
        final String senderAddress;
        final String body;
        final long timestampMs;

        NotificationMessage(String sender, String senderAddress, String body, long timestampMs) {
            this.sender = sender == null ? "" : sender.trim();
            this.senderAddress = senderAddress == null ? "" : senderAddress.trim();
            this.body = body == null ? "" : body.trim();
            this.timestampMs = timestampMs;
        }
    }
}
