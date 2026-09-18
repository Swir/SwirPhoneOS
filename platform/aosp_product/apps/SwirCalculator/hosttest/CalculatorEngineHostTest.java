package org.swir.phoneos.calculator;

/** Dependency-free host test executed by CI with javac/java. */
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
        assertError(engine, "division by zero");

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

        engine.clear();
        engine.inputDigit(9);
        engine.scientific(CalculatorEngine.ScientificOperation.SQRT);
        assertEquals("3", engine.display(), "square root");
        engine.scientific(CalculatorEngine.ScientificOperation.SQUARE);
        assertEquals("9", engine.display(), "square");
        engine.scientific(CalculatorEngine.ScientificOperation.RECIPROCAL);
        assertNear(1.0d / 9.0d, Double.parseDouble(engine.display()), 1.0e-15, "reciprocal");

        engine.clear();
        engine.inputDigit(3);
        engine.inputDigit(0);
        engine.scientific(CalculatorEngine.ScientificOperation.SIN);
        assertNear(0.5d, Double.parseDouble(engine.display()), 1.0e-15, "sin degrees");
        engine.clear();
        engine.inputDigit(6);
        engine.inputDigit(0);
        engine.scientific(CalculatorEngine.ScientificOperation.COS);
        assertNear(0.5d, Double.parseDouble(engine.display()), 1.0e-15, "cos degrees");

        engine.clear();
        engine.inputDigit(9);
        engine.inputDigit(0);
        engine.scientific(CalculatorEngine.ScientificOperation.TAN);
        assertError(engine, "tan singularity");

        engine.clear();
        engine.inputDigit(1);
        engine.inputDigit(0);
        engine.inputDigit(0);
        engine.scientific(CalculatorEngine.ScientificOperation.LOG10);
        assertEquals("2", engine.display(), "log10");
        engine.clear();
        engine.inputDigit(1);
        engine.scientific(CalculatorEngine.ScientificOperation.LN);
        assertEquals("0", engine.display(), "natural log");

        engine.clear();
        engine.inputDigit(4);
        engine.toggleSign();
        engine.scientific(CalculatorEngine.ScientificOperation.ABS);
        assertEquals("4", engine.display(), "absolute value");

        engine.clear();
        engine.inputPi();
        assertNear(Math.PI, Double.parseDouble(engine.display()), 1.0e-15, "pi");
        engine.inputE();
        assertNear(Math.E, Double.parseDouble(engine.display()), 1.0e-15, "e");

        engine.clear();
        engine.toggleAngleMode();
        if (engine.angleMode() != CalculatorEngine.AngleMode.RADIANS) {
            throw new AssertionError("angle mode must toggle to radians");
        }
        engine.inputPi();
        engine.choose(CalculatorEngine.Operation.DIVIDE);
        engine.inputDigit(2);
        engine.equalsResult();
        engine.scientific(CalculatorEngine.ScientificOperation.SIN);
        assertNear(1.0d, Double.parseDouble(engine.display()), 1.0e-15, "sin radians");

        engine.clear();
        engine.inputDigit(0);
        engine.scientific(CalculatorEngine.ScientificOperation.RECIPROCAL);
        assertError(engine, "reciprocal zero");
        engine.inputDigit(1);
        engine.toggleSign();
        engine.scientific(CalculatorEngine.ScientificOperation.SQRT);
        assertError(engine, "sqrt negative");
        engine.inputDigit(0);
        engine.scientific(CalculatorEngine.ScientificOperation.LN);
        assertError(engine, "ln zero");
    }

    private static void assertError(CalculatorEngine engine, String label) {
        if (!engine.hasError()) {
            throw new AssertionError(label + " must enter error state");
        }
    }

    private static void assertEquals(String expected, String actual, String label) {
        if (!expected.equals(actual)) {
            throw new AssertionError(label + ": expected=" + expected + " actual=" + actual);
        }
    }

    private static void assertNear(double expected, double actual, double tolerance, String label) {
        if (Math.abs(expected - actual) > tolerance) {
            throw new AssertionError(label + ": expected=" + expected + " actual=" + actual);
        }
    }
}
