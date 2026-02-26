---
name: spec
description: Turns a conversation, idea, or discussion into a structured technical specification document. Use when the user asks to write a spec, technical spec, design doc, RFC, API design, data model, spec this out, turn this into a spec, write up the design, document this, implementation spec, spec for this feature.
argument-hint: "[feature or system to specify]"
allowed-tools: Write
---

# Spec

Turns a conversation, idea, or discussion into a complete, structured technical specification saved as a markdown file.

## Workflow

1. **Extract the core idea** — identify what system, feature, or API is being specified from the conversation or argument. See [DESIGN.md](DESIGN.md).

2. **Ask clarifying questions if needed** — if the problem, scale, or constraints are unclear, ask at most 3 targeted questions before proceeding. See [DESIGN.md](DESIGN.md).

3. **Draft the problem statement and goals** — write the Problem Statement and Goals/Non-Goals sections first. Do not proceed to design until these are locked. See [FORMAT.md](FORMAT.md).

4. **Design the API/interface surface** — specify the public interface: functions, endpoints, decorators, or CLI commands. Use code blocks. See [FORMAT.md](FORMAT.md).

5. **Design the data model** — define key data structures, schemas, and artifact shapes. Use code blocks. See [FORMAT.md](FORMAT.md).

6. **Identify failure modes** — enumerate what can go wrong and how each is mitigated. See [FORMAT.md](FORMAT.md).

7. **Write the full spec** — assemble all sections in the exact output format. See [FORMAT.md](FORMAT.md).

8. **Save to file** — write the spec to `spec-[slug].md` in the current working directory, where slug is a lowercase hyphenated version of the title. Print the full spec to the conversation as well.

## Self-review checklist

Before delivering, verify ALL:

- [ ] Problem Statement is 3-6 sentences of prose — no bullet points
- [ ] Goals are concrete and measurable (not "improve performance" but "p99 latency < 500ms")
- [ ] Non-Goals section is present with at least 2 items
- [ ] API/Interface section contains actual code blocks — not prose descriptions of code
- [ ] Data Model section contains actual code blocks — not prose descriptions
- [ ] Failure Modes table is present with Failure, Probability, Impact, and Mitigation columns
- [ ] Success Metrics are measurable (numbers, percentages, latency targets)
- [ ] Open Questions is present — even if empty, the section must appear
- [ ] File is saved as `spec-[slug].md` in the current working directory
- [ ] No section contains "TBD" — unknowns go in Open Questions instead

## Golden rules

Hard rules. Never violate these.

1. **Problem before design.** Always write the Problem Statement and Goals before designing anything. A design without a problem statement will be wrong.
2. **Non-Goals are mandatory.** Never skip the Non-Goals section. It is as important as Goals — it defines the boundary of the work.
3. **Failure Modes are mandatory.** A spec with no Failure Modes table is incomplete. Happy-path-only specs fail in production.
4. **Success Metrics are mandatory.** Without measurable criteria there is no definition of done. Vague metrics ("users are happy") are rejected — replace with numbers.
5. **Never write TBD in API or Data Model.** If the design is unknown, write the open question in the Open Questions section. The spec body must contain actual designs, not placeholders.
6. **Always save the spec to a file.** Print to conversation AND write `spec-[slug].md`. Specs that exist only in the conversation are lost.
7. **Ask at most 3 clarifying questions.** If the problem is truly ambiguous, ask — but never more than 3 at once, and prefer to proceed with stated assumptions over interrogating the user.

## Reference files

| File | Contents |
|------|----------|
| [FORMAT.md](FORMAT.md) | Complete spec template, section-by-section writing guidance, good vs bad examples, and a complete abbreviated example spec |
| [DESIGN.md](DESIGN.md) | How to extract design from conversation, API-first design principle, handling ambiguity, making key decisions explicit |
