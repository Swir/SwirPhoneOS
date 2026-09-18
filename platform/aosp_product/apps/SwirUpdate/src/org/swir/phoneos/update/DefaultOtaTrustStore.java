package org.swir.phoneos.update;

/**
 * Production trust-anchor entry point for Swir Update.
 *
 * Deliberately empty until release engineering provisions reviewed public OTA verification keys.
 * This prevents test keys, ad-hoc keys or caller-supplied keys from silently becoming production
 * trust anchors. Provisioning a real key must be an explicit, reviewable source change.
 */
public final class DefaultOtaTrustStore {
    private DefaultOtaTrustStore() {}

    public static OtaTrustStore create() {
        return OtaTrustStore.empty();
    }
}