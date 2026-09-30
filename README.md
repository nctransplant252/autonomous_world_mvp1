# Autonomous World MVP

A local MVP for an autonomous fictional-world simulator.

## What it does

You define:
- a world
- characters
- their personalities, goals, fears, relationships, memories, and private knowledge
- an initial situation

Then press **PLAY**. Characters make their own decisions. The user does not select their actions.

The simulator records:
- actions
- dialogue
- motivations
- knowledge used
- consequences
- memories
- relationship changes
- world-state changes

The MVP includes:
- Python backend
- simple browser UI
- structured world state
- autonomous character decision-making
- action validation
- persistent memories
- relationship state
- event log
- "why did they do that?" trace
- save/load JSON
- a built-in Harry/Ron/Hermione test scenario

## Important design rule

The LLM is the actor/decision-maker, not the source of truth.

The Python simulation owns canon/state. The model proposes an action; the simulator validates and applies it.

This is intentional. It prevents the model from simply writing a story and calling that autonomy.

## Requirements

- Python 3.10+
- An OpenAI API key
- An API model available to your account

## Setup in PyCharm

1. Open this folder as a PyCharm project.
2. Create a Python virtual environment.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Copy `.env.example` to `.env`.
5. Put your API key and an API model ID in `.env`.
6. Start the app:

```bash
python app.py
```

7. Open the address shown in the terminal.

## Environment

```text
OPENAI_API_KEY=your_key
OPENAI_MODEL=your_api_model_id
SIMULATION_STEPS=24
```

Do not commit `.env`.

## First test

The included scenario is:

> Harry and Ron have reconciled after the First Task and return to Gryffindor Tower. Hermione has spent weeks caught between them.

Nothing says Hermione MUST be angry.

The simulator has to derive her response from her character state, memories, relationships, goals, and knowledge.

That is the test.

## Architecture

WORLD
  ↓
CHARACTERS
  ↓
PRIVATE KNOWLEDGE / MEMORY
  ↓
DECISION MODEL
  ↓
ACTION VALIDATION
  ↓
STATE CHANGE
  ↓
EVENT LOG
  ↓
NEXT ACTOR

Later, a separate cinematic layer can consume the event log:

SIMULATION → EVENTS → SCENES/SHOTS → VIDEO/VOICE/MUSIC → MOVIE

Do not make the video generator responsible for story logic. The simulation should establish what happened first.
