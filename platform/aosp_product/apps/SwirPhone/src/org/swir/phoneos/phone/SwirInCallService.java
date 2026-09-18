package org.swir.phoneos.phone;

import android.content.Intent;
import android.net.Uri;
import android.telecom.Call;
import android.telecom.InCallService;
import android.telecom.TelecomManager;
import android.telecom.VideoProfile;

import java.util.List;

public final class SwirInCallService extends InCallService {
    private static final Object LOCK = new Object();
    private static Call activeCall;

    @Override public void onCallAdded(Call call) {
        super.onCallAdded(call);
        synchronized (LOCK) {
            activeCall = call;
        }
        showCallUi(call);
    }

    @Override public void onCallRemoved(Call call) {
        super.onCallRemoved(call);
        synchronized (LOCK) {
            if (activeCall == call) {
                List<Call> remaining = getCalls();
                activeCall = remaining.isEmpty() ? null : remaining.get(remaining.size() - 1);
            }
        }
    }

    @Override public void onDestroy() {
        synchronized (LOCK) {
            activeCall = null;
        }
        super.onDestroy();
    }

    public static boolean hasActiveCall() {
        return currentCall() != null;
    }

    public static int currentState() {
        Call call = currentCall();
        return call == null ? -1 : call.getState();
    }

    public static String currentNumber() {
        Call call = currentCall();
        if (call == null || call.getDetails() == null) return "";
        Call.Details details = call.getDetails();
        if (details.getHandlePresentation() != TelecomManager.PRESENTATION_ALLOWED) return "";
        Uri handle = details.getHandle();
        if (handle == null) return "";
        String value = handle.getSchemeSpecificPart();
        if (value == null) return "";
        value = value.trim();
        if (value.length() > DialerPolicy.MAX_DIAL_LENGTH) return "";
        for (int i = 0; i < value.length(); i++) {
            if (Character.isISOControl(value.charAt(i))) return "";
        }
        return value;
    }

    public static boolean answerActiveCall() {
        Call call = currentCall();
        if (call == null || call.getState() != Call.STATE_RINGING) return false;
        call.answer(VideoProfile.STATE_AUDIO_ONLY);
        return true;
    }

    public static boolean rejectActiveCall() {
        Call call = currentCall();
        if (call == null || call.getState() != Call.STATE_RINGING) return false;
        call.reject(false, null);
        return true;
    }

    public static boolean disconnectActiveCall() {
        Call call = currentCall();
        if (call == null || call.getState() == Call.STATE_DISCONNECTED) return false;
        call.disconnect();
        return true;
    }

    private static Call currentCall() {
        synchronized (LOCK) {
            return activeCall;
        }
    }

    private void showCallUi(Call call) {
        int state = call.getState();
        if (state != Call.STATE_RINGING && state != Call.STATE_DIALING && state != Call.STATE_CONNECTING) return;
        Intent intent = new Intent(this, InCallActivity.class);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        try {
            startActivity(intent);
        } catch (RuntimeException ignored) {
            // The default-dialer/runtime contract is verified only on a real built image.
        }
    }
}
