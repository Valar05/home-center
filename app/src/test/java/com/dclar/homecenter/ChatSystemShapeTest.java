package com.dclar.homecenter;

import org.junit.Test;

import java.util.List;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public class ChatSystemShapeTest {
    @Test
    public void defaultQuickActionsDescribeTheChatSurface() {
        List<ChatSystemShape.QuickAction> actions = ChatSystemShape.defaultQuickActions();

        assertEquals(6, actions.size());
        assertEquals("Gemini key", actions.get(0).label);
        assertTrue(actions.get(0).isSettings());
        assertEquals("Pantry + fridge", actions.get(1).label);
        assertTrue(actions.get(1).isPrompt());
        assertEquals("What can I make", actions.get(2).label);
        assertEquals("Brainstorm", actions.get(3).label);
        assertEquals("Rescue meal", actions.get(4).label);
        assertEquals("Compact chat", actions.get(5).label);
        assertTrue(actions.get(5).isCompact());
    }

    @Test
    public void mainPromptPushesKitchenOrchestrationAndVariants() {
        String prompt = ChatSystemShape.buildMainPrompt(
                "make butter toast",
                "User wants dinner with chicken and potatoes.",
                "User: I have chicken and potatoes.\nAssistant: Try roasting.\n");

        assertTrue(prompt.contains("proactive kitchen and household assistant"));
        assertTrue(prompt.contains("two to four distinct meal variants"));
        assertTrue(prompt.contains("air fryer"));
        assertTrue(prompt.contains("parboiling potatoes"));
        assertTrue(prompt.contains("braising"));
        assertTrue(prompt.contains("Do not recap known ingredients"));
        assertTrue(prompt.contains("Conversation summary: User wants dinner with chicken and potatoes."));
        assertTrue(prompt.contains("Latest user request:"));
        assertTrue(prompt.contains("make butter toast"));
        assertTrue(prompt.contains("The latest user request controls"));
        assertTrue(prompt.contains("User: I have chicken and potatoes."));
        assertTrue(prompt.endsWith("Assistant:"));
    }

    @Test
    public void recipePromptDemandsTightSummaryAndStepOne() {
        String prompt = ChatSystemShape.buildRecipePrompt(
                "butter toast",
                "Need a quick chicken dinner.",
                "User: chicken\nAssistant: roast it\n");

        assertTrue(prompt.contains("The user wants a recipe, not a recap"));
        assertTrue(prompt.contains("Format the answer as a compact recipe card"));
        assertTrue(prompt.contains("Summary: one short line."));
        assertTrue(prompt.contains("Step 1: immediate first action."));
        assertTrue(prompt.contains("Step 2: next action."));
        assertTrue(prompt.contains("Keep it tight: one recipe, no long preface"));
        assertTrue(prompt.contains("seasoning, method, efficient sequencing"));
        assertTrue(prompt.contains("temperatures"));
        assertTrue(prompt.contains("doneness temperature"));
        assertTrue(prompt.contains("Prefer a compact recipe card around 5 steps or fewer"));
        assertTrue(prompt.contains("Do not restate ingredients"));
        assertTrue(prompt.contains("Do not summarize the request"));
        assertTrue(prompt.contains("Known context summary:"));
        assertTrue(prompt.contains("Latest user request:"));
        assertTrue(prompt.contains("The latest user request controls"));
        assertTrue(prompt.contains("Always end with a Next step or Next steps block"));
    }

    @Test
    public void recipePromptShouldBeARecipeCardNotAConversationSummary() {
        String prompt = ChatSystemShape.buildRecipePrompt(
                "butter toast",
                "Need a quick chicken dinner.",
                "User: chicken\nAssistant: roast it\n");

        assertTrue(prompt.contains("Summary:"));
        assertTrue(prompt.contains("Step 1:"));
        assertTrue(prompt.contains("Step 2:"));
        assertFalse(prompt.contains("Conversation summary:"));
        assertFalse(prompt.contains("Conversation so far:"));
        assertTrue(prompt.contains("Next step:") || prompt.contains("Next steps:"));
    }

    @Test
    public void enforceNextStepAppendsAConcreteFollowUp() {
        String response = ChatSystemShape.enforceNextStep(
                "Roast the potatoes at 425 F for 30 minutes.",
                "I want to cook potatoes.");

        assertTrue(response.contains("Next step:"));
    }

    @Test
    public void enforceNextStepDoesNotAppendIngredientPromptsToGeneralAnswers() {
        String response = ChatSystemShape.enforceNextStep(
                "I checked June's Holocron. The latest cycle was June 4-10, 2026, and the next estimate is around July 2, 2026.",
                "okay check out James holocron and tell me when my period should start");

        assertFalse(response.contains("main ingredient"));
        assertFalse(response.contains("second constraint"));
        assertFalse(response.contains("Next steps:"));
    }

    @Test
    public void enforceNextStepUsesPluralForMultiPartRequests() {
        String response = ChatSystemShape.enforceNextStep(
                "Here are three dinner ideas.",
                "I have chicken and potatoes and broccoli.");

        assertTrue(response.contains("Next steps:"));
        assertTrue(response.contains("- "));
    }

    @Test
    public void enforceRecipeCardRepairsTitleAndSummaryOnlyResponses() {
        String response = ChatSystemShape.enforceRecipeCard(
                "**Fried Egg Sandwich**\n\nSummary: A quick sandwich with a runny yolk.",
                "make me an egg sandwich");

        assertTrue(response.contains("Step 1:"));
        assertTrue(response.contains("Step 2:"));
    }

    @Test
    public void recipePromptMarksOldIngredientsAsBackgroundOnly() {
        String prompt = ChatSystemShape.buildRecipePrompt(
                "what can I make tonight?",
                "Earlier the user mentioned bread and butter.",
                "User: butter toast\nAssistant: Make toast.\n");

        assertTrue(prompt.contains("Old ingredients are background only"));
        assertTrue(prompt.contains("Latest user request:"));
        assertTrue(prompt.contains("what can I make tonight?"));
    }


    @Test
    public void latestRequestOverridesStaleFoodContext() {
        String transcript = "User: I have bread and butter.\nAssistant: Make butter toast.\n";
        String prompt = ChatSystemShape.buildBrainstormPrompt(
                "Give me a few meal ideas with easy ingredients.",
                "Earlier the user discussed butter toast.",
                transcript);

        assertTrue(prompt.contains("Do not anchor on bread, butter, toast, or eggs"));
        assertTrue(prompt.contains("Latest user request:"));
        assertTrue(prompt.contains("Give me a few meal ideas with easy ingredients."));
        assertFalse(prompt.contains("Assistant: Make butter toast."));
    }

    @Test
    public void brainstormDoesNotInheritFullTranscript() {
        String transcript = "User: I have bread and butter.\n"
                + "Assistant: Butterbrot is good.\n"
                + "User: I like cast iron.\n"
                + "Assistant: Use it for toast.\n";
        String managed = ChatSystemShape.managedTranscriptFor(
                "Give me a few meal ideas with easy ingredients.",
                transcript);

        assertTrue(managed.contains("User: I have bread and butter."));
        assertTrue(managed.contains("User: I like cast iron."));
        assertFalse(managed.contains("Assistant: Butterbrot is good."));
        assertFalse(managed.contains("Assistant: Use it for toast."));
    }

    @Test
    public void pluralBrainstormReturnsMultipleIdeas() {
        String response = ChatSystemShape.enforceResponseShape(
                "**Fried Egg Sandwich**\n\nSummary: A quick, satisfying sandwich.",
                "Give me a few meal ideas with easy ingredients.");

        assertTrue(response.contains("Here are three easy meal ideas:"));
        assertTrue(response.contains("1."));
        assertTrue(response.contains("2."));
        assertTrue(response.contains("3."));
        assertTrue(response.contains("Next steps:"));
        assertFalse(response.contains("tell me the protein, starch, and time limit"));
    }

    @Test
    public void truncatedModelResponseIsDetectedOrRepaired() {
        String response = ChatSystemShape.enforceResponseShape(
                "Here's a comforting classic: a crispy, gooey grilled cheese sandwich, perfect for a",
                "Give me a few meal ideas with easy ingredients.");

        assertTrue(ChatSystemShape.looksTruncated("Here's a comforting classic: perfect for a"));
        assertTrue(response.contains("Here are three easy meal ideas:"));
        assertTrue(response.contains("Next steps:"));
    }

    @Test
    public void genericFallbackDoesNotAskAlreadyAnsweredQuestionsForUnboundedBrainstorm() {
        String response = ChatSystemShape.enforceNextStep(
                "1. Skillet rice bowl.\n2. Air fryer potatoes.\n3. Soup upgrade.",
                "Give me a few meal ideas with easy ingredients.");

        assertTrue(response.contains("Next steps:"));
        assertTrue(response.contains("pick one idea"));
        assertFalse(response.contains("tell me the protein, starch, and time limit"));
    }

    @Test
    public void recipeIntentDetectsCookingRequests() {
        assertTrue(ChatSystemShape.isRecipeIntent("build me a chicken dinner"));
        assertTrue(ChatSystemShape.isRecipeIntent("what can I make with potatoes"));
        assertFalse(ChatSystemShape.isRecipeIntent("remind me about my bucket code"));
    }

    @Test
    public void compactionPromptPreservesSummaryAndTranscript() {
        String prompt = ChatSystemShape.buildCompactionPrompt(
                "Need a quick chicken dinner.",
                "User: chicken\nAssistant: roast it\n");
        String summary = ChatSystemShape.summarizeLocally(
                "Need a quick chicken dinner.",
                "User: chicken\nAssistant: roast it\n");

        assertTrue(prompt.contains("Summarize this Home Center conversation"));
        assertTrue(prompt.contains("Existing summary to preserve:"));
        assertTrue(prompt.contains("Need a quick chicken dinner."));
        assertTrue(prompt.contains("User: chicken"));
        assertTrue(summary.startsWith("- Existing summary:"));
        assertTrue(summary.contains("User: chicken"));
        assertFalse(summary.isEmpty());
    }

    @Test
    public void startupGreetingSwitchesForRestoredSessions() {
        assertTrue(ChatSystemShape.startupGreeting(true).contains("Welcome back"));
        assertTrue(ChatSystemShape.startupGreeting(false).contains("Home Center is ready"));
        assertTrue(ChatSystemShape.isStartupGreeting("Home Center is ready. Try pantry inventory, what can I make, recipe brainstorm, or rescue meal."));
        assertTrue(ChatSystemShape.isStartupGreeting("Welcome back. I restored your last conversation. Try pantry inventory, what can I make, recipe brainstorm, or rescue meal."));
    }
}
