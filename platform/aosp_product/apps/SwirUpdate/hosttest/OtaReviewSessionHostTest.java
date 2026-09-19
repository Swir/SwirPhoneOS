package org.swir.phoneos.update;

import java.io.ByteArrayInputStream;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.Signature;
import java.util.Collections;
import java.util.EnumSet;

public final class OtaReviewSessionHostTest {
    public static void main(String[] args) throws Exception {
        byte[] packageBytes = new byte[]{0x50, 0x4b, 0x03, 0x04, 0x01, 0x02, 0x03, 0x04};
        UpdatePolicy.PackageInspection inspection = UpdatePolicy.inspectPackage(
                "swirphoneos-update.zip",
                packageBytes.length,
                new ByteArrayInputStream(packageBytes));
        check(inspection.reviewReady(), "package preflight ready");

        KeyPair pair = rsaPair();
        String keyId = "swir-beta-2026-01";
        OtaTrustStore store = new OtaTrustStore(Collections.singletonList(new OtaTrustStore.Entry(
                keyId,
                pair.getPublic(),
                UpdatePolicy.sha256Hex(pair.getPublic().getEncoded()),
                OtaTrustStore.KeyStatus.ACTIVE,
                EnumSet.of(UpdatePolicy.Channel.BETA))));

        String current = "swir/device/product:17/CP2A.260605.016/1:userdebug/test-keys";
        String target = "swir/device/product:17/CP2A.260605.016/2:userdebug/release-keys";
        byte[] manifest = canonicalManifest(current, target, keyId, inspection);
        byte[] signature = sign(manifest, pair);

        OtaReviewSession session = new OtaReviewSession();
        check(session.review(store, current, UpdatePolicy.Channel.BETA).state() == OtaReviewSession.State.NEED_PACKAGE,
                "empty session needs package");
        check(!session.selectSignature(new ByteArrayInputStream(signature)), "signature cannot precede manifest");

        session.setPackage("swirphoneos-update.zip", inspection);
        check(session.review(store, current, UpdatePolicy.Channel.BETA).state() == OtaReviewSession.State.NEED_MANIFEST,
                "ready package needs manifest");
        check(session.selectManifest(new ByteArrayInputStream(manifest)), "canonical manifest accepted");
        check(session.review(store, current, UpdatePolicy.Channel.BETA).state() == OtaReviewSession.State.NEED_SIGNATURE,
                "manifest needs detached signature");
        check(session.selectSignature(new ByteArrayInputStream(signature)), "bounded signature accepted");
        OtaReviewSession.Review ready = session.review(store, current, UpdatePolicy.Channel.BETA);
        check(ready.state() == OtaReviewSession.State.AUTHENTIC_REVIEW_READY_NOT_STAGED, "exact review ready");
        check(ready.authenticReviewReady(), "ready helper true");
        check(!ready.stagingAllowed(), "review never stages");
        check(session.manifestSha256().length() == 64, "manifest digest exposed");
        check(session.signatureSha256().length() == 64, "signature digest exposed");
        check(session.parsedManifest() != null && target.equals(session.parsedManifest().targetFingerprint()),
                "parsed target retained");

        byte[] tamperedSignature = signature.clone();
        tamperedSignature[0] ^= 1;
        check(session.selectSignature(new ByteArrayInputStream(tamperedSignature)), "tampered signature bytes still bounded input");
        OtaReviewSession.Review tampered = session.review(store, current, UpdatePolicy.Channel.BETA);
        check(tampered.state() == OtaReviewSession.State.MANIFEST_POLICY_REJECTED, "signature tamper rejected by policy");
        check(tampered.manifestState() == UpdatePolicy.ManifestState.REJECTED_SIGNATURE, "signature reason preserved");

        session.setPackage("swirphoneos-update.zip", inspection);
        check(!session.manifestReady() && !session.signatureReady(), "new package invalidates old signed artifacts");
        check(session.review(store, current, UpdatePolicy.Channel.BETA).state() == OtaReviewSession.State.NEED_MANIFEST,
                "replacement package requires fresh metadata");

        byte[] oversized = new byte[UpdatePolicy.MAX_MANIFEST_BYTES + 1];
        check(!session.selectManifest(new ByteArrayInputStream(oversized)), "oversized manifest rejected");
        check(session.review(store, current, UpdatePolicy.Channel.BETA).state() == OtaReviewSession.State.MANIFEST_REJECTED,
                "manifest rejection state retained");

        session.setPackage("swirphoneos-update.zip", inspection);
        check(session.selectManifest(new ByteArrayInputStream(manifest)), "manifest can be reselected");
        byte[] oversizedSignature = new byte[OtaReviewSession.MAX_SIGNATURE_BYTES + 1];
        check(!session.selectSignature(new ByteArrayInputStream(oversizedSignature)), "oversized signature rejected");
        check(session.review(store, current, UpdatePolicy.Channel.BETA).state() == OtaReviewSession.State.SIGNATURE_REJECTED,
                "signature rejection state retained");

        session.setPackage("swirphoneos-update.zip", inspection);
        check(session.selectManifest(new ByteArrayInputStream(manifest)), "manifest ready for empty trust store");
        check(session.selectSignature(new ByteArrayInputStream(signature)), "signature ready for empty trust store");
        OtaReviewSession.Review noTrust = session.review(DefaultOtaTrustStore.create(), current, UpdatePolicy.Channel.BETA);
        check(noTrust.state() == OtaReviewSession.State.TRUST_REJECTED, "empty production trust store fails closed");
        check(noTrust.trustState() == OtaTrustStore.ResolveState.UNKNOWN_KEY, "unknown key reason preserved");
        check(!noTrust.stagingAllowed(), "trust rejection never stages");

        check(OtaReviewSession.readBounded(null, 8) == null, "null input rejected");
        check(OtaReviewSession.readBounded(new ByteArrayInputStream(new byte[0]), 8) == null, "empty input rejected");
        check(OtaReviewSession.readBounded(new ByteArrayInputStream(new byte[9]), 8) == null, "bounded read rejects overflow");
    }

    private static KeyPair rsaPair() throws Exception {
        KeyPairGenerator generator = KeyPairGenerator.getInstance("RSA");
        generator.initialize(2048);
        return generator.generateKeyPair();
    }

    private static byte[] canonicalManifest(
            String current,
            String target,
            String keyId,
            UpdatePolicy.PackageInspection inspection) {
        String text = UpdatePolicy.MANIFEST_HEADER + "\n"
                + "source_fingerprint=" + current + "\n"
                + "target_fingerprint=" + target + "\n"
                + "channel=BETA\n"
                + "package_name=swirphoneos-update.zip\n"
                + "package_size=" + inspection.sizeBytes() + "\n"
                + "package_sha256=" + inspection.sha256() + "\n"
                + "key_id=" + keyId + "\n"
                + "rollback_required=true";
        return text.getBytes(java.nio.charset.StandardCharsets.UTF_8);
    }

    private static byte[] sign(byte[] manifest, KeyPair pair) throws Exception {
        Signature signer = Signature.getInstance("SHA256withRSA");
        signer.initSign(pair.getPrivate());
        signer.update(manifest);
        return signer.sign();
    }

    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}
