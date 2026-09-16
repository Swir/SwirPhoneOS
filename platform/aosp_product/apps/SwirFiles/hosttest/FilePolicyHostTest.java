package org.swir.phoneos.files;

public final class FilePolicyHostTest {
    public static void main(String[] args) {
        require(FilePolicy.validName("Photos 2026"));
        require(!FilePolicy.validName(""));
        require(!FilePolicy.validName(".."));
        require(!FilePolicy.validName("a/b"));
        require(!FilePolicy.validName("a\\b"));
        require(FilePolicy.matches("Holiday.JPG", "holiday"));
        require(!FilePolicy.matches("notes.txt", "photo"));
        require(FilePolicy.matches("anything", "   "));
    }

    private static void require(boolean value) {
        if (!value) throw new AssertionError("FilePolicy contract failed");
    }
}
