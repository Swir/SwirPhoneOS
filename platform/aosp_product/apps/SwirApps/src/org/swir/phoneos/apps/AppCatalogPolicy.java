package org.swir.phoneos.apps;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Locale;

public final class AppCatalogPolicy {
    public static final int MAX_QUERY = 120;
    private AppCatalogPolicy() {}
    public static String normalizeQuery(String value) { if (value == null) return ""; String trimmed=value.trim(); if (trimmed.length()>MAX_QUERY) trimmed=trimmed.substring(0,MAX_QUERY); return trimmed.toLowerCase(Locale.ROOT); }
    public static boolean matches(String label,String packageName,String query) { String needle=normalizeQuery(query); if (needle.isEmpty()) return true; return (label==null?"":label.toLowerCase(Locale.ROOT)).contains(needle)||(packageName==null?"":packageName.toLowerCase(Locale.ROOT)).contains(needle); }
    public static boolean validPackageName(String value) { return value!=null && value.matches("[A-Za-z0-9_]+(\\.[A-Za-z0-9_]+)+") && value.length()<=255; }
    public static String sha256(byte[] value) { if (value==null||value.length==0) return ""; try { byte[] digest=MessageDigest.getInstance("SHA-256").digest(value); StringBuilder out=new StringBuilder(64); for(byte b:digest) out.append(String.format(Locale.ROOT,"%02X",b&0xff)); return out.toString(); } catch(NoSuchAlgorithmException impossible) { throw new IllegalStateException(impossible); } }
    public static String shortDigest(String digest) { if (digest==null||!digest.matches("[0-9A-Fa-f]{64}")) return ""; return digest.substring(0,16).toUpperCase(Locale.ROOT); }
}
