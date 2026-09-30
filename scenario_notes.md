# MVP Test Notes

## Test question

Can autonomous characters produce a believable social situation without being handed a plot?

## Scenario

Harry and Ron have reconciled after the First Task.

They return to Gryffindor Tower.

Hermione spent weeks caught between them.

## What is NOT predetermined

The system must not be told:

- Hermione is angry.
- Hermione forgives Ron.
- Harry and Ron celebrate.
- Ron apologizes.
- Hermione confronts Ron.
- Everyone hugs.
- A dramatic argument happens.

Any of those can happen if the character state makes them plausible.

## What we are watching for

A good run should demonstrate:

1. Characters have different priorities.
2. Characters do not know things they could not know.
3. Actions follow from prior events.
4. Relationships change because of interactions.
5. The world remembers what happened.
6. Characters can choose not to act.
7. The model does not automatically manufacture drama.
8. A later action can be traced back to earlier information.

## Bad signs

If the output looks like:

> Hermione is angry because this creates conflict, so she confronts Ron.

that is not sufficient.

If the model invents:

> Hermione secretly knows Ron has been planning something for weeks.

when no such knowledge exists, the knowledge model failed.

If every turn produces a major revelation, the system is probably optimizing for entertainment instead of behaving autonomously.

## The eventual movie test

Once the simulation is convincing, the event log becomes the source of truth for a cinematic adapter.

The cinematic adapter should never decide what actually happened.

It should decide:

- which events deserve scenes
- camera/shot descriptions
- dialogue presentation
- transitions
- pacing
- music/SFX suggestions

Then a video pipeline can render the established events.
