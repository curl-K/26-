package edu.whpu.reagent;

import org.junit.jupiter.api.Test;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.junit.jupiter.api.Assertions.assertTrue;

class SeedHashTest {

    @Test
    void demoPasswordsMatchTheMigration() throws Exception {
        String sql = Files.readString(Path.of("src/main/resources/db/migration/V1__init.sql"));
        BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();
        assertTrue(encoder.matches("manager123", hash(sql, "manager")));
        assertTrue(encoder.matches("chen123", hash(sql, "chen")));
        assertTrue(encoder.matches("li123", hash(sql, "li")));
    }

    private static String hash(String sql, String username) {
        Matcher matcher = Pattern.compile("\\('" + username + "', '[^']+', '[^']+', '(\\$2[ab]\\$[^']+)'").matcher(sql);
        assertTrue(matcher.find(), username);
        return matcher.group(1);
    }
}
