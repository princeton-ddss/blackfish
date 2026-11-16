---
name: blackfish-project-setup
description: Configure local Blackfish project tracking when the user asks to connect or update a GitHub project board.
---

Paths and commands below are relative to the repository root unless a working directory is specified.

Set up GitHub Project integration for agent workflow tracking.

Use the owner and project number supplied in the request or already established in the conversation. Creating an issue or PR alone does not request project configuration changes.

## Step 1: Get project details

If these details are not available, ask the user:
- Owner: organization name (e.g., "princeton-ddss") or "@me" for personal projects
- Project number: the project number (visible in project URL)

## Step 2: Query project structure via GraphQL

For organization projects:
```bash
gh api graphql -f query='
  query($owner: String!, $number: Int!) {
    organization(login: $owner) {
      projectV2(number: $number) {
        id
        title
        field(name: "Status") {
          ... on ProjectV2SingleSelectField {
            id
            options {
              id
              name
            }
          }
        }
      }
    }
  }
' -F owner="<owner>" -F number=<number>
```

For personal projects (when owner is "@me"), use this query instead:
```bash
gh api graphql -f query='
  query($number: Int!) {
    viewer {
      projectV2(number: $number) {
        id
        title
        field(name: "Status") {
          ... on ProjectV2SingleSelectField {
            id
            options {
              id
              name
            }
          }
        }
      }
    }
  }
' -F number=<number>
```

## Step 3: Validate required status options

The project MUST have these status options (names can vary slightly):
- Backlog (or "Todo", "New")
- Ready (or "Ready to Start")
- In progress (or "Active", "Working")
- In review (or "Review", "Pending Review")
- Done (or "Closed", "Complete")

Compare status names case-insensitively when identifying their roles, but preserve the exact names and IDs returned by GitHub in the configuration. If any are missing, warn the user and ask if they want to proceed anyway.

## Step 4: Write configuration file

The config file `.claude/projects.json` is an array of projects. If the file exists, append to it (avoiding duplicates by project_id). If not, create a new array.

Each project entry:
```json
{
  "name": "<title-from-query>",
  "owner": "<owner>",
  "project_number": <number>,
  "project_id": "<project-id-from-query>",
  "fields": {
    "status": {
      "id": "<field-id-from-query>",
      "options": {
        "<option-name>": "<option-id>",
        ...
      }
    }
  }
}
```

## Step 5: Confirm setup

Report to the user:
- Project title and owner
- Number of status options found
- Path to config file
- Reminder about `gh auth refresh -s project` if token scope errors occur
