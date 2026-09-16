package org.swir.phoneos.calculator;

import java.math.BigDecimal;
import java.math.MathContext;
import java.math.RoundingMode;

/** Pure-Java calculator state machine. It intentionally has no Android dependency. */
public final class CalculatorEngine {
    public enum Operation { NONE, ADD, SUBTRACT, MULTIPLY, DIVIDE }

    private static final MathContext MATH = new MathContext(16, RoundingMode.HALF_EVEN);
    private BigDecimal accumulator;
    private Operation pending = Operation.NONE;
    private String input = "0";
    private boolean replaceInput = true;
    private boolean error;

    public void clear() {
        accumulator = null;
        pending = Operation.NONE;
        input = "0";
        replaceInput = true;
        error = false;
    }

    public void inputDigit(int digit) {
        if (digit < 0 || digit > 9) {
            throw new IllegalArgumentException("digit out of range");
        }
        recoverFromError();
        if (replaceInput) {
            input = Integer.toString(digit);
            replaceInput = false;
            return;
        }
        if ("0".equals(input)) {
            input = Integer.toString(digit);
        } else if (input.length() < 32) {
            input += digit;
        }
    }

    public void inputDecimal() {
        recoverFromError();
        if (replaceInput) {
            input = "0.";
            replaceInput = false;
        } else if (!input.contains(".")) {
            input += ".";
        }
    }

    public void backspace() {
        if (error) {
            clear();
            return;
        }
        if (replaceInput) {
            return;
        }
        if (input.length() <= 1 || (input.length() == 2 && input.startsWith("-"))) {
            input = "0";
            replaceInput = true;
        } else {
            input = input.substring(0, input.length() - 1);
        }
    }

    public void toggleSign() {
        recoverFromError();
        BigDecimal value = currentValue();
        input = format(value.negate(MATH));
        replaceInput = false;
    }

    public void percent() {
        recoverFromError();
        input = format(currentValue().divide(new BigDecimal("100"), MATH));
        replaceInput = true;
    }

    public void choose(Operation operation) {
        if (operation == null || operation == Operation.NONE) {
            throw new IllegalArgumentException("operation required");
        }
        recoverFromError();
        if (accumulator == null) {
            accumulator = currentValue();
        } else if (!replaceInput && pending != Operation.NONE) {
            accumulator = apply(accumulator, currentValue(), pending);
            if (error) {
                return;
            }
            input = format(accumulator);
        }
        pending = operation;
        replaceInput = true;
    }

    public void equalsResult() {
        if (error || pending == Operation.NONE || accumulator == null) {
            return;
        }
        BigDecimal result = apply(accumulator, currentValue(), pending);
        if (!error) {
            input = format(result);
        }
        accumulator = null;
        pending = Operation.NONE;
        replaceInput = true;
    }

    public String display() {
        return error ? "" : input;
    }

    public boolean hasError() {
        return error;
    }

    public Operation pendingOperation() {
        return pending;
    }

    private void recoverFromError() {
        if (error) {
            clear();
        }
    }

    private BigDecimal currentValue() {
        try {
            return new BigDecimal(input, MATH);
        } catch (NumberFormatException exc) {
            error = true;
            return BigDecimal.ZERO;
        }
    }

    private BigDecimal apply(BigDecimal left, BigDecimal right, Operation operation) {
        try {
            switch (operation) {
                case ADD:
                    return left.add(right, MATH);
                case SUBTRACT:
                    return left.subtract(right, MATH);
                case MULTIPLY:
                    return left.multiply(right, MATH);
                case DIVIDE:
                    if (BigDecimal.ZERO.compareTo(right) == 0) {
                        error = true;
                        return BigDecimal.ZERO;
                    }
                    return left.divide(right, MATH);
                default:
                    return right;
            }
        } catch (ArithmeticException exc) {
            error = true;
            return BigDecimal.ZERO;
        }
    }

    private static String format(BigDecimal value) {
        BigDecimal normalized = value.stripTrailingZeros();
        if (BigDecimal.ZERO.compareTo(normalized) == 0) {
            return "0";
        }
        return normalized.toPlainString();
    }
}
