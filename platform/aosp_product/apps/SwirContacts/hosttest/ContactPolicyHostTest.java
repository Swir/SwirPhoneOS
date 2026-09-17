package org.swir.phoneos.contacts;

import java.util.ArrayList;

public final class ContactPolicyHostTest {
    public static void main(String[] args) {
        check("Alice Smith".equals(ContactPolicy.normalizeName(" Alice Smith ")), "name");
        check("+481234".equals(ContactPolicy.normalizePhone(" +48 (123) 4 ")), "phone");
        check(ContactPolicy.validEmail("a@example.org"), "valid email");
        check(!ContactPolicy.validEmail("invalid@"), "invalid email");
        check(ContactPolicy.validContact("Alice", "+48123", ""), "phone contact");
        check(ContactPolicy.matches("ali", "Alice", "+48123", "a@example.org"), "search");
        String card = ContactPolicy.toVCard("Alice, Smith", "+48123", "a@example.org");
        check(card.contains("BEGIN:VCARD"), "vcard begin");
        check(card.contains("TEL:+48123"), "vcard phone");
        check(card.contains("EMAIL:a@example.org"), "vcard email");
        ArrayList<String[]> parsed = ContactPolicy.parseVCards(card);
        check(parsed.size() == 1, "parse count");
        check("Alice, Smith".equals(parsed.get(0)[0]), "parse escaped name");
        check("+48123".equals(parsed.get(0)[1]), "parse phone");
        check(ContactPolicy.parseVCards("not a vcard").isEmpty(), "reject invalid");
        StringBuilder huge = new StringBuilder();
        while (huge.length() <= ContactPolicy.MAX_IMPORT_BYTES) huge.append('x');
        check(ContactPolicy.parseVCards(huge.toString()).isEmpty(), "reject oversized import");
    }

    private static void check(boolean condition, String label) {
        if (!condition) throw new AssertionError(label);
    }
}
