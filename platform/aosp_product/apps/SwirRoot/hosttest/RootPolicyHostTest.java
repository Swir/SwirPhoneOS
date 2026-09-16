package org.swir.phoneos.swirroot;

public final class RootPolicyHostTest {
    public static void main(String[] args) {
        RootPolicy.Gates all = new RootPolicy.Gates(true, true, true, true, true, true, true);

        RootPolicy.Decision noBackend = RootPolicy.evaluateEnable(all, false, false);
        require(!noBackend.allowed, "source stage must deny root enable");
        require("unsupported_build".equals(noBackend.reasonCode), "unsupported build reason must be explicit");
        require(noBackend.proposedState == RootPolicy.State.UNAVAILABLE, "denied transitions stay unavailable");

        RootPolicy.Decision plan = RootPolicy.evaluateEnable(all, true, true);
        require(plan.allowed, "all safety gates should make an enable plan eligible");
        require(plan.proposedState == RootPolicy.State.TRANSITION, "eligible plan enters transition state only");

        RootPolicy.Gates noRollback = new RootPolicy.Gates(true, true, true, false, true, true, true);
        require(!RootPolicy.evaluateEnable(noRollback, true, true).allowed, "rollback is mandatory");

        RootPolicy.Gates noOwner = new RootPolicy.Gates(true, true, false, true, true, true, true);
        require(!RootPolicy.evaluateEnable(noOwner, true, true).allowed, "owner confirmation is mandatory");

        RootPolicy.Gates unknownRestore = new RootPolicy.Gates(true, true, true, true, true, true, false);
        RootPolicy.Decision unroot = RootPolicy.evaluateUnroot(unknownRestore, true, true);
        require(!unroot.allowed, "unroot requires expected non-root restore state");
        require("expected_nonroot_state_known".equals(unroot.reasonCode), "unroot denial reason must be explicit");

        require(RootPolicy.evaluateUnroot(all, true, true).allowed, "complete unroot plan should be eligible");
    }

    private static void require(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }
}
