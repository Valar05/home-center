package com.homecenter.operatoroverlay;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/**
 * Pure-Java parser for the canonical heartbeat skill-light wire envelope.
 *
 * This is source-side semantic ingestion only. It does not own transport,
 * rendering, the Operator Overlay service, phone execution, or P0 recovery.
 */
public final class HeartbeatEnvelopeParser {
    public static final String SCHEMA = "heartbeat-skill-lights.v1";
    public static final int MAX_LIGHTS = 64;
    private static final int MAX_JSON_DEPTH = 32;
    private static final int MAX_STRING_CHARS = 8192;

    public static final class Pulse {
        public final String pulseId;
        public final boolean complete;
        public final List<HeartbeatSkillPolicy.Candidate> candidates;

        private Pulse(
                String pulseId,
                boolean complete,
                List<HeartbeatSkillPolicy.Candidate> candidates) {
            this.pulseId = pulseId;
            this.complete = complete;
            this.candidates = Collections.unmodifiableList(new ArrayList<>(candidates));
        }
    }

    public static final class Result {
        public final Pulse pulse;
        public final String boundary;

        private Result(Pulse pulse, String boundary) {
            this.pulse = pulse;
            this.boundary = clean(boundary);
        }

        public boolean accepted() {
            return pulse != null;
        }
    }

    private HeartbeatEnvelopeParser() {
    }

    public static Result parse(String payloadJson) {
        if (payloadJson == null || payloadJson.trim().isEmpty()) {
            return reject("Heartbeat envelope is empty.");
        }
        try {
            Object parsed = new JsonCursor(payloadJson).parseDocument();
            Map<String, Object> root = asObject(parsed, "Heartbeat envelope root must be an object.");

            String schema = requiredString(root, "schema");
            if (!SCHEMA.equals(schema)) {
                throw new ParseFailure("Unsupported heartbeat envelope schema: " + schema);
            }

            String pulseId = requiredString(root, "pulseId");
            boolean complete = requiredBoolean(root, "complete");
            List<Object> rawLights = requiredArray(root, "lights");
            if (rawLights.size() > MAX_LIGHTS) {
                throw new ParseFailure(
                        "Heartbeat envelope exceeds " + MAX_LIGHTS + " lights.");
            }

            List<HeartbeatSkillPolicy.Candidate> candidates = new ArrayList<>();
            Set<String> seenIds = new HashSet<>();
            for (int index = 0; index < rawLights.size(); index++) {
                Map<String, Object> light = asObject(
                        rawLights.get(index),
                        "Light " + index + " must be an object.");
                HeartbeatSkillPolicy.Candidate candidate = parseCandidate(light, index);
                String key = candidate.id.toLowerCase(Locale.ROOT);
                if (!seenIds.add(key)) {
                    throw new ParseFailure("Duplicate heartbeat light id: " + candidate.id);
                }
                candidates.add(candidate);
            }

            return new Result(new Pulse(pulseId, complete, candidates), "");
        } catch (ParseFailure failure) {
            return reject(failure.getMessage());
        } catch (RuntimeException unexpected) {
            return reject("Heartbeat envelope parser rejected unexpected input.");
        }
    }

    private static HeartbeatSkillPolicy.Candidate parseCandidate(
            Map<String, Object> light,
            int index) {
        String id = requiredString(light, "id");
        String label = requiredString(light, "label");
        String provenanceKind = requiredString(light, "provenanceKind");
        String provenanceLocator = requiredString(light, "provenanceLocator");
        String activationReason = requiredString(light, "activationReason");
        HeartbeatSkillPolicy.State state = parseState(requiredString(light, "state"), index);
        boolean changedThisPulse = requiredBoolean(light, "changedThisPulse");
        String consequence = requiredString(light, "consequence");
        String evidenceBoundary = requiredString(light, "evidenceBoundary");

        if ((state == HeartbeatSkillPolicy.State.ACTIVE
                || state == HeartbeatSkillPolicy.State.RECOVERED)
                && !changedThisPulse) {
            throw new ParseFailure(
                    "Light " + index + " state " + state.name().toLowerCase(Locale.ROOT)
                            + " requires changedThisPulse=true.");
        }

        HeartbeatSkillPolicy.Candidate candidate = new HeartbeatSkillPolicy.Candidate(
                id,
                label,
                provenanceKind,
                provenanceLocator,
                activationReason,
                state,
                changedThisPulse,
                consequence,
                evidenceBoundary);
        if (!HeartbeatSkillPolicy.hasTypedSourceContract(candidate)) {
            throw new ParseFailure("Light " + index + " lacks the complete typed source contract.");
        }
        return candidate;
    }

    private static HeartbeatSkillPolicy.State parseState(String raw, int index) {
        switch (raw.toLowerCase(Locale.ROOT)) {
            case "active":
                return HeartbeatSkillPolicy.State.ACTIVE;
            case "blocked":
                return HeartbeatSkillPolicy.State.BLOCKED;
            case "fault":
                return HeartbeatSkillPolicy.State.FAULT;
            case "recovered":
                return HeartbeatSkillPolicy.State.RECOVERED;
            default:
                throw new ParseFailure("Light " + index + " has unsupported state: " + raw);
        }
    }

    private static String requiredString(Map<String, Object> object, String key) {
        Object value = object.get(key);
        if (!(value instanceof String)) {
            throw new ParseFailure("Heartbeat field " + key + " must be a string.");
        }
        String clean = clean((String) value);
        if (clean.isEmpty()) {
            throw new ParseFailure("Heartbeat field " + key + " must not be empty.");
        }
        return clean;
    }

    private static boolean requiredBoolean(Map<String, Object> object, String key) {
        Object value = object.get(key);
        if (!(value instanceof Boolean)) {
            throw new ParseFailure("Heartbeat field " + key + " must be a boolean.");
        }
        return (Boolean) value;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> asObject(Object value, String boundary) {
        if (!(value instanceof Map)) throw new ParseFailure(boundary);
        return (Map<String, Object>) value;
    }

    @SuppressWarnings("unchecked")
    private static List<Object> requiredArray(Map<String, Object> object, String key) {
        Object value = object.get(key);
        if (!(value instanceof List)) {
            throw new ParseFailure("Heartbeat field " + key + " must be an array.");
        }
        return (List<Object>) value;
    }

    private static Result reject(String boundary) {
        return new Result(null, boundary);
    }

    private static String clean(String value) {
        return value == null ? "" : value.trim();
    }

    private static final class ParseFailure extends RuntimeException {
        ParseFailure(String message) {
            super(message);
        }
    }

    /** Tiny strict JSON reader so the semantic path remains JVM-testable. */
    private static final class JsonCursor {
        private final String input;
        private int index;

        JsonCursor(String input) {
            this.input = input;
        }

        Object parseDocument() {
            skipWhitespace();
            Object value = parseValue(0);
            skipWhitespace();
            if (index != input.length()) {
                throw fail("Trailing data after JSON document.");
            }
            return value;
        }

        private Object parseValue(int depth) {
            if (depth > MAX_JSON_DEPTH) throw fail("JSON nesting exceeds limit.");
            skipWhitespace();
            if (index >= input.length()) throw fail("Unexpected end of JSON.");
            char c = input.charAt(index);
            switch (c) {
                case '{':
                    return parseObject(depth + 1);
                case '[':
                    return parseArray(depth + 1);
                case '"':
                    return parseString();
                case 't':
                    expectLiteral("true");
                    return Boolean.TRUE;
                case 'f':
                    expectLiteral("false");
                    return Boolean.FALSE;
                case 'n':
                    expectLiteral("null");
                    return null;
                default:
                    if (c == '-' || (c >= '0' && c <= '9')) return parseNumber();
                    throw fail("Unexpected JSON token.");
            }
        }

        private Map<String, Object> parseObject(int depth) {
            expect('{');
            skipWhitespace();
            Map<String, Object> out = new LinkedHashMap<>();
            if (peek('}')) {
                index++;
                return out;
            }
            while (true) {
                skipWhitespace();
                if (!peek('"')) throw fail("Object member name must be a string.");
                String key = parseString();
                if (out.containsKey(key)) throw fail("Duplicate JSON member: " + key);
                skipWhitespace();
                expect(':');
                out.put(key, parseValue(depth));
                skipWhitespace();
                if (peek('}')) {
                    index++;
                    return out;
                }
                expect(',');
            }
        }

        private List<Object> parseArray(int depth) {
            expect('[');
            skipWhitespace();
            List<Object> out = new ArrayList<>();
            if (peek(']')) {
                index++;
                return out;
            }
            while (true) {
                out.add(parseValue(depth));
                skipWhitespace();
                if (peek(']')) {
                    index++;
                    return out;
                }
                expect(',');
            }
        }

        private String parseString() {
            expect('"');
            StringBuilder out = new StringBuilder();
            while (index < input.length()) {
                char c = input.charAt(index++);
                if (c == '"') return out.toString();
                if (c < 0x20) throw fail("Unescaped control character in string.");
                if (c == '\\') {
                    if (index >= input.length()) throw fail("Unterminated string escape.");
                    char escaped = input.charAt(index++);
                    switch (escaped) {
                        case '"': out.append('"'); break;
                        case '\\': out.append('\\'); break;
                        case '/': out.append('/'); break;
                        case 'b': out.append('\b'); break;
                        case 'f': out.append('\f'); break;
                        case 'n': out.append('\n'); break;
                        case 'r': out.append('\r'); break;
                        case 't': out.append('\t'); break;
                        case 'u': out.append(parseUnicodeEscape()); break;
                        default: throw fail("Unsupported string escape.");
                    }
                } else {
                    out.append(c);
                }
                if (out.length() > MAX_STRING_CHARS) throw fail("JSON string exceeds limit.");
            }
            throw fail("Unterminated JSON string.");
        }

        private char parseUnicodeEscape() {
            if (index + 4 > input.length()) throw fail("Incomplete unicode escape.");
            int value = 0;
            for (int i = 0; i < 4; i++) {
                int digit = Character.digit(input.charAt(index++), 16);
                if (digit < 0) throw fail("Invalid unicode escape.");
                value = (value << 4) | digit;
            }
            return (char) value;
        }

        private BigDecimal parseNumber() {
            int start = index;
            if (peek('-')) index++;
            if (index >= input.length()) throw fail("Invalid JSON number.");
            if (peek('0')) {
                index++;
            } else {
                requireDigitOneToNine();
                while (index < input.length() && Character.isDigit(input.charAt(index))) index++;
            }
            if (peek('.')) {
                index++;
                requireDigit();
                while (index < input.length() && Character.isDigit(input.charAt(index))) index++;
            }
            if (peek('e') || peek('E')) {
                index++;
                if (peek('+') || peek('-')) index++;
                requireDigit();
                while (index < input.length() && Character.isDigit(input.charAt(index))) index++;
            }
            try {
                return new BigDecimal(input.substring(start, index));
            } catch (NumberFormatException badNumber) {
                throw fail("Invalid JSON number.");
            }
        }

        private void requireDigitOneToNine() {
            if (index >= input.length()) throw fail("Invalid JSON number.");
            char c = input.charAt(index);
            if (c < '1' || c > '9') throw fail("Invalid JSON number.");
            index++;
        }

        private void requireDigit() {
            if (index >= input.length() || !Character.isDigit(input.charAt(index))) {
                throw fail("Invalid JSON number.");
            }
        }

        private void expectLiteral(String literal) {
            if (!input.regionMatches(index, literal, 0, literal.length())) {
                throw fail("Invalid JSON literal.");
            }
            index += literal.length();
        }

        private void expect(char expected) {
            skipWhitespace();
            if (!peek(expected)) throw fail("Expected '" + expected + "'.");
            index++;
        }

        private boolean peek(char c) {
            return index < input.length() && input.charAt(index) == c;
        }

        private void skipWhitespace() {
            while (index < input.length()) {
                char c = input.charAt(index);
                if (c == ' ' || c == '\n' || c == '\r' || c == '\t') index++;
                else break;
            }
        }

        private ParseFailure fail(String message) {
            return new ParseFailure(message + " At character " + index + ".");
        }
    }
}
