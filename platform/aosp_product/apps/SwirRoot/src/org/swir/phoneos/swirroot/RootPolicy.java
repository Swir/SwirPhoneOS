package org.swir.phoneos.swirroot;

/**
 * Pure-Java fail-closed policy for the future first-party root mutation backend.
 *
 * This class plans whether a transition is eligible. It never changes boot images,
 * partitions, bootloader state, verified boot state, or process privileges.
 */
public final class RootPolicy {
    public enum State {
        UNAVAILABLE,
        ROOT_OFF,
        ROOT_ON,
        TRANSITION
    }

    public static final class Gates {
        public final boolean exactBuildMatch;
        public final boolean verifiedDeviceProfile;
        public final boolean ownerConfirmed;
        public final boolean rollbackMaterialVerified;
        public final boolean journalAvailable;
        public final boolean updateStateSafe;
        public final boolean expectedNonRootStateKnown;

        public Gates(
                boolean exactBuildMatch,
                boolean verifiedDeviceProfile,
                boolean ownerConfirmed,
                boolean rollbackMaterialVerified,
                boolean journalAvailable,
                boolean updateStateSafe,
                boolean expectedNonRootStateKnown) {
            this.exactBuildMatch = exactBuildMatch;
            this.verifiedDeviceProfile = verifiedDeviceProfile;
            this.ownerConfirmed = ownerConfirmed;
            this.rollbackMaterialVerified = rollbackMaterialVerified;
            this.journalAvailable = journalAvailable;
            this.updateStateSafe = updateStateSafe;
            this.expectedNonRootStateKnown = expectedNonRootStateKnown;
        }
    }

    public static final class Decision {
        public final boolean allowed;
        public final State proposedState;
        public final String reasonCode;

        private Decision(boolean allowed, State proposedState, String reasonCode) {
            this.allowed = allowed;
            this.proposedState = proposedState;
            this.reasonCode = reasonCode;
        }
    }

    private RootPolicy() {}

    public static Decision evaluateEnable(
            Gates gates, boolean writeBackendEnabled, boolean supportedBuild) {
        if (!writeBackendEnabled || !supportedBuild) {
            return deny("unsupported_build");
        }
        if (!gates.exactBuildMatch) return deny("exact_build_match");
        if (!gates.verifiedDeviceProfile) return deny("verified_device_profile");
        if (!gates.ownerConfirmed) return deny("owner_confirmation");
        if (!gates.rollbackMaterialVerified) return deny("rollback_material_verified");
        if (!gates.journalAvailable) return deny("journal_available");
        if (!gates.updateStateSafe) return deny("update_state_safe");
        if (!gates.expectedNonRootStateKnown) return deny("expected_nonroot_state_known");
        return new Decision(true, State.TRANSITION, "ready_enable");
    }

    public static Decision evaluateUnroot(
            Gates gates, boolean writeBackendEnabled, boolean supportedBuild) {
        if (!writeBackendEnabled || !supportedBuild) {
            return deny("unsupported_build");
        }
        if (!gates.exactBuildMatch) return deny("exact_build_match");
        if (!gates.verifiedDeviceProfile) return deny("verified_device_profile");
        if (!gates.ownerConfirmed) return deny("owner_confirmation");
        if (!gates.rollbackMaterialVerified) return deny("rollback_material_verified");
        if (!gates.journalAvailable) return deny("journal_available");
        if (!gates.updateStateSafe) return deny("update_state_safe");
        if (!gates.expectedNonRootStateKnown) return deny("expected_nonroot_state_known");
        return new Decision(true, State.TRANSITION, "ready_unroot");
    }

    private static Decision deny(String reason) {
        return new Decision(false, State.UNAVAILABLE, reason);
    }
}
