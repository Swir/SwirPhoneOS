package org.swir.phoneos.swirroot;

import android.app.Service;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Binder;
import android.os.Build;
import android.os.IBinder;
import java.util.ArrayList;
import java.util.List;

/**
 * Non-exported owner-facing status/diagnostics service.
 *
 * Mutation execution intentionally does not exist in this source stage. The constants stay
 * fail-closed until an exact physically verified device/build backend and rollback path exist.
 * The app-private journal records only owner review/diagnostic events; it is not the future
 * mutation transaction journal and therefore does not satisfy RootPolicy.journalAvailable.
 */
public final class SwirRootService extends Service {
    private static final boolean WRITE_BACKEND_ENABLED = false;
    private static final boolean SUPPORTED_BUILD = false;
    private static final int MAX_AUDIT_EVENTS = 32;
    private static final String PREFS = "swirroot_diagnostics";
    private static final String AUDIT = "audit";

    private final LocalBinder binder = new LocalBinder();

    public final class LocalBinder extends Binder {
        public SwirRootService service() {
            return SwirRootService.this;
        }
    }

    @Override
    public IBinder onBind(Intent intent) {
        return binder;
    }

    public RootPolicy.State currentState() {
        return RootPolicy.State.UNAVAILABLE;
    }

    public String currentBuildFingerprint() {
        return Build.FINGERPRINT;
    }

    public RootPolicy.Decision reviewEnable(boolean ownerConfirmed) {
        RootPolicy.Decision decision = RootPolicy.evaluateEnable(
                liveGates(ownerConfirmed), WRITE_BACKEND_ENABLED, SUPPORTED_BUILD);
        appendAudit("enable:" + decision.reasonCode);
        return decision;
    }

    public RootPolicy.Decision reviewUnroot(boolean ownerConfirmed) {
        RootPolicy.Decision decision = RootPolicy.evaluateUnroot(
                liveGates(ownerConfirmed), WRITE_BACKEND_ENABLED, SUPPORTED_BUILD);
        appendAudit("unroot:" + decision.reasonCode);
        return decision;
    }

    public List<String> auditSnapshot() {
        String serialized = preferences().getString(AUDIT, "");
        ArrayList<String> result = new ArrayList<>();
        if (serialized == null || serialized.isEmpty()) return result;
        for (String item : serialized.split("\n")) {
            if (!item.isEmpty()) result.add(item);
        }
        return result;
    }

    public boolean mutationBackendAvailable() {
        return WRITE_BACKEND_ENABLED && SUPPORTED_BUILD;
    }

    private RootPolicy.Gates liveGates(boolean ownerConfirmed) {
        // No physical-device verification/rollback transaction journal is claimed in source-only stage.
        return new RootPolicy.Gates(
                false,
                false,
                ownerConfirmed,
                false,
                false,
                false,
                false);
    }

    private SharedPreferences preferences() {
        return getSharedPreferences(PREFS, MODE_PRIVATE);
    }

    private void appendAudit(String event) {
        List<String> events = auditSnapshot();
        while (events.size() >= MAX_AUDIT_EVENTS) events.remove(0);
        events.add(event);
        StringBuilder serialized = new StringBuilder();
        for (String item : events) {
            if (serialized.length() > 0) serialized.append('\n');
            serialized.append(item);
        }
        preferences().edit().putString(AUDIT, serialized.toString()).apply();
    }
}
