# Netrunner Vision

Netrunner is a browser for people who need the web narrated, magnified, simplified, guided, and eventually driven.

It is not primarily an ecommerce assistant. It is an accessibility and task-learning layer over hostile websites.

## Target users

- Blind and low-vision users.
- Users with limited mobility or fine motor control.
- Users with executive-function friction.
- Users who are tired, overloaded, distracted, intoxicated, or otherwise not at full mission-control capacity.
- Household assistants using Home Center to complete routine web tasks safely.

## Product thesis

Every successful web task should leave behind a reusable map.

The user may begin by doing the task manually. Netrunner records what happened, redacts sensitive data, asks whether the task succeeded, and converts the episode into candidate knowledge.

Over time, Home Center accumulates a practical map of how websites actually work.

## First wedge

Accessible-first browser reader:

- Open a page.
- Read the current page aloud.
- Read the focused element aloud.
- Magnify and spotlight the focused region.
- Let the user ask what is on the page and what actions are available.
- Record the session as a redacted episode.

## Training wheels MVP

The first useful version should not drive the whole browser. It should watch the user drive.

Netrunner records:

- Intent.
- Visible DOM landmarks.
- Accessibility tree hints.
- Focused element.
- Clicked element.
- Typed fields, with sensitive values redacted.
- Page transitions.
- User corrections.
- Outcome: success, failure, abandoned, blocked.

## Element Command Mode

Long-press any visible element to open a command menu. The user should see friendly labels, not CSS goblin runes.

Examples:

- Hide this annoyance -> apply `display: none` or equivalent user stylesheet rule.
- Make this bigger -> boost font size or zoom selected region.
- Read this -> send selected element text to voice engine.
- Keep this visible -> pin element or extract it into the side panel.
- Explain this -> summarize the selected element and nearby context.
- Ignore things like this -> create a candidate rule for similar elements on the site.
- Undo last page change -> revert the last user-applied DOM/style override.

This is especially important for modal walls, cookie banners, newsletter popups, sticky ads, chat bubbles, and hostile overlays.

## Success definition

A user can open a hostile web page, understand it, remove visual noise, complete a simple task manually, and leave behind a reusable episode for future guidance.
