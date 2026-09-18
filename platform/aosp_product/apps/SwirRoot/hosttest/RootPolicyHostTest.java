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
        RootPolicy.Decision enableUnknownRestore = RootPolicy.evaluateEnable(unknownRestore, true, true);
        require(!enableUnknownRestore.allowed, "enable requires a known non-root restore state before mutation");
        require("expected_nonroot_state_known".equals(enableUnknownRestore.reasonCode), "enable restore-state denial must be explicit");

        RootPolicy.Decision unrootUnknownRestore = RootPolicy.evaluateUnroot(unknownRestore, true, true);
        require(!unrootUnknownRestore.allowed, "unroot requires expected non-root restore state");
        require("expected_nonroot_state_known".equals(unrootUnknownRestore.reasonCode), "unroot restore-state denial must be explicit");

        RootPolicy.Gates unverifiedProfile = new RootPolicy.Gates(true, false, true, true, true, true, true);
        RootPolicy.Decision unrootUnverifiedProfile = RootPolicy.evaluateUnroot(unverifiedProfile, true, true);
        require(!unrootUnverifiedProfile.allowed, "unroot requires the same verified device profile as enable");
        require("verified_device_profile".equals(unrootUnverifiedProfile.reasonCode), "unroot profile denial must be explicit");

        RootPolicy.Gates unsafeUpdateState = new RootPolicy.Gates(true, true, true, true, true, false, true);
        RootPolicy.Decision unrootUnsafeUpdateState = RootPolicy.evaluateUnroot(unsafeUpdateState, true, true);
        require(!unrootUnsafeUpdateState.allowed, "unroot must not mutate boot state during an unsafe update state");
        require("update_state_safe".equals(unrootUnsafeUpdateState.reasonCode), "unroot update-state denial must be explicit");

        require(RootPolicy.evaluateUnroot(all, true, true).allowed, "complete unroot plan should be eligible");
    }

    private static void require(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }
}
