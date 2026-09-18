package org.swir.phoneos.calculator;

import android.app.Activity;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.GridLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.text.DecimalFormatSymbols;

/** Offline SwirPhoneOS calculator with basic and source-stage scientific functions. */
public final class MainActivity extends Activity {
    private final CalculatorEngine engine = new CalculatorEngine();
    private TextView display;
    private Button angleModeButton;
    private char decimalSeparator;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        decimalSeparator = DecimalFormatSymbols.getInstance().getDecimalSeparator();
        getWindow().setStatusBarColor(getColor(R.color.swir_background));
        getWindow().setNavigationBarColor(getColor(R.color.swir_surface));
        setContentView(buildUi());
        refreshDisplay();
        refreshAngleMode();
    }

    private View buildUi() {
        int spaceXs = getResources().getDimensionPixelSize(R.dimen.swir_space_xs);
        int spaceSm = getResources().getDimensionPixelSize(R.dimen.swir_space_sm);
        int spaceMd = getResources().getDimensionPixelSize(R.dimen.swir_space_md);

        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(getColor(R.color.swir_background));

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(spaceMd, spaceMd, spaceMd, spaceMd);
        root.setLayoutDirection(View.LAYOUT_DIRECTION_LOCALE);
        scroll.addView(root, new ScrollView.LayoutParams(
                ScrollView.LayoutParams.MATCH_PARENT, ScrollView.LayoutParams.WRAP_CONTENT));

        TextView title = new TextView(this);
        title.setText(R.string.app_name);
        title.setTextColor(getColor(R.color.swir_text_primary));
        title.setTextSize(24);
        root.addView(title);

        TextView subtitle = new TextView(this);
        subtitle.setText(R.string.scientific_mode);
        subtitle.setTextColor(getColor(R.color.swir_text_secondary));
        subtitle.setTextSize(14);
        subtitle.setPadding(0, spaceXs, 0, spaceSm);
        root.addView(subtitle);

        display = new TextView(this);
        display.setTextColor(getColor(R.color.swir_text_primary));
        display.setTextSize(42);
        display.setGravity(Gravity.END | Gravity.CENTER_VERTICAL);
        display.setMinHeight(dp(104));
        display.setContentDescription(getString(R.string.display_description));
        root.addView(display, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        TextView scientificLabel = new TextView(this);
        scientificLabel.setText(R.string.scientific_functions);
        scientificLabel.setTextColor(getColor(R.color.swir_text_secondary));
        scientificLabel.setTextSize(13);
        scientificLabel.setPadding(0, spaceSm, 0, spaceXs);
        root.addView(scientificLabel);

        GridLayout scientific = new GridLayout(this);
        scientific.setColumnCount(4);
        scientific.setUseDefaultMargins(false);
        scientific.setAlignmentMode(GridLayout.ALIGN_BOUNDS);
        scientific.setLayoutDirection(View.LAYOUT_DIRECTION_LOCALE);
        scientific.addView(scientificButton(R.string.sine_short, R.string.sine, CalculatorEngine.ScientificOperation.SIN), cellParams());
        scientific.addView(scientificButton(R.string.cosine_short, R.string.cosine, CalculatorEngine.ScientificOperation.COS), cellParams());
        scientific.addView(scientificButton(R.string.tangent_short, R.string.tangent, CalculatorEngine.ScientificOperation.TAN), cellParams());
        scientific.addView(scientificButton(R.string.square_root_short, R.string.square_root, CalculatorEngine.ScientificOperation.SQRT), cellParams());
        scientific.addView(scientificButton(R.string.natural_log_short, R.string.natural_log, CalculatorEngine.ScientificOperation.LN), cellParams());
        scientific.addView(scientificButton(R.string.base10_log_short, R.string.base10_log, CalculatorEngine.ScientificOperation.LOG10), cellParams());
        scientific.addView(scientificButton(R.string.square_short, R.string.square, CalculatorEngine.ScientificOperation.SQUARE), cellParams());
        scientific.addView(scientificButton(R.string.reciprocal_short, R.string.reciprocal, CalculatorEngine.ScientificOperation.RECIPROCAL), cellParams());
        scientific.addView(constantButton(R.string.pi_short, R.string.pi_constant, true), cellParams());
        scientific.addView(constantButton(R.string.e_short, R.string.e_constant, false), cellParams());
        scientific.addView(scientificButton(R.string.absolute_short, R.string.absolute_value, CalculatorEngine.ScientificOperation.ABS), cellParams());
        angleModeButton = new Button(this);
        configureButton(angleModeButton, false);
        angleModeButton.setContentDescription(getString(R.string.switch_angle_mode));
        angleModeButton.setOnClickListener(v -> {
            engine.toggleAngleMode();
            refreshAngleMode();
        });
        scientific.addView(angleModeButton, cellParams());
        root.addView(scientific, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        TextView basicLabel = new TextView(this);
        basicLabel.setText(R.string.basic_functions);
        basicLabel.setTextColor(getColor(R.color.swir_text_secondary));
        basicLabel.setTextSize(13);
        basicLabel.setPadding(0, spaceSm, 0, spaceXs);
        root.addView(basicLabel);

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
        return scroll;
    }

    private Button scientificButton(int label, int description, CalculatorEngine.ScientificOperation operation) {
        Button button = new Button(this);
        configureButton(button, false);
        button.setText(label);
        button.setContentDescription(getString(description));
        button.setOnClickListener(v -> {
            engine.scientific(operation);
            refreshDisplay();
        });
        return button;
    }

    private Button constantButton(int label, int description, boolean pi) {
        Button button = new Button(this);
        configureButton(button, false);
        button.setText(label);
        button.setContentDescription(getString(description));
        button.setOnClickListener(v -> {
            if (pi) engine.inputPi();
            else engine.inputE();
            refreshDisplay();
        });
        return button;
    }

    private Button makeButton(final String key) {
        Button button = new Button(this);
        configureButton(button, isOperator(key));
        button.setText(".".equals(key) ? String.valueOf(decimalSeparator) : key);
        button.setContentDescription(descriptionFor(key));
        button.setOnClickListener(view -> handleKey(key));
        return button;
    }

    private void configureButton(Button button, boolean accented) {
        button.setAllCaps(false);
        button.setTextSize(18);
        button.setMinHeight(getResources().getDimensionPixelSize(R.dimen.swir_touch_min));
        button.setTextColor(getColor(R.color.swir_text_primary));
        button.setBackgroundColor(getColor(accented ? R.color.swir_accent : R.color.swir_surface_alt));
    }

    private GridLayout.LayoutParams cellParams() {
        GridLayout.LayoutParams params = new GridLayout.LayoutParams();
        params.width = 0;
        params.height = dp(58);
        params.columnSpec = GridLayout.spec(GridLayout.UNDEFINED, 1f);
        int margin = getResources().getDimensionPixelSize(R.dimen.swir_space_xs);
        params.setMargins(margin, margin, margin, margin);
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

    private void refreshAngleMode() {
        if (angleModeButton == null) return;
        angleModeButton.setText(engine.angleMode() == CalculatorEngine.AngleMode.DEGREES
                ? R.string.angle_degrees_short : R.string.angle_radians_short);
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
