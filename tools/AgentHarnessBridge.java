package com.dclar.homecenter;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public final class AgentHarnessBridge {
    private AgentHarnessBridge() {
    }

    public static void main(String[] args) throws Exception {
        if (args.length < 1) {
            throw new IllegalArgumentException("usage: AgentHarnessBridge <command> ...");
        }
        String command = args[0];
        if ("shape".equals(command)) {
            requireArgs(args, 3);
            System.out.print(ChatSystemShape.enforceResponseShape(read(args[1]), read(args[2])));
            return;
        }
        if ("prompt".equals(command)) {
            requireArgs(args, 5);
            String mode = args[1];
            String latest = read(args[2]);
            String summary = read(args[3]);
            String transcript = read(args[4]);
            if ("brainstorm".equals(mode)) {
                System.out.print(ChatSystemShape.buildBrainstormPrompt(latest, summary, transcript));
                return;
            }
            if ("recipe".equals(mode)) {
                System.out.print(ChatSystemShape.buildRecipePrompt(latest, summary, transcript));
                return;
            }
            System.out.print(ChatSystemShape.buildMainPrompt(latest, summary, transcript));
            return;
        }
        if ("managed".equals(command)) {
            requireArgs(args, 3);
            System.out.print(ChatSystemShape.managedTranscriptFor(read(args[1]), read(args[2])));
            return;
        }
        if ("fallback".equals(command)) {
            requireArgs(args, 2);
            System.out.print(ChatSystemShape.localFallbackForFailedRequest(read(args[1])));
            return;
        }
        throw new IllegalArgumentException("unknown command: " + command);
    }

    private static String read(String path) throws Exception {
        return new String(Files.readAllBytes(Paths.get(path)), StandardCharsets.UTF_8);
    }

    private static void requireArgs(String[] args, int count) {
        if (args.length != count) {
            throw new IllegalArgumentException("expected " + count + " args, got " + args.length);
        }
    }
}
