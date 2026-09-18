package org.swir.phoneos.update;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.Signature;

public final class UpdatePolicyHostTest {
    public static void main(String[] args) throws Exception {
        check(UpdatePolicy.channelForBuild("user", "release-keys") == UpdatePolicy.Channel.STABLE, "stable");
        check(UpdatePolicy.channelForBuild("userdebug", "test-keys") == UpdatePolicy.Channel.BETA, "beta");
        check(UpdatePolicy.channelForBuild("eng", "test-keys") == UpdatePolicy.Channel.DEVELOPER, "developer");
        check(UpdatePolicy.fingerprintMatches("a", "a"), "fingerprint exact");
        check(!UpdatePolicy.fingerprintMatches("a", "b"), "fingerprint mismatch");

        byte[] metadata = "{\"version\":1,\"channel\":\"stable\"}".getBytes(StandardCharsets.UTF_8);
        KeyPairGenerator generator = KeyPairGenerator.getInstance("RSA");
        generator.initialize(2048);
        KeyPair pair = generator.generateKeyPair();
        Signature signer = Signature.getInstance("SHA256withRSA");
        signer.initSign(pair.getPrivate());
        signer.update(metadata);
        byte[] signature = signer.sign();
        check(UpdatePolicy.verifyDetachedSignature(metadata, signature, pair.getPublic()), "valid signature");
        metadata[0] ^= 1;
        check(!UpdatePolicy.verifyDetachedSignature(metadata, signature, pair.getPublic()), "tamper rejected");
        check(UpdatePolicy.sha256Hex("abc".getBytes(StandardCharsets.UTF_8)).equals("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"), "sha256");

        byte[] candidate = new byte[]{0x50, 0x4b, 0x03, 0x04, 0x01, 0x02, 0x03, 0x04};
        UpdatePolicy.PackageInspection ready = UpdatePolicy.inspectPackage(
                "swirphoneos-update.zip", candidate.length, new ByteArrayInputStream(candidate));
        check(ready.reviewReady(), "local candidate review ready");
        check(ready.state() == UpdatePolicy.PackageState.REVIEW_READY_UNTRUSTED, "candidate remains untrusted");
        check(ready.sizeBytes() == candidate.length, "candidate size");
        check(ready.sha256().equals(UpdatePolicy.sha256Hex(candidate)), "candidate digest");

        check(!UpdatePolicy.safePackageName("../update.zip"), "path traversal name rejected");
        check(!UpdatePolicy.safePackageName("update.bin"), "non-zip name rejected");
        check(UpdatePolicy.inspectPackage("update.bin", candidate.length, new ByteArrayInputStream(candidate)).state()
                == UpdatePolicy.PackageState.REJECTED_NAME, "bad name state");
        check(UpdatePolicy.inspectPackage("update.zip", UpdatePolicy.MAX_PACKAGE_BYTES + 1L, new ByteArrayInputStream(candidate)).state()
                == UpdatePolicy.PackageState.REJECTED_SIZE, "oversize declaration rejected");
        check(UpdatePolicy.inspectPackage("update.zip", candidate.length + 1L, new ByteArrayInputStream(candidate)).state()
                == UpdatePolicy.PackageState.REJECTED_SIZE, "size drift rejected");
        check(UpdatePolicy.inspectPackage("update.zip", 4L, new ByteArrayInputStream(new byte[]{1, 2, 3, 4})).state()
                == UpdatePolicy.PackageState.REJECTED_FORMAT, "non-zip rejected");
        check(UpdatePolicy.inspectPackage("update.zip", -1L, null).state()
                == UpdatePolicy.PackageState.READ_FAILED, "null stream fails closed");

        InputStream broken = new InputStream() {
            @Override public int read() throws IOException { throw new IOException("expected"); }
            @Override public int read(byte[] bytes) throws IOException { throw new IOException("expected"); }
        };
        check(UpdatePolicy.inspectPackage("update.zip", -1L, broken).state()
                == UpdatePolicy.PackageState.READ_FAILED, "read error fails closed");

        String current = "swir/device/product:17/CP2A.260605.016/1:userdebug/test-keys";
        String target = "swir/device/product:17/CP2A.260605.016/2:userdebug/release-keys";
        String keyId = "swir-release-rsa-2026-01";
        String canonical = String.join("\n",
                UpdatePolicy.MANIFEST_HEADER,
                "source_fingerprint=" + current,
                "target_fingerprint=" + target,
                "channel=BETA",
                "package_name=swirphoneos-update.zip",
                "package_size=" + candidate.length,
                "package_sha256=" + ready.sha256(),
                "key_id=" + keyId,
                "rollback_required=true");
        byte[] canonicalBytes = canonical.getBytes(StandardCharsets.UTF_8);
        byte[] canonicalSignature = sign(canonicalBytes, pair);

        UpdatePolicy.OtaManifest parsed = UpdatePolicy.parseCanonicalManifest(canonicalBytes);
        check(parsed != null, "canonical manifest parsed");
        check(parsed.packageSize() == candidate.length, "manifest package size");
        check(parsed.rollbackRequired(), "manifest rollback policy");

        UpdatePolicy.ManifestReview manifestReady = UpdatePolicy.reviewSignedManifest(
                canonicalBytes,
                canonicalSignature,
                pair.getPublic(),
                keyId,
                current,
                UpdatePolicy.Channel.BETA,
                "swirphoneos-update.zip",
                ready);
        check(manifestReady.authenticReviewReady(), "signed manifest review ready");
        check(manifestReady.state() == UpdatePolicy.ManifestState.AUTHENTIC_REVIEW_READY_NOT_STAGED, "manifest state");
        check(!manifestReady.stagingAllowed(), "signed review does not authorize staging");

        byte[] tamperedManifest = canonical.replace("package_size=8", "package_size=9").getBytes(StandardCharsets.UTF_8);
        check(UpdatePolicy.reviewSignedManifest(
                tamperedManifest, canonicalSignature, pair.getPublic(), keyId, current,
                UpdatePolicy.Channel.BETA, "swirphoneos-update.zip", ready).state()
                == UpdatePolicy.ManifestState.REJECTED_SIGNATURE, "metadata tamper rejected by signature");
        check(UpdatePolicy.reviewSignedManifest(
                canonicalBytes, canonicalSignature, pair.getPublic(), "other-key", current,
                UpdatePolicy.Channel.BETA, "swirphoneos-update.zip", ready).state()
                == UpdatePolicy.ManifestState.REJECTED_KEY_ID, "wrong key id rejected");
        check(UpdatePolicy.reviewSignedManifest(
                canonicalBytes, canonicalSignature, pair.getPublic(), keyId, "other/source/build",
                UpdatePolicy.Channel.BETA, "swirphoneos-update.zip", ready).state()
                == UpdatePolicy.ManifestState.REJECTED_SOURCE_BUILD, "wrong source build rejected");
        check(UpdatePolicy.reviewSignedManifest(
                canonicalBytes, canonicalSignature, pair.getPublic(), keyId, current,
                UpdatePolicy.Channel.STABLE, "swirphoneos-update.zip", ready).state()
                == UpdatePolicy.ManifestState.REJECTED_CHANNEL, "wrong channel rejected");
        check(UpdatePolicy.reviewSignedManifest(
                canonicalBytes, canonicalSignature, pair.getPublic(), keyId, current,
                UpdatePolicy.Channel.BETA, "different.zip", ready).state()
                == UpdatePolicy.ManifestState.REJECTED_PACKAGE_BINDING, "wrong selected package rejected");

        String noRollback = canonical.replace("rollback_required=true", "rollback_required=false");
        byte[] noRollbackBytes = noRollback.getBytes(StandardCharsets.UTF_8);
        check(UpdatePolicy.reviewSignedManifest(
                noRollbackBytes, sign(noRollbackBytes, pair), pair.getPublic(), keyId, current,
                UpdatePolicy.Channel.BETA, "swirphoneos-update.zip", ready).state()
                == UpdatePolicy.ManifestState.REJECTED_ROLLBACK_POLICY, "rollback requirement enforced");
        check(UpdatePolicy.parseCanonicalManifest((canonical + "\nextra=value").getBytes(StandardCharsets.UTF_8)) == null,
                "unknown field rejected");
        check(UpdatePolicy.parseCanonicalManifest(canonical.replace("package_sha256=", "package_sha256=ABC").getBytes(StandardCharsets.UTF_8)) == null,
                "noncanonical digest rejected");
    }

    private static byte[] sign(byte[] data, KeyPair pair) throws Exception {
        Signature signer = Signature.getInstance("SHA256withRSA");
        signer.initSign(pair.getPrivate());
        signer.update(data);
        return signer.sign();
    }

    private static void check(boolean value, String label) {
        if (!value) throw new AssertionError(label);
    }
}
