package com.dclar.homecenter;

import android.app.Notification;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.os.Parcelable;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;

import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.FirebaseUser;
import com.google.firebase.firestore.FieldValue;
import com.google.firebase.firestore.FirebaseFirestore;
import com.google.firebase.firestore.SetOptions;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

public final class SmsCalendarNotificationListener extends NotificationListenerService {
    private static final String GOOGLE_MESSAGES_PACKAGE = "com.google.android.apps.messaging";
    private static final String PREFS = "home_center";
    private static final String KEY_BUCKET_CODE = "bucket_code";

    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        if (sbn == null || !GOOGLE_MESSAGES_PACKAGE.equals(sbn.getPackageName())) return;
        Notification notification = sbn.getNotification();
        if (notification == null || (notification.flags & Notification.FLAG_GROUP_SUMMARY) != 0) return;

        NotificationMessage message = latestMessage(notification);
        SmsReminderClassifier.Result classification = SmsReminderClassifier.classify(message.sender, message.body);
        if (!classification.candidate) {
            LocalLog.info("smsCalendar.skip",
                    "package=google_messages reason=" + classification.reason + " bodyPersisted=false");
            return;
        }
        persistCandidate(sbn, message, classification);
    }

    private void persistCandidate(StatusBarNotification sbn, NotificationMessage message,
                                  SmsReminderClassifier.Result classification) {
        FirebaseUser user = FirebaseAuth.getInstance().getCurrentUser();
        if (user == null) {
            LocalLog.info("smsCalendar.drop", "reason=not_signed_in bodyPersisted=false");
            return;
        }
        SharedPreferences prefs = getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        String bucketId = normalizeBucketId(prefs.getString(KEY_BUCKET_CODE, ""));
        if (bucketId.isEmpty()) {
            LocalLog.info("smsCalendar.drop", "reason=missing_household bodyPersisted=false");
            return;
        }
        long receivedAtMs = Math.max(1L, sbn.getPostTime());
        String sourceHash = sha256(sbn.getPackageName() + "\n" + message.sender + "\n"
                + message.senderAddress + "\n"
                + message.body + "\n" + receivedAtMs);
        String id = "sms_" + sourceHash.substring(0, 40);

        Map<String, Object> source = new HashMap<>();
        source.put("type", "android_notification");
        source.put("packageName", sbn.getPackageName());
        source.put("notificationKeyHash", sha256(sbn.getKey()));

        Map<String, Object> classificationMap = new HashMap<>();
        classificationMap.put("candidate", true);
        classificationMap.put("confidence", classification.confidence);
        classificationMap.put("matchReasons", classification.matchReasons);
        classificationMap.put("normalizedAliases", classification.normalizedAliases);
        classificationMap.put("classifierVersion", "2026-07-25.v1");

        Map<String, Object> record = new HashMap<>();
        record.put("sender", message.sender);
        record.put("senderAddress", message.senderAddress);
        record.put("body", message.body);
        record.put("receivedAtMs", receivedAtMs);
        record.put("sourceHash", sourceHash);
        record.put("source", source);
        record.put("classification", classificationMap);
        record.put("status", "pending");
        record.put("privacyScope", "appointment_reminder_candidate");
        record.put("createdByUid", user.getUid());
        record.put("createdByEmail", user.getEmail() == null ? "" : user.getEmail().toLowerCase(Locale.US));
        record.put("createdAtMs", System.currentTimeMillis());
        record.put("createdAt", FieldValue.serverTimestamp());
        record.put("updatedAtMs", System.currentTimeMillis());

        FirebaseFirestore.getInstance()
                .collection("households").document(bucketId)
                .collection("smsCalendarIntake").document(id)
                .set(record, SetOptions.merge())
                .addOnSuccessListener(ignored ->
                        LocalLog.info("smsCalendar.capture", "messageId=" + id + " bodyPersisted=true"))
                .addOnFailureListener(error ->
                        LocalLog.error("smsCalendar.capture", "messageId=" + id + " bodyPersisted=false", error));
    }

    private NotificationMessage latestMessage(Notification notification) {
        Bundle extras = notification.extras == null ? new Bundle() : notification.extras;
        String fallbackSender = charSequence(extras.getCharSequence(Notification.EXTRA_TITLE));
        String fallbackBody = charSequence(extras.getCharSequence(Notification.EXTRA_TEXT));
        Parcelable[] bundles = extras.getParcelableArray(Notification.EXTRA_MESSAGES);
        if (bundles == null || bundles.length == 0) return new NotificationMessage(fallbackSender, "", fallbackBody);
        java.util.List<Notification.MessagingStyle.Message> messages =
                Notification.MessagingStyle.Message.getMessagesFromBundleArray(bundles);
        if (messages == null || messages.isEmpty()) return new NotificationMessage(fallbackSender, "", fallbackBody);
        Notification.MessagingStyle.Message latest = messages.get(messages.size() - 1);
        String sender = latest.getSenderPerson() == null ? fallbackSender : charSequence(latest.getSenderPerson().getName());
        String senderAddress = latest.getSenderPerson() == null ? "" : safeSenderAddress(latest.getSenderPerson().getUri());
        String body = charSequence(latest.getText());
        return new NotificationMessage(sender.isEmpty() ? fallbackSender : sender, senderAddress,
                body.isEmpty() ? fallbackBody : body);
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

    private static String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] bytes = digest.digest((value == null ? "" : value).getBytes(StandardCharsets.UTF_8));
            StringBuilder out = new StringBuilder();
            for (byte item : bytes) out.append(String.format(Locale.US, "%02x", item));
            return out.toString();
        } catch (Exception error) {
            return Integer.toHexString((value == null ? "" : value).hashCode())
                    + "0000000000000000000000000000000000000000000000000000000000000000";
        }
    }

    private static final class NotificationMessage {
        final String sender;
        final String senderAddress;
        final String body;

        NotificationMessage(String sender, String senderAddress, String body) {
            this.sender = sender == null ? "" : sender.trim();
            this.senderAddress = senderAddress == null ? "" : senderAddress.trim();
            this.body = body == null ? "" : body.trim();
        }
    }
}
