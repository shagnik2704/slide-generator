# Business Requirements

## 2.1 Clarity of explanation
- **No Vague Statements**: Refrain from using vague statements like "go here", "click this".
- **Clear Instructions**: Use clear statements like "go to the top left hand corner", "click file and then new".
- **Explain Every Action**: Explain EVERY action: mouse clicks, releasing the mouse, etc. (e.g., "Click the mouse at 2:15").
- **Pre-requisites**: If skipping explanation, ensure it is covered in pre-requisite tutorials.
- **Exact Menu Names**: Write menu items, dialog boxes, tabs, toolbars EXACTLY as they appear.
- **Menu Paths**: List menu paths in the order of clicking/selecting (e.g., "Select **File** from the **Main** menu").
- **Active Voice**: Maximise the use of active voice.

## 2.2 Intentional mistakes
- **Show Mistakes**: Show common mistakes and how to recover from them.
- **Deliberate Errors**: Demonstrate things that don't work through deliberate mistakes to reinforce learning.

## 2.3 KISS: Keep it Simple, Stupid
- **Short Sentences**: Keep most sentences under 60 characters. All sentences MUST be under 80 characters.
- **Simple Language**: Refrain from using complex words and sentences.
- **No Jargon**: Avoid jargon that only experts understand.
- **Telephone Test**: Script should be understandable just by hearing (without seeing).

## 2.4 Timing
- **Duration**: The script should take about 6 to 8 minutes to read aloud (resulting in a ~10 min tutorial).

## 2.5 Grammar
- **Spell Check**: Ensure no wrong spellings (e.g., mail vs male).
- **Grammar Check**: Ensure correct grammar.

## 2.6 Appearance on the wiki page (Script Format)
- **Two Column Format**: First column "Visual Cue", Second column "Narration".
- **Visual Cue Title**: First column must be titled "Visual Cue".
- **New Line**: Every sentence of the script must start on a new line.
- **Visual Cues**: Write visual cues for EVERY activity.
- **New Row**: Script for every new activity must start on a new row.
- **Key Phrases**: Include "video tutorial" as a key phrase.
- **Bold Key Phrases**: Key phrases explained in the guideline must be in **bold face**.

# Slide Requirements

## 3.1 Templates
- **Beamer**: Use LaTeX Beamer.
- **Un-maximised View**: Slides must be readable in un-maximised windows.
- **Consistency**: Use the same template/color for the entire series.
- **Logo**: Include `logo.png` as a watermark on every slide (bottom right).

## 3.2 Font
- **Size**: Use 17pt font size.

## 3.3 Content Display
- **Line Limit**: Maximum 7 lines per slide.
- **Bullet Points**: Maximise use of bullet points.
- **Animation**: Bullet points should appear one by one (slow through).
- **No 3rd Level**: Avoid 3rd level bullet points. Minimize 2nd level.

## 3.4 & 3.5 Common Slides & Arrangement
The slides MUST follow this exact order:
1.  **Opening Slide**: Title, Author, etc.
2.  **Learning Objectives**: What will be covered.
3.  **System Requirements**: OS, Software versions.
4.  **Pre-requisites**: If any.
5.  **Main Content**: The tutorial topics.
6.  **Summary**: Recap of what was covered.
7.  **Assignment**: A practice task.
8.  **Acknowledgement**: Credits.

## 3.6 Content Details
- **Recap**: Include recap of difficult/important concepts.
- **URLs**: Include relevant URLs.
- **Commands**: Show difficult commands/syntax.

## 3.8 Punctuation & URLs
- **URL Breaking**: Do not split URLs at dashes. Split at `/` and leave a space before the `/`.
- **Spacing**: No space before punctuation. One space after punctuation.

## 3.9 Slide Metadata
- **No Slide Numbers**: Do not show slide numbers.
- **Date**: Explicitly put the date on the screen (e.g., "23 February 2012"). Do not use `\date`.
- **Date Format**: Day Month Year (full words).
