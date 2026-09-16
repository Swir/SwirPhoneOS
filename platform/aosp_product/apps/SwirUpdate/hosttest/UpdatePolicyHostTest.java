package org.swir.phoneos.update;

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
    }

    private static void check(boolean value, String label) {
        if (!value) throw new AssertionError(label);
    }
}
