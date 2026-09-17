package org.swir.phoneos.contacts;

public final class ContactPolicyHostTest {
    public static void main(String[] args) {
        if (!ContactPolicy.matches("Ada Lovelace", "+47 123", "ada")) throw new AssertionError();
        if (!ContactPolicy.matches("Ada", "+47 123", "123")) throw new AssertionError();
        if (ContactPolicy.matches("Ada", "+47 123", "grace")) throw new AssertionError();
        if (!ContactPolicy.validLookupKey("42-lookup")) throw new AssertionError();
        if (ContactPolicy.validLookupKey("\n")) throw new AssertionError();
        if (!"Ada_Lovelace.vcf".equals(ContactPolicy.vcardFileName("Ada Lovelace"))) throw new AssertionError();
        if (!"contact.vcf".equals(ContactPolicy.vcardFileName("../"))) throw new AssertionError();
    }
}
