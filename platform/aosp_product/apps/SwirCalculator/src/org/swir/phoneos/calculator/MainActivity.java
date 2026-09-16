package org.swir.phoneos.calculator;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.GridLayout;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.text.DecimalFormatSymbols;

/** First functional SwirPhoneOS application source: an offline calculator. */
public final class MainActivity extends Activity {
    private final CalculatorEngine engine = new CalculatorEngine();
    private TextView display;
    private char decimalSeparator;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        decimalSeparator = DecimalFormatSymbols.getInstance().getDecimalSeparator();
        getWindow().setStatusBarColor(Color.rgb(4, 11, 23));
        getWindow().setNavigationBarColor(Color.rgb(4, 11, 23));
        setContentView(buildUi());
        refreshDisplay();
    }

    private View buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(18), dp(18), dp(18));
        root.setBackgroundColor(Color.rgb(7, 18, 34));
        root.setLayoutDirection(View.LAYOUT_DIRECTION_LOCALE);

        TextView title = new TextView(this);
        title.setText(R.string.app_name);
        title.setTextColor(Color.rgb(120, 205, 255));
        title.setTextSize(20);
        root.addView(title, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        display = new TextView(this);
        display.setTextColor(Color.WHITE);
        display.setTextSize(46);
        display.setGravity(Gravity.END | Gravity.CENTER_VERTICAL);
        display.setMinHeight(dp(112));
        display.setContentDescription(getString(R.string.display_description));
        root.addView(display, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));

        GridLayout keypad = new GridLayout(this);
        keypad.setColumnCount(4);
        keypad.setRowCount(5);
        keypad.setUseDefaultMargins(false);
        keypad.setAlignmentMode(GridLayout.ALIGN_BOUNDS);
        keypad.setLayoutDirection(View.LAYOUT_DIRECTION_LOCALE);

        String[][] keys = {
                {"C", "±", "%", "÷"},
                {"7", "8", "9", "×"},
                {"4", "5", "6", "-"},
                {"1", "2", "3", "+"},
                {"⌫", "0", ".", "="}
        };
        for (String[] row : keys) {
            for (String key : row) {
                keypad.addView(makeButton(key), cellParams());
            }
        }
        root.addView(keypad, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));
        return root;
    }

    private Button makeButton(final String key) {
        Button button = new Button(this);
        button.setAllCaps(false);
        button.setText(".".equals(key) ? String.valueOf(decimalSeparator) : key);
        button.setTextSize(22);
        button.setTextColor(Color.WHITE);
        button.setBackgroundColor(isOperator(key) ? Color.rgb(18, 88, 145) : Color.rgb(17, 38, 62));
        button.setContentDescription(descriptionFor(key));
        button.setOnClickListener(view -> handleKey(key));
        return button;
    }

    private GridLayout.LayoutParams cellParams() {
        GridLayout.LayoutParams params = new GridLayout.LayoutParams();
        params.width = 0;
        params.height = dp(66);
        params.columnSpec = GridLayout.spec(GridLayout.UNDEFINED, 1f);
        params.setMargins(dp(4), dp(4), dp(4), dp(4));
        return params;
    }

    private void handleKey(String key) {
        if (key.length() == 1 && Character.isDigit(key.charAt(0))) {
            engine.inputDigit(key.charAt(0) - '0');
        } else {
            switch (key) {
                case "C": engine.clear(); break;
                case "±": engine.toggleSign(); break;
                case "%": engine.percent(); break;
                case "⌫": engine.backspace(); break;
                case ".": engine.inputDecimal(); break;
                case "+": engine.choose(CalculatorEngine.Operation.ADD); break;
                case "-": engine.choose(CalculatorEngine.Operation.SUBTRACT); break;
                case "×": engine.choose(CalculatorEngine.Operation.MULTIPLY); break;
                case "÷": engine.choose(CalculatorEngine.Operation.DIVIDE); break;
                case "=": engine.equalsResult(); break;
                default: throw new IllegalArgumentException("unsupported calculator key");
            }
        }
        refreshDisplay();
    }

    private void refreshDisplay() {
        if (engine.hasError()) {
            display.setText(R.string.error);
            return;
        }
        String text = engine.display();
        if (decimalSeparator != '.') {
            text = text.replace('.', decimalSeparator);
        }
        display.setText(text);
    }

    private boolean isOperator(String key) {
        return "+".equals(key) || "-".equals(key) || "×".equals(key)
                || "÷".equals(key) || "=".equals(key);
    }

    private String descriptionFor(String key) {
        switch (key) {
            case "C": return getString(R.string.clear);
            case "±": return getString(R.string.positive_negative);
            case "%": return getString(R.string.percent);
            case "⌫": return getString(R.string.backspace);
            case ".": return getString(R.string.decimal);
            case "+": return getString(R.string.plus);
            case "-": return getString(R.string.minus);
            case "×": return getString(R.string.multiply);
            case "÷": return getString(R.string.divide);
            case "=": return getString(R.string.equals);
            default: return key;
        }
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
