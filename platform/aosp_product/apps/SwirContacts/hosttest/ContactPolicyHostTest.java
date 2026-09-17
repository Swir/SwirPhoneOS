package org.swir.phoneos.contacts;

public final class ContactPolicyHostTest {
    public static void main(String[] args) {
        check("Alice Smith".equals(ContactPolicy.normalizeName(" Alice Smith ")), "name");
        check("+481234".equals(ContactPolicy.normalizePhone(" +48 (123) 4 ")), "phone");
        check(ContactPolicy.validEmail("a@example.org"), "valid email");
        check(!ContactPolicy.validEmail("invalid@"), "invalid email");
        check(ContactPolicy.validContact("Alice", "+48123", ""), "phone contact");
        check(ContactPolicy.matches("ali", "Alice", "+48123", "a@example.org"), "search");
        String card = ContactPolicy.toVCard("Alice", "+48123", "a@example.org");
        check(card.contains("BEGIN:VCARD"), "vcard begin");
        check(card.contains("TEL:+48123"), "vcard phone");
        check(card.contains("EMAIL:a@example.org"), "vcard email");
    }

    private static void check(boolean condition, String label) {
        if (!condition) throw new AssertionError(label);
    }
}
