package com.dclar.homecenter;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

final class ChatSystemShape {
    private static final int MAX_SUMMARY_CHARS = 4000;
    private static final int MAX_MANAGED_CONTEXT_CHARS = 1200;

    private ChatSystemShape() {
    }

    enum QuickActionType {
        PROMPT,
        SETTINGS,
        COMPACT
    }

    static final class TemplateBlock {
        final String label;
        final String body;

        TemplateBlock(String label, String body) {
            this.label = label;
            this.body = body;
        }
    }

    static final class QuickAction {
        final String label;
        final String prompt;
        final QuickActionType type;

        QuickAction(String label, String prompt, QuickActionType type) {
            this.label = label;
            this.prompt = prompt;
            this.type = type;
        }

        boolean isPrompt() {
            return type == QuickActionType.PROMPT;
        }

        boolean isSettings() {
            return type == QuickActionType.SETTINGS;
        }

        boolean isCompact() {
            return type == QuickActionType.COMPACT;
        }
    }

    static String startupGreeting(boolean restoredConversation) {
        return restoredConversation
                ? "Welcome back. I restored your last conversation. Try pantry inventory, what can I make, recipe brainstorm, or rescue meal."
                : "Home Center is ready. Try pantry inventory, what can I make, recipe brainstorm, or rescue meal.";
    }

    static List<QuickAction> defaultQuickActions() {
        List<QuickAction> actions = new ArrayList<>();
        actions.add(new QuickAction("Gemini key", "", QuickActionType.SETTINGS));
        actions.add(new QuickAction("Pantry + fridge", "Help me inventory what I have in the pantry and fridge.", QuickActionType.PROMPT));
        actions.add(new QuickAction("What can I make", "Given what I have, what meals can I make tonight?", QuickActionType.PROMPT));
        actions.add(new QuickAction("Brainstorm", "Give me a few meal ideas with easy ingredients.", QuickActionType.PROMPT));
        actions.add(new QuickAction("Rescue meal", "I need the easiest possible dinner using what I have.", QuickActionType.PROMPT));
        actions.add(new QuickAction("Compact chat", "", QuickActionType.COMPACT));
        return Collections.unmodifiableList(actions);
    }

    static List<TemplateBlock> defaultTemplateBlocks() {
        List<TemplateBlock> blocks = new ArrayList<>();
        blocks.add(new TemplateBlock(
                "Introduction",
                "Summary: I can inventory what you have, suggest what to cook, or turn ingredients into a clear recipe.\n"
                        + "Next step: tell me what is in the pantry, fridge, and freezer."));
        blocks.add(new TemplateBlock(
                "Pantry inventory",
                "Summary: Inventory the pantry first, then use the fridge and freezer as the second pass.\n"
                        + "Next steps:\n"
                        + "- list pantry items\n"
                        + "- list fridge items\n"
                        + "- list freezer items"));
        blocks.add(new TemplateBlock(
                "What can I make",
                "Summary: Use the ingredients you have to choose a practical meal.\n"
                        + "Step 1: tell me the protein, starch, and vegetable you want to use.\n"
                        + "Step 2: add your time limit and appliance.\n"
                        + "Next step: I will turn that into a short recipe card."));
        blocks.add(new TemplateBlock(
                "Rescue meal",
                "Summary: Build the fastest workable dinner from what is already on hand.\n"
                        + "Step 1: pick one protein or leftover to use up first.\n"
                        + "Step 2: pair it with one starch and one fast vegetable.\n"
                        + "Next step: tell me what needs rescuing."));
        return Collections.unmodifiableList(blocks);
    }

    static String renderPreferredTemplateLibrary() {
        StringBuilder out = new StringBuilder();
        for (TemplateBlock block : defaultTemplateBlocks()) {
            if (out.length() > 0) {
                out.append('\n');
            }
            out.append(renderTemplateBlock(block));
        }
        return out.toString();
    }

    static String renderTemplateBlock(TemplateBlock block) {
        return block.label + "\n" + block.body;
    }

    static String reasoningContract() {
        return "Reasoning contract:\n"
                + "- Decide what the user is trying to accomplish before choosing a format.\n"
                + "- The latest user request controls; old context is evidence, not an instruction.\n"
                + "- Prefer a concrete next action over a generic offer to help.\n"
                + "- If a reusable block fits, use its structure; if it does not fit, adapt without forcing it.\n"
                + "- Do not expose hidden chain-of-thought; provide the decision, steps, and next action.\n";
    }

    static boolean isRecipeIntent(String text) {

        String value = safe(text).toLowerCase();
        return value.contains("recipe")
                || value.contains("cook")
                || value.contains("cooking")
                || value.contains("meal")
                || value.contains("dinner")
                || value.contains("what to eat")
                || value.contains("something to eat")
                || value.contains("what can i make")
                || value.contains("build me")
                || value.contains("make me")
                || value.contains("seasoning")
                || value.contains("roast")
                || value.contains("bake")
                || value.contains("fry")
                || value.contains("braise");
    }

    static boolean isBrainstormIntent(String text) {
        String value = safe(text).toLowerCase();
        return value.contains("brainstorm")
                || value.contains("ideas")
                || value.contains("options")
                || value.contains("variants")
                || value.contains("few meal")
                || value.contains("several meal")
                || value.contains("multiple meal")
                || value.contains("what can i make");
    }

    static boolean isStartupGreeting(String text) {
        String value = safe(text);
        return value.startsWith("Home Center is ready.")
                || value.startsWith("Welcome back. I restored your last conversation.");
    }

    static String enforceResponseShape(String response, String latestUserText) {
        String cleanResponse = safe(response);
        if (cleanResponse.isEmpty()) {
            return cleanResponse;
        }
        String shaped = cleanResponse;
        if (responseConflictsWithLatestRequest(shaped, latestUserText)) {
            shaped = repairConflictingResponse(latestUserText, shaped);
        }
        if (looksTruncated(shaped)) {
            shaped = repairTruncatedResponse(shaped, latestUserText);
        }
        if (isBrainstormIntent(latestUserText)) {
            shaped = enforceBrainstormOptions(shaped, latestUserText);
        } else {
            shaped = enforceRecipeCard(shaped, latestUserText);
        }
        return enforceNextStep(shaped, latestUserText);
    }

    static String enforceNextStep(String response, String latestUserText) {
        String cleanResponse = safe(response);
        if (cleanResponse.isEmpty() || hasNextStep(cleanResponse) || hasNextSteps(cleanResponse)) {
            return cleanResponse;
        }
        if (isIntegrationStatusIntent(latestUserText) || isIntegrationStatusAnswer(cleanResponse)) {
            return cleanResponse;
        }
        if (!shouldForceNextStep(latestUserText, cleanResponse)) {
            return cleanResponse;
        }
        String followUp = suggestedNextSteps(latestUserText, cleanResponse);
        if (followUp.isEmpty()) {
            return cleanResponse;
        }
        return cleanResponse + "\n\n" + followUp;
    }

    static String localFallbackForFailedRequest(String latestUserText) {
        String user = safe(latestUserText).toLowerCase();
        if (isBrainstormIntent(user)) {
            return fallbackBrainstormOptions();
        }
        if (isRecipeIntent(user)) {
            return enforceNextStep("Summary: I can build a recipe once I know the main ingredient and cooking tool.\n"
                    + "Step 1: Name one protein, leftover, or vegetable you want to use first.\n"
                    + "Step 2: Add your fastest tool: air fryer, oven, microwave, skillet, or pot.", latestUserText);
        }
        if (user.contains("inventory") || user.contains("pantry") || user.contains("fridge")) {
            return renderTemplateBlock(defaultTemplateBlocks().get(1));
        }
        return enforceNextStep("I can keep going locally, but Gemini is unavailable right now.", latestUserText);
    }

    static String enforceRecipeCard(String response, String latestUserText) {
        String cleanResponse = safe(response);
        if (cleanResponse.isEmpty() || !isRecipeIntent(latestUserText) || hasStepOne(cleanResponse)) {
            return cleanResponse;
        }
        return cleanResponse + "\n\n" + fallbackRecipeSteps(latestUserText, cleanResponse);
    }

    static String enforceBrainstormOptions(String response, String latestUserText) {
        String cleanResponse = safe(response);
        if (cleanResponse.isEmpty() || !isBrainstormIntent(latestUserText) || hasMultipleMealIdeas(cleanResponse)) {
            return cleanResponse;
        }
        return fallbackBrainstormOptions();
    }

    static boolean looksTruncated(String response) {
        String cleanResponse = safe(response);
        if (cleanResponse.isEmpty()) {
            return false;
        }
        String value = cleanResponse.toLowerCase();
        if (value.endsWith(" and") || value.endsWith(" or") || value.endsWith(" for") || value.endsWith(" with")
                || value.endsWith(" to") || value.endsWith(" a") || value.endsWith(" the")) {
            return true;
        }
        char last = cleanResponse.charAt(cleanResponse.length() - 1);
        if (".!?):".indexOf(last) >= 0) {
            return false;
        }
        return cleanResponse.length() < 220 && !hasNextStep(cleanResponse) && !hasNextSteps(cleanResponse);
    }

    private static boolean responseConflictsWithLatestRequest(String response, String latestUserText) {
        String answer = safe(response).toLowerCase();
        String user = safe(latestUserText).toLowerCase();
        boolean latestIsCorrection = user.contains("actually") || user.contains("ignore") || user.contains("instead");
        boolean latestWantsFood = isRecipeIntent(user) || isBrainstormIntent(user) || user.contains("dinner") || user.contains("meal");
        boolean answerStaysOnOldCart = answer.contains("shopping cart") || answer.contains("walmart cart");
        return latestIsCorrection && latestWantsFood && answerStaysOnOldCart;
    }

    private static String repairConflictingResponse(String latestUserText, String response) {
        if (isBrainstormIntent(latestUserText)) {
            return fallbackBrainstormOptions();
        }
        if (isRecipeIntent(latestUserText)) {
            return "Summary: Simple dinner from the latest request.\n" + fallbackRecipeSteps(latestUserText, response);
        }
        return "Summary: Use the latest request as the active task.";
    }

    private static boolean hasNextStep(String text) {
        return safe(text).toLowerCase().contains("next step:");
    }

    private static boolean hasNextSteps(String text) {
        return safe(text).toLowerCase().contains("next steps:");
    }

    private static boolean hasStepOne(String text) {
        String value = safe(text).toLowerCase();
        return value.contains("step 1:") || value.contains("1.");
    }

    private static boolean isIntegrationStatusIntent(String text) {
        String value = safe(text).toLowerCase();
        boolean mentionsIntegration = value.contains("google")
                || value.contains("drive")
                || value.contains("docs")
                || value.contains("gmail")
                || value.contains("calendar")
                || value.contains("cartesia")
                || value.contains("speech")
                || value.contains("narration")
                || value.contains("connected")
                || value.contains("access");
        boolean asksStatus = value.contains("can you see")
                || value.contains("can home center see")
                || value.contains("can you read")
                || value.contains("can home center read")
                || value.contains("can you open")
                || value.contains("can home center open")
                || value.contains("can you access")
                || value.contains("can home center access")
                || value.contains("do you have access")
                || value.contains("does home center have access")
                || value.contains("permission")
                || value.contains("are you connected")
                || value.contains("is home center connected")
                || value.contains("is google connected")
                || value.contains("is drive connected")
                || value.contains("is docs connected")
                || value.contains("open drive")
                || value.contains("list contents")
                || value.contains("list files")
                || value.contains("read google")
                || value.contains("brain folder");
        return mentionsIntegration && asksStatus;
    }

    private static boolean isIntegrationStatusAnswer(String text) {
        String value = safe(text).toLowerCase();
        return value.contains("google drive is not connected")
                || value.contains("google docs is not connected")
                || value.contains("google tools are not connected")
                || value.contains("narration is unavailable")
                || value.contains("ask drew to connect google");
    }

    private static boolean shouldForceNextStep(String latestUserText, String response) {
        String user = safe(latestUserText).toLowerCase();
        String answer = safe(response);
        return isRecipeIntent(user)
                || isBrainstormIntent(user)
                || user.contains("inventory")
                || user.contains("pantry")
                || user.contains("fridge")
                || answer.contains("?");
    }

    private static String suggestedNextSteps(String latestUserText, String response) {
        String user = safe(latestUserText).toLowerCase();
        String answer = safe(response).toLowerCase();
        boolean plural = needsPluralFollowUp(user, answer);
        if (plural) {
            StringBuilder steps = new StringBuilder();
            steps.append("Next steps:\n");
            steps.append("- ").append(pluralFirstStep(user, answer)).append('\n');
            steps.append("- ").append(pluralSecondStep(user, answer));
            return steps.toString();
        }
        return "Next step: " + singularNextStep(user, answer);
    }

    private static boolean needsPluralFollowUp(String user, String answer) {
        return user.contains(" and ")
                || user.contains(",")
                || user.contains("options")
                || user.contains("ideas")
                || user.contains("variants")
                || user.contains("several")
                || user.contains("multiple")
                || user.contains("what can i make")
                || user.contains("brainstorm");
    }

    private static String pluralFirstStep(String user, String answer) {
        if (user.contains("brainstorm") || user.contains("ideas") || user.contains("options") || user.contains("variants") || user.contains("few meal")) {
            return "pick one idea and I will turn it into a tight Step 1 recipe.";
        }
        if (user.contains("recipe") || user.contains("cook") || user.contains("meal") || user.contains("dinner") || user.contains("rescue") || user.contains("what can i make")) {
            return "tell me the protein, starch, and time limit you want to use.";
        }
        if (user.contains("inventory") || user.contains("pantry") || user.contains("fridge")) {
            return "tell me what is in the pantry, fridge, and freezer.";
        }
        if (answer.contains("?")) {
            return "answer the question the app asked first.";
        }
        return "tell me the next concrete thing to do first.";
    }

    private static String pluralSecondStep(String user, String answer) {
        if (user.contains("brainstorm") || user.contains("ideas") || user.contains("options") || user.contains("variants") || user.contains("few meal")) {
            return "or tell me one ingredient you want to use up and I will rerank the options.";
        }
        if (user.contains("recipe") || user.contains("cook") || user.contains("meal") || user.contains("dinner") || user.contains("rescue") || user.contains("what can i make")) {
            return "tell me whether you want fast, crispy, saucy, or braised.";
        }
        if (user.contains("inventory") || user.contains("pantry") || user.contains("fridge")) {
            return "tell me the freezer items and any food that needs to be used first.";
        }
        if (answer.contains("?")) {
            return "tell me the missing detail the question is asking for.";
        }
        return "tell me the second concrete thing to do.";
    }

    private static String singularNextStep(String user, String answer) {
        if (user.contains("inventory") || user.contains("pantry") || user.contains("fridge")) {
            return "tell me what is in the pantry, fridge, and freezer.";
        }
        if (user.contains("recipe") || user.contains("cook") || user.contains("meal") || user.contains("dinner") || user.contains("rescue") || user.contains("what can i make")) {
            if (answer.contains("step 1") || answer.contains("summary:")) {
                return "start with Step 1 now.";
            }
            return "tell me the ingredients, tools, or time limit you want to cook with.";
        }
        if (user.contains("brainstorm") || user.contains("ideas")) {
            return "pick one idea and I will turn it into Step 1.";
        }
        if (user.contains("help") || user.contains("what should i")) {
            return "tell me the task or problem you want to work around.";
        }
        if (answer.contains("?")) {
            return "answer that question or tell me the missing detail.";
        }
        return "tell me the next thing you want me to do.";
    }

    private static String fallbackRecipeSteps(String latestUserText, String response) {
        String user = safe(latestUserText).toLowerCase();
        String answer = safe(response).toLowerCase();
        if (user.contains("egg") || answer.contains("egg")) {
            return "Step 1: Heat a skillet over medium and butter or oil the pan.\n"
                    + "Step 2: Toast the bread while the egg cooks; fry the egg 2 to 3 minutes until the white is set.\n"
                    + "Step 3: Season with salt and pepper, assemble hot, and eat now.";
        }
        if (user.contains("toast") || user.contains("bread") || user.contains("butter")
                || answer.contains("toast") || answer.contains("bread") || answer.contains("butter")) {
            return "Step 1: Toast the bread until crisp and hot.\n"
                    + "Step 2: Butter it immediately so the butter melts into the toast.\n"
                    + "Step 3: Add salt, cinnamon sugar, jam, or an egg if you want it to become a meal.";
        }
        return "Step 1: Put the main pan or appliance on heat now.\n"
                + "Step 2: Season the main ingredient, then cook until browned or hot through.\n"
                + "Step 3: Add the fastest side last and serve when the main item is done.";
    }

    private static String repairTruncatedResponse(String response, String latestUserText) {
        if (isBrainstormIntent(latestUserText)) {
            return fallbackBrainstormOptions();
        }
        if (isRecipeIntent(latestUserText)) {
            return response + "\n\n" + fallbackRecipeSteps(latestUserText, response);
        }
        return response + "\n\nResponse note: the model reply looked cut off, so treat this as incomplete.";
    }

    private static boolean hasMultipleMealIdeas(String response) {
        String value = safe(response).toLowerCase();
        int numbered = 0;
        for (String marker : new String[]{"1.", "2.", "3.", "idea 1", "idea 2", "option 1", "option 2"}) {
            if (value.contains(marker)) {
                numbered++;
            }
        }
        int bullets = countOccurrences(value, "\n- ") + countOccurrences(value, "\n* ");
        return numbered >= 2 || bullets >= 2 || value.contains("three") && value.contains("ideas");
    }

    private static int countOccurrences(String value, String needle) {
        int count = 0;
        int offset = 0;
        while (true) {
            int found = value.indexOf(needle, offset);
            if (found < 0) {
                return count;
            }
            count++;
            offset = found + needle.length();
        }
    }

    private static String fallbackBrainstormOptions() {
        return "Here are three easy meal ideas:\n"
                + "1. Crispy chicken, potatoes, and broccoli: parboil potatoes 10 minutes, air fry at 400 F until crisp, microwave frozen broccoli, and sear or air fry seasoned chicken to 165 F.\n"
                + "2. Saucy skillet bowl: brown the protein, add a quick sauce or bouillon-backed gravy, fold in potatoes or rice, and finish broccoli in the microwave while the pan reduces.\n"
                + "3. Sheet-pan or air-fryer dinner: roast the starch first, add seasoned protein second, then add the vegetable last so everything lands hot together.\n\n"
                + "Next steps:\n"
                + "- pick one idea and I will turn it into Step 1.\n"
                + "- or tell me one ingredient you want to use up and I will rerank the options.";
    }

    static String managedTranscriptFor(String latestUserText, String transcript) {
        String cleanTranscript = safe(transcript);
        if (cleanTranscript.isEmpty()) {
            return "";
        }
        if (!dependsOnPriorContext(latestUserText)) {
            return durableUserContext(cleanTranscript);
        }
        return trimTo(cleanTranscript, MAX_MANAGED_CONTEXT_CHARS);
    }

    private static boolean dependsOnPriorContext(String latestUserText) {
        String user = safe(latestUserText).toLowerCase();
        return user.contains("that")
                || user.contains("those")
                || user.contains("same")
                || user.contains("earlier")
                || user.contains("what i have")
                || user.contains("given what i have")
                || user.contains("using what i have")
                || user.contains("from before");
    }

    private static String durableUserContext(String transcript) {
        String[] lines = transcript.split("\\n");
        StringBuilder out = new StringBuilder();
        for (String line : lines) {
            String cleanLine = line.trim();
            String lower = cleanLine.toLowerCase();
            if (!lower.startsWith("user:")) {
                continue;
            }
            if (lower.contains("i have")
                    || lower.contains("pantry")
                    || lower.contains("fridge")
                    || lower.contains("freezer")
                    || lower.contains("allergic")
                    || lower.contains("avoid")
                    || lower.contains("air fryer")
                    || lower.contains("oven")
                    || lower.contains("microwave")
                    || lower.contains("cast iron")) {
                out.append(cleanLine).append('\n');
            }
        }
        return trimTo(out.toString().trim(), MAX_MANAGED_CONTEXT_CHARS);
    }

    static String buildMainPrompt(String conversationSummary, String transcript) {
        return buildMainPrompt("", conversationSummary, transcript);
    }

    static String buildMainPrompt(String latestUserText, String conversationSummary, String transcript) {
        StringBuilder prompt = new StringBuilder();
        prompt.append("You are Home Center, a proactive kitchen and household assistant for low-motivation users.\n");
        prompt.append("Your job is to take initiative, advertise useful skills, and reduce user effort.\n");
        prompt.append(reasoningContract());
        prompt.append("The latest user request controls. Do not get stuck on earlier topics or reuse old examples unless the latest request still needs them.\n");
        prompt.append("Skills to push when relevant: pantry and fridge inventory, what can I make, recipe brainstorm, rescue meals, timing and sequencing, reuse of pans and utensils, and kitchen orchestration.\n");
        prompt.append("If the user asks for a recipe, answer as a recipe card: a tight one-line summary, then Step 1 immediately, then compact cooking instructions with seasoning, method, timing, temperatures, and doneness temperature.\n");
        prompt.append("Do not recap known ingredients or restate the ask unless it changes the cooking choice.\n");
        prompt.append("Do not start with a summary paragraph before cooking instructions.\n");
        prompt.append("When the user lists ingredients, return two to four distinct meal variants when possible, not just one dish.\n");
        prompt.append("Prefer explicit orchestration: one active hot task, parallel prep when possible, and a clear order of operations.\n");
        prompt.append("Use the air fryer for small-batch speed, the oven for volume or broil/convection/high heat, and the microwave as a parallel tool for frozen vegetables or quick heating.\n");
        prompt.append("Recommend parboiling potatoes before roasting, baking, or frying when it will improve speed or texture.\n");
        prompt.append("Use braising for tough or cheap proteins when tenderness and sauce matter more than crispness.\n");
        prompt.append("Reply concisely and concretely. Keep the tone direct. If the user asks about cooking, prioritize timing, safety, sequencing, and clear next steps.\n");
        prompt.append("Always end with a Next step or Next steps block. Use the literal labels Next step: or Next steps: when you answer. Use the plural form when the user request is multi-part or asks for options, variants, or brainstormed choices.\n");
        prompt.append("Preferred reusable blocks. Reuse these exact structures when they fit the request instead of inventing a new format:\n");
        prompt.append(renderPreferredTemplateLibrary()).append('\n');
        String latest = safe(latestUserText);
        if (!latest.isEmpty()) {
            prompt.append("Latest user request:\n");
            prompt.append(latest).append('\n');
            prompt.append("Treat the latest user request as the controlling instruction.\n");
        }
        String summary = safe(conversationSummary);
        if (!summary.isEmpty()) {
            prompt.append("Conversation summary: ").append(trimTo(summary, MAX_SUMMARY_CHARS)).append('\n');
        }
        String managedTranscript = managedTranscriptFor(latestUserText, transcript);
        if (!managedTranscript.isEmpty()) {
            prompt.append("Managed context, background only:\n");
            prompt.append(managedTranscript).append('\n');
        }
        prompt.append("Assistant:");
        return prompt.toString();
    }

    static String buildBrainstormPrompt(String latestUserText, String conversationSummary, String transcript) {
        StringBuilder prompt = new StringBuilder();
        prompt.append("You are Home Center. The user wants meal ideas, not one finished recipe and not a recap.\n");
        prompt.append(reasoningContract());
        prompt.append("The latest user request controls. Older food mentions are stale unless the latest request explicitly refers to them.\n");
        prompt.append("Return three distinct meal ideas using easy-to-get ingredients. Do not anchor on bread, butter, toast, or eggs unless the latest request names them.\n");
        prompt.append("Each idea should include: meal name, why it works, core method, and one orchestration note.\n");
        prompt.append("Preferred reusable blocks. Reuse these exact structures when they fit the request instead of inventing a new format:\n");
        prompt.append(renderPreferredTemplateLibrary()).append('\n');
        prompt.append("Prefer practical Home Center techniques: parboil potatoes when useful, air fryer for speed, microwave frozen vegetables in parallel, oven for volume, cast iron for hard sear, braise when tenderness matters.\n");
        prompt.append("Keep each idea compact. Do not ask for protein, starch, or time unless the user requested a bounded brainstorm and omitted the bound.\n");
        prompt.append("Always end with Next steps: and give two action choices: pick an idea for Step 1, or provide one ingredient to rerank around.\n");
        String latest = safe(latestUserText);
        if (!latest.isEmpty()) {
            prompt.append("Latest user request:\n");
            prompt.append(latest).append('\n');
        }
        String summary = safe(conversationSummary);
        if (!summary.isEmpty()) {
            prompt.append("Durable context summary, background only:\n");
            prompt.append(trimTo(summary, MAX_SUMMARY_CHARS)).append('\n');
        }
        String managedTranscript = managedTranscriptFor(latestUserText, transcript);
        if (!managedTranscript.isEmpty()) {
            prompt.append("Managed context, background only:\n");
            prompt.append(managedTranscript).append('\n');
        }
        prompt.append("Assistant:");
        return prompt.toString();
    }

    static String buildRecipePrompt(String conversationSummary, String transcript) {
        return buildRecipePrompt("", conversationSummary, transcript);
    }

    static String buildRecipePrompt(String latestUserText, String conversationSummary, String transcript) {
        StringBuilder prompt = new StringBuilder();
        prompt.append("You are Home Center. The user wants a recipe, not a recap.\n");
        prompt.append(reasoningContract());
        prompt.append("The latest user request controls. Do not get stuck on earlier topics or keep talking about old food if the latest request changed.\n");
        prompt.append("Old ingredients are background only. Ignore them unless the latest request names them or depends on them.\n");
        prompt.append("Format the answer as a compact recipe card:\n");
        prompt.append("Summary: one short line.\n");
        prompt.append("Step 1: immediate first action.\n");
        prompt.append("Step 2: next action.\n");
        prompt.append("Then continue with only the steps needed.\n");
        prompt.append("Preferred reusable blocks. Reuse these exact structures when they fit the request instead of inventing a new format:\n");
        prompt.append(renderPreferredTemplateLibrary()).append('\n');
        prompt.append("Keep it tight: one recipe, no long preface, no alternate plans unless the user asked.\n");
        prompt.append("Include seasoning, method, efficient sequencing, explicit cooking instructions, timing, temperatures, and a recommended doneness temperature when relevant.\n");
        prompt.append("Assume the user knows ordinary kitchen basics unless the detail changes the cook.\n");
        prompt.append("Do not restate ingredients unless a missing detail changes the cook.\n");
        prompt.append("Do not summarize the request before answering.\n");
        prompt.append("If there is a useful outlier technique like braising, call it out briefly.\n");
        prompt.append("Prefer a compact recipe card around 5 steps or fewer unless the method truly needs more.\n");
        prompt.append("If the answer would get long, trim explanation before trimming the actual cooking steps.\n");
        prompt.append("Always end with a Next step or Next steps block using the literal labels Next step: or Next steps:. If the recipe is complete, the follow-up should tell the user to start with Step 1 now. If the recipe still needs information, the follow-up should ask for the missing ingredient, tool, or time limit.\n");
        String latest = safe(latestUserText);
        if (!latest.isEmpty()) {
            prompt.append("Latest user request:\n");
            prompt.append(latest).append('\n');
            prompt.append("Treat the latest user request as the controlling instruction.\n");
        }
        String summary = safe(conversationSummary);
        if (!summary.isEmpty()) {
            prompt.append("Known context summary: ").append(trimTo(summary, MAX_SUMMARY_CHARS)).append('\n');
        }
        String managedTranscript = managedTranscriptFor(latestUserText, transcript);
        if (!managedTranscript.isEmpty()) {
            prompt.append("Managed context, background only:\n");
            prompt.append(managedTranscript).append('\n');
        }
        prompt.append("Assistant:");
        return prompt.toString();
    }

    static String buildCompactionPrompt(String conversationSummary, String transcript) {
        StringBuilder prompt = new StringBuilder();
        prompt.append("Summarize this Home Center conversation for later restoration and debugging.\n");
        prompt.append("Capture the user's goals, ingredients, tools, constraints, meal ideas, and next best actions.\n");
        prompt.append("Return 4 to 8 terse bullet points. No filler. No preamble.\n");
        String summary = safe(conversationSummary);
        if (!summary.isEmpty()) {
            prompt.append("Existing summary to preserve:\n");
            prompt.append(trimTo(summary, MAX_SUMMARY_CHARS)).append('\n');
        }
        prompt.append("Conversation:\n");
        prompt.append(trimTo(safe(transcript), MAX_SUMMARY_CHARS));
        return prompt.toString();
    }

    static String summarizeLocally(String conversationSummary, String transcript) {
        String summary = safe(conversationSummary);
        String turns = safe(transcript);
        if (summary.isEmpty() && turns.isEmpty()) {
            return "";
        }
        StringBuilder out = new StringBuilder();
        if (!summary.isEmpty()) {
            out.append("- Existing summary: ").append(trimTo(summary, MAX_SUMMARY_CHARS)).append('\n');
        }
        if (!turns.isEmpty()) {
            String[] lines = turns.split("\\n");
            int count = 0;
            for (int i = Math.max(0, lines.length - 4); i < lines.length; i++) {
                String line = lines[i].trim();
                if (line.isEmpty()) {
                    continue;
                }
                out.append("- ").append(line).append('\n');
                count++;
            }
            if (count == 0) {
                out.append("- Recent conversation available in chat history.");
            }
        }
        return trimTo(out.toString().trim(), MAX_SUMMARY_CHARS);
    }

    private static String safe(String value) {
        return value == null ? "" : value.trim();
    }

    private static String trimTo(String value, int maxChars) {
        if (value == null) {
            return "";
        }
        String trimmed = value.trim();
        if (trimmed.length() <= maxChars) {
            return trimmed;
        }
        return trimmed.substring(trimmed.length() - maxChars);
    }
}
