package org.swir.phoneos.calculator;

/** Tiny dependency-free host test executed by CI with javac/java. */
public final class CalculatorEngineHostTest {
    public static void main(String[] args) {
        CalculatorEngine engine = new CalculatorEngine();
        engine.inputDigit(1);
        engine.inputDigit(2);
        engine.choose(CalculatorEngine.Operation.ADD);
        engine.inputDigit(7);
        engine.equalsResult();
        assertEquals("19", engine.display(), "addition");

        engine.clear();
        engine.inputDigit(8);
        engine.choose(CalculatorEngine.Operation.DIVIDE);
        engine.inputDigit(0);
        engine.equalsResult();
        if (!engine.hasError()) {
            throw new AssertionError("division by zero must enter error state");
        }

        engine.inputDigit(5);
        assertEquals("5", engine.display(), "digit input must recover from error");
        engine.toggleSign();
        assertEquals("-5", engine.display(), "toggle sign");
        engine.percent();
        assertEquals("-0.05", engine.display(), "percent");

        engine.clear();
        engine.inputDigit(1);
        engine.inputDecimal();
        engine.inputDigit(5);
        engine.choose(CalculatorEngine.Operation.MULTIPLY);
        engine.inputDigit(2);
        engine.equalsResult();
        assertEquals("3", engine.display(), "decimal multiplication");
    }

    private static void assertEquals(String expected, String actual, String label) {
        if (!expected.equals(actual)) {
            throw new AssertionError(label + ": expected=" + expected + " actual=" + actual);
        }
    }
}
