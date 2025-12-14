# Course Outline Chat - Usage Guide

## Overview

The Course Outline Chat is an interactive chatbot that guides Subject Matter Experts (SMEs) through creating a Spoken Tutorial Course Outline. It follows a structured interview process to capture all required information and automatically enforces Spoken Tutorial pedagogy rules.

## How to Use

### 1. **Start the Chat**

1. Open the chatbot UI
2. Switch to **"Outline Chat"** mode (top right toggle)
3. The bot will greet you and ask the first question

### 2. **Conversation Flow**

The bot follows a structured 5-phase interview:

#### **Phase A: Warm-up & Context**
The bot asks for:
- **Tutorial Name**: What should we call this course?
- **Target Audience**: Who is this for? (e.g., school students, college beginners, lab technicians)
- **Entry Behaviour**: What should learners already know?
- **Purpose**: What will learners be able to do after completing the course?

#### **Phase B: Outcomes & Scope**
- **Course Objectives**: List 3-6 concrete things learners should be able to do
  - Tip: Phrase as actions (e.g., "Create a basic report", "Write and run a Python function")
- **Topics Included**: Which topics must be covered?
- **Topics Not Included**: What's out-of-scope?

#### **Phase C: Examples (Critical)**
- **Core Example**: A real file, dataset, scenario, or project for demonstrations
  - Examples: "student marksheet" for Excel, "bookstore DB" for SQL, "small image set" for image processing
  - ⚠️ **This is mandatory** - Spoken Tutorials teach via a running example
- **Allied Examples** (optional): 0-2 alternate scenarios for variations

#### **Phase D: Structure & Tutorial Breakdown**
- **Number of Tutorials**: How many short tutorials/modules? (recommended: 3-12)

For each tutorial, the bot will ask:
1. **Title**: Short title (e.g., "Importing data")
2. **Demonstrable Steps**: List 3-6 hands-on steps
   - ⚠️ Avoid menu-only instructions like "File → Open"
   - ✅ Instead: "Open the marksheet file from Desktop and show how to sort by marks"
3. **Time**: Estimated time in seconds (e.g., 300 for 5 minutes)
4. **Comments**: Any special notes (files to attach, assumptions, exercises)

#### **Phase E: Metadata**
- **Prepared By**: Your name
- **Date**: Preferred date (defaults to today)
- **Keywords**: 3-6 searchable keywords (comma-separated)

### 3. **Review & Edit**

Once all information is collected:
- The bot generates a **draft outline** with a pedagogy compliance badge
- Review the draft carefully
- Suggest edits in plain text (e.g., "Combine tutorial 2 and 3", "Remove step C from tutorial 1")
- The bot will apply your edits and regenerate the draft

### 4. **Approve & Export**

When satisfied:
- Type **"approve"** to finalize the outline
- The bot marks it as approved
- Export the outline using:
  ```
  GET /outline_chat/{project_id}/export?format=json
  ```

## API Usage

### Endpoint: `POST /outline_chat`

**Request Body:**
```json
{
  "conversation": [
    { "role": "user", "content": "Introduction to Python" },
    { "role": "assistant", "content": "Great! Who is the target audience?" }
  ],
  "outline_data": null,  // Auto-managed by backend
  "project_id": 1234567890,  // Optional, auto-generated if not provided
  "phase": "warmup"  // Optional, auto-managed
}
```

**Response:**
```json
{
  "project_id": 1234567890,
  "assistant_message": "Please give the tutorial name...",
  "follow_up_question": null,
  "phase": "warmup",
  "outline_data": {
    "tutorial_name": "Introduction to Python",
    "target_audience": "",
    // ... other fields
  },
  "validation_errors": [],
  "pedagogy_compliance": {
    "core_example": false,
    "demo_percentage": 0,
    "menu_free": true,
    "time_checks": true,
    "no_repetition": true
  },
  "is_draft_ready": false,
  "is_approved": false
}
```

### Endpoint: `GET /outline_chat/{project_id}/export?format=json`

**Response:**
```json
{
  "tutorial_name": "Introduction to Python",
  "foss_version": "Not Applicable",
  "target_audience": "College beginners",
  "entry_behaviour": "Basic computer skills",
  "purpose": "Learn Python programming fundamentals",
  "recommended_no_of_tutorials": 5,
  "prepared_by": "John Doe",
  "domain": "",
  "reviewer": "IITB ST Team",
  "date": "2024-01-15",
  "keywords": ["python", "programming", "beginners"],
  "about_course": "...",
  "course_objectives": ["...", "..."],
  "topics_included": ["...", "..."],
  "topics_not_included": ["..."],
  "core_example": "Student grade calculator",
  "allied_examples": ["Employee payroll system"],
  "tutorial_rows": [
    {
      "tutorial_number": 1,
      "title": "Getting Started",
      "topics_details": ["Install Python", "Open IDLE", "Write first program"],
      "time_seconds": 300,
      "comments": "Attach Python installer"
    }
  ]
}
```

## Pedagogy Rules Enforced

The bot automatically enforces these Spoken Tutorial rules:

1. **Core Example Required**: Every course must have a core example for demonstrations
2. **75-80% Demo Content**: At least 75% of each tutorial must be demonstration, not theory
3. **Menu-Free Instructions**: Converts menu paths (e.g., "File → Open") into action descriptions
4. **Theory Minimization**: Limits theory to 1-2 lines per tutorial
5. **No Repetition**: Flags duplicate topics across tutorials
6. **Time Sanity**: Warns if tutorials are < 60s or > 600s (10 minutes)

## Example Conversation

```
Bot: Please give the tutorial name (what should we call this course?).

SME: Introduction to Excel for Data Analysis

Bot: Who is the target audience? (e.g., school students, college beginners, lab technicians).

SME: College students in business programs

Bot: What should learners already know before starting? (short list of prerequisites / entry behaviour).

SME: Basic computer skills, familiarity with Windows

Bot: What is the main purpose of this course in one sentence? (What will learners be able to do?)

SME: Students will be able to analyze data using Excel functions, create charts, and generate reports.

Bot: List the top 3-6 course objectives — what concrete things should learners be able to do after completing the course?
Tip: Please phrase objectives as actions (e.g., 'Create a basic report', 'Write and run a Python function').

SME: 
1. Import data from CSV files
2. Use VLOOKUP and SUMIF functions
3. Create pivot tables
4. Generate charts and graphs
5. Format professional reports

Bot: Give one core example (a real file, dataset, scenario, or project) we can use for demonstrations.
Example prompts: 'student marksheet' for Excel; 'bookstore DB' for SQL; 'small image set' for image processing.
(Why: Spoken Tutorials teach via a running example — this is mandatory.)

SME: A student marksheet Excel file with columns: Student Name, Math, Science, English, Total, Grade

Bot: How many short tutorials (modules) should this course contain? (recommended: 3-12).

SME: 5

Bot: Tutorial #1 — give a short title (e.g., 'Importing data').

SME: Importing and Formatting Data

Bot: For Tutorial #1 (Importing and Formatting Data): list 3-6 demonstrable steps the learner will follow (short bullets).
Tip: Avoid menu-only instructions like 'File → Open'. Instead describe actions: 'Open the marksheet file from Desktop and show how to sort by marks'.

SME:
1. Open the marksheet CSV file from Desktop
2. Show how to format column headers (bold, center)
3. Adjust column widths to fit content
4. Apply number formatting to marks columns
5. Add borders to the table

Bot: Estimated time for Tutorial #1 (Importing and Formatting Data) in seconds (e.g., 300 for 5 minutes).

SME: 300

[... continues for all 5 tutorials ...]

Bot: Here's your draft Course Outline:

[Shows formatted draft with compliance badge]

Please review and suggest any edits. Type 'approve' when ready to finalize.

SME: Change tutorial 2 title to "Working with Functions" and add a step about IF function

Bot: ✓ Applied your edits: Updated tutorial 2 title and added IF function step

[Shows updated draft]

SME: approve

Bot: ✅ Outline approved! Generating final outputs...
```

## Tips for SMEs

1. **Be Specific**: Provide concrete examples and real scenarios
2. **Think Demo-First**: Focus on what learners will DO, not just what they'll learn
3. **Avoid Menu Paths**: Instead of "File → Save As", describe: "Save the file with a new name using the Save As dialog"
4. **Keep Steps Short**: Each demonstrable step should be clear and actionable
5. **Use Real Examples**: The core example should be something learners can relate to

## Troubleshooting

### Bot keeps asking the same question
- Make sure you're providing the information in the format requested
- Check if your answer was clear enough (the bot may need clarification)

### Validation errors appear
- Address each error one by one
- The bot will guide you on how to fix them

### Can't approve the outline
- Make sure you're in the "review" phase
- Type exactly "approve" (case-insensitive)
- Check that all required fields are filled

## Next Steps After Approval

Once the outline is approved:
1. Export the JSON using the export endpoint
2. Use the JSON to generate scripts (can be integrated with the script generation pipeline)
3. The outline data matches the Course Outline template format exactly

