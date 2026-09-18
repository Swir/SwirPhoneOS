package org.swir.phoneos.phone;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.telecom.Call;
import android.view.Gravity;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

public final class InCallActivity extends Activity {
    private final Handler handler = new Handler(Looper.getMainLooper());
    private TextView numberView;
    private TextView stateView;
    private Button answerButton;
    private Button rejectButton;
    private Button endButton;

    private final Runnable refresher = new Runnable() {
        @Override public void run() {
            refreshCallState();
            handler.postDelayed(this, 500L);
        }
    };

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        setTitle(R.string.app_name);
        setContentView(buildUi());
        refreshCallState();
    }

    @Override protected void onResume() {
        super.onResume();
        handler.removeCallbacks(refresher);
        handler.post(refresher);
    }

    @Override protected void onPause() {
        handler.removeCallbacks(refresher);
        super.onPause();
    }

    private LinearLayout buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.CENTER_HORIZONTAL);
        int padding = dim(R.dimen.swir_space_lg);
        root.setPadding(padding, padding, padding, padding);
        root.setBackgroundColor(getColor(R.color.swir_background));

        TextView eyebrow = text(getString(R.string.incall_eyebrow), 13, getColor(R.color.swir_accent_cyan));
        root.addView(eyebrow, matchWrap());
        TextView title = text(getString(R.string.incall_title), 30, getColor(R.color.swir_text_primary));
        root.addView(title, matchWrap());

        numberView = text("", 24, getColor(R.color.swir_text_primary));
        numberView.setGravity(Gravity.CENTER_HORIZONTAL);
        LinearLayout.LayoutParams numberParams = matchWrap();
        numberParams.topMargin = dim(R.dimen.swir_space_lg);
        root.addView(numberView, numberParams);

        stateView = text("", 16, getColor(R.color.swir_text_secondary));
        stateView.setGravity(Gravity.CENTER_HORIZONTAL);
        root.addView(stateView, matchWrap());

        LinearLayout primary = new LinearLayout(this);
        primary.setOrientation(LinearLayout.HORIZONTAL);
        primary.setGravity(Gravity.CENTER);
        answerButton = actionButton(R.string.answer_call);
        answerButton.setOnClickListener(v -> { SwirInCallService.answerActiveCall(); refreshCallState(); });
        primary.addView(answerButton, weighted());
        rejectButton = actionButton(R.string.reject_call);
        rejectButton.setOnClickListener(v -> { SwirInCallService.rejectActiveCall(); refreshCallState(); });
        primary.addView(rejectButton, weighted());
        LinearLayout.LayoutParams primaryParams = matchWrap();
        primaryParams.topMargin = dim(R.dimen.swir_space_lg);
        root.addView(primary, primaryParams);

        endButton = actionButton(R.string.end_call);
        endButton.setOnClickListener(v -> { SwirInCallService.disconnectActiveCall(); refreshCallState(); });
        LinearLayout.LayoutParams endParams = matchWrap();
        endParams.topMargin = dim(R.dimen.swir_space_sm);
        root.addView(endButton, endParams);
        return root;
    }

    private void refreshCallState() {
        int state = SwirInCallService.currentState();
        String number = SwirInCallService.currentNumber();
        if (number.isEmpty()) number = getString(R.string.unknown_number);
        numberView.setText(getString(R.string.incall_number_format, number));
        stateView.setText(getString(R.string.incall_state_format, getString(stateLabel(state))));
        boolean ringing = state == Call.STATE_RINGING;
        boolean connected = state == Call.STATE_ACTIVE || state == Call.STATE_HOLDING || state == Call.STATE_DIALING || state == Call.STATE_CONNECTING;
        answerButton.setEnabled(ringing);
        rejectButton.setEnabled(ringing);
        endButton.setEnabled(connected);
    }

    private int stateLabel(int state) {
        switch (state) {
            case Call.STATE_NEW: return R.string.call_state_new;
            case Call.STATE_CONNECTING: return R.string.call_state_connecting;
            case Call.STATE_DIALING: return R.string.call_state_dialing;
            case Call.STATE_RINGING: return R.string.call_state_ringing;
            case Call.STATE_ACTIVE: return R.string.call_state_active;
            case Call.STATE_HOLDING: return R.string.call_state_holding;
            case Call.STATE_DISCONNECTED: return R.string.call_state_disconnected;
            case Call.STATE_DISCONNECTING: return R.string.call_state_disconnecting;
            case Call.STATE_SELECT_PHONE_ACCOUNT: return R.string.call_state_select_account;
            default: return R.string.call_state_unknown;
        }
    }

    private TextView text(String value, int sp, int color) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(sp);
        view.setTextColor(color);
        int vertical = dim(R.dimen.swir_space_xs);
        view.setPadding(0, vertical, 0, vertical);
        return view;
    }

    private Button actionButton(int textRes) {
        Button button = new Button(this);
        button.setText(textRes);
        button.setMinHeight(dim(R.dimen.swir_touch_min));
        return button;
    }

    private LinearLayout.LayoutParams matchWrap() { return new LinearLayout.LayoutParams(-1, -2); }
    private LinearLayout.LayoutParams weighted() { return new LinearLayout.LayoutParams(0, -2, 1f); }
    private int dim(int id) { return getResources().getDimensionPixelSize(id); }
}
