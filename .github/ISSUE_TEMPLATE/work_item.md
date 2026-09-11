---
name: Work item (maintainers)
about: A scoped piece of work — root cause, plan, or design proposal
title: ''
labels: ''
assignees: ''
---

<!--
Maintainer-facing. Delete every heading that doesn't apply — a two-line issue is
fine (#473), and so is a full investigation (#484). Add the type label
(bug / enhancement / documentation / refactor) and any area labels by hand.

If this is part of a larger effort, open with: Part of #N.
-->

## Summary

<!-- What's wrong, or what should exist. One or two sentences. -->

## Root cause

<!--
For bugs: the actual mechanism, not the symptom. File and line where it lives,
the offending code, and the evidence — command output, logs, a reproduction.
Name the failure sequence explicitly if it's more than one step.
-->

## Scope

<!--
The change, as a list of concrete edits: files, functions, migration revision
ids, new parameters. Precise enough that the PR can be read against it.
-->

## Tests

<!-- What proves this works, including the regression case that would have caught it. -->

## Out of scope

<!-- Related problems this deliberately doesn't fix, and why. Link follow-up issues. -->

## Related

<!-- Part of #N, blocks / blocked by #N, related #N. -->
