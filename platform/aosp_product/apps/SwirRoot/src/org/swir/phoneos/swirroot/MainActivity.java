package org.swir.phoneos.swirroot;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.graphics.Color;
import android.os.Bundle;
import android.os.IBinder;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.util.List;

/** Premium owner-facing SwirRoot control surface with fail-closed review-only transitions. */
public final class MainActivity extends Activity {
    private SwirRootService service;
    private boolean bound;
    private TextView stateValue;
    private TextView buildValue;
    private TextView lastResult;
    private TextView auditValue;

    private final ServiceConnection connection = new ServiceConnection() {
        @Override
        public void onServiceConnected(ComponentName name, IBinder binder) {
            service = ((SwirRootService.LocalBinder) binder).service();
            render();
        }

        @Override
        public void onServiceDisconnected(ComponentName name) {
            service = null;
            render();
        }
    };

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(Color.rgb(3, 9, 20));
        getWindow().setNavigationBarColor(Color.rgb(3, 9, 20));
        setContentView(buildUi());
    }

    @Override
    protected void onStart() {
        super.onStart();
        bound = bindService(new Intent(this, SwirRootService.class), connection, Context.BIND_AUTO_CREATE);
    }

    @Override
    protected void onStop() {
        if (bound) {
            unbindService(connection);
            bound = false;
        }
        service = null;
        super.onStop();
    }

    private View buildUi() {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(20), dp(22), dp(20), dp(26));
        root.setBackgroundColor(Color.rgb(6, 16, 31));
        root.setLayoutDirection(View.LAYOUT_DIRECTION_LOCALE);
        scroll.addView(root, new ScrollView.LayoutParams(ScrollView.LayoutParams.MATCH_PARENT, ScrollView.LayoutParams.WRAP_CONTENT));

        root.addView(text(getString(R.string.app_name), 30, Color.rgb(93, 220, 255)), matchWrap());
        TextView subtitle = text(getString(R.string.subtitle), 14, Color.rgb(177, 199, 222));
        subtitle.setPadding(0, dp(3), 0, dp(16));
        root.addView(subtitle, matchWrap());

        LinearLayout stateCard = card();
        stateCard.addView(label(getString(R.string.state_title)));
        stateValue = text(getString(R.string.state_unavailable), 24, Color.WHITE);
        stateValue.setPadding(0, dp(4), 0, dp(8));
        stateCard.addView(stateValue, matchWrap());
        stateCard.addView(label(getString(R.string.build_title)));
        buildValue = text(getString(R.string.unknown_value), 12, Color.rgb(177, 199, 222));
        buildValue.setTextIsSelectable(true);
        stateCard.addView(buildValue, matchWrap());
        root.addView(stateCard, cardParams());

        LinearLayout safetyCard = card();
        safetyCard.addView(label(getString(R.string.safety_title)));
        safetyCard.addView(text(getString(R.string.safety_body), 14, Color.WHITE), matchWrap());
        root.addView(safetyCard, cardParams());

        LinearLayout workflowCard = card();
        workflowCard.addView(label(getString(R.string.workflow_title)));
        workflowCard.addView(text(getString(R.string.workflow_body), 14, Color.WHITE), matchWrap());
        workflowCard.addView(actionButton(R.string.enable_review, v -> confirmEnable()), matchWrap());
        workflowCard.addView(actionButton(R.string.unroot_review, v -> confirmUnroot()), matchWrap());
        workflowCard.addView(actionButton(R.string.diagnostics, v -> refreshDiagnostics()), matchWrap());
        root.addView(workflowCard, cardParams());

        LinearLayout resultCard = card();
        resultCard.addView(label(getString(R.string.last_result)));
        lastResult = text(getString(R.string.decision_denied_unsupported), 14, Color.WHITE);
        resultCard.addView(lastResult, matchWrap());
        resultCard.addView(label(getString(R.string.audit_title)));
        auditValue = text(getString(R.string.audit_empty), 13, Color.rgb(177, 199, 222));
        auditValue.setPadding(0, dp(4), 0, 0);
        resultCard.addView(auditValue, matchWrap());
        root.addView(resultCard, cardParams());
        return scroll;
    }

    private void confirmEnable() {
        new AlertDialog.Builder(this)
                .setTitle(R.string.confirm_enable_title)
                .setMessage(R.string.confirm_enable_body)
                .setNegativeButton(R.string.cancel, null)
                .setPositiveButton(R.string.continue_label, (dialog, which) -> {
                    if (service != null) showDecision(service.reviewEnable(true));
                })
                .show();
    }

    private void confirmUnroot() {
        new AlertDialog.Builder(this)
                .setTitle(R.string.confirm_unroot_title)
                .setMessage(R.string.confirm_unroot_body)
                .setNegativeButton(R.string.cancel, null)
                .setPositiveButton(R.string.continue_label, (dialog, which) -> {
                    if (service != null) showDecision(service.reviewUnroot(true));
                })
                .show();
    }

    private void refreshDiagnostics() {
        if (lastResult != null) lastResult.setText(R.string.diagnostics_refreshed);
        render();
    }

    private void showDecision(RootPolicy.Decision decision) {
        lastResult.setText(reasonText(decision.reasonCode));
        renderAudit();
    }

    private void render() {
        if (stateValue == null) return;
        if (service == null) {
            stateValue.setText(R.string.state_unavailable);
            buildValue.setText(R.string.unknown_value);
            auditValue.setText(R.string.audit_empty);
            return;
        }
        stateValue.setText(stateText(service.currentState()));
        buildValue.setText(service.currentBuildFingerprint());
        renderAudit();
    }

    private void renderAudit() {
        if (service == null) return;
        List<String> events = service.auditSnapshot();
        if (events.isEmpty()) {
            auditValue.setText(R.string.audit_empty);
            return;
        }
        StringBuilder out = new StringBuilder();
        for (String event : events) {
            if (out.length() > 0) out.append('\n');
            out.append(auditText(event));
        }
        auditValue.setText(out.toString());
    }

    private String auditText(String event) {
        if (event.startsWith("enable:")) return getString(R.string.audit_attempt_enable) + getString(R.string.audit_separator) + reasonText(event.substring(7));
        if (event.startsWith("unroot:")) return getString(R.string.audit_attempt_unroot) + getString(R.string.audit_separator) + reasonText(event.substring(7));
        return getString(R.string.audit_refresh);
    }

    private String reasonText(String reason) {
        if ("unsupported_build".equals(reason)) return getString(R.string.decision_denied_unsupported);
        if ("exact_build_match".equals(reason)) return getString(R.string.decision_denied_build);
        if ("verified_device_profile".equals(reason)) return getString(R.string.decision_denied_profile);
        if ("owner_confirmation".equals(reason)) return getString(R.string.decision_denied_owner);
        if ("rollback_material_verified".equals(reason)) return getString(R.string.decision_denied_rollback);
        if ("journal_available".equals(reason)) return getString(R.string.decision_denied_journal);
        if ("update_state_safe".equals(reason)) return getString(R.string.decision_denied_update);
        if ("expected_nonroot_state_known".equals(reason)) return getString(R.string.decision_denied_expected_state);
        if ("ready_enable".equals(reason)) return getString(R.string.decision_ready_enable);
        if ("ready_unroot".equals(reason)) return getString(R.string.decision_ready_unroot);
        return getString(R.string.diagnostics_refreshed);
    }

    private int stateText(RootPolicy.State state) {
        if (state == RootPolicy.State.ROOT_OFF) return R.string.state_off;
        if (state == RootPolicy.State.ROOT_ON) return R.string.state_on;
        if (state == RootPolicy.State.TRANSITION) return R.string.state_transition;
        return R.string.state_unavailable;
    }

    private LinearLayout card() {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(16), dp(15), dp(16), dp(15));
        card.setBackgroundColor(Color.rgb(11, 32, 53));
        return card;
    }

    private TextView label(String value) {
        TextView label = text(value, 12, Color.rgb(93, 220, 255));
        label.setPadding(0, dp(2), 0, dp(4));
        return label;
    }

    private Button actionButton(int textRes, View.OnClickListener listener) {
        Button button = new Button(this);
        button.setAllCaps(false);
        button.setText(textRes);
        button.setTextColor(Color.WHITE);
        button.setBackgroundColor(Color.rgb(17, 55, 83));
        button.setOnClickListener(listener);
        LinearLayout.LayoutParams params = matchWrap();
        params.setMargins(0, dp(7), 0, 0);
        button.setLayoutParams(params);
        return button;
    }

    private TextView text(String value, int sp, int color) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(sp);
        view.setTextColor(color);
        return view;
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
    }

    private LinearLayout.LayoutParams cardParams() {
        LinearLayout.LayoutParams params = matchWrap();
        params.setMargins(0, 0, 0, dp(12));
        return params;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
