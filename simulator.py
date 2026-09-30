from __future__ import annotations

import json
import os
import random
import re
from copy import deepcopy
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from openai import OpenAI
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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"
)

response = client.chat.completions.create(
    model="nvidia/nemotron-3.5-lightning:free",
    messages=[
        {"role": "user", "content": "Your prompt here"}
    ]
)

print(response.choices[0].message.content)

ACTION_TYPES = {
    "speak",
    "move",
    "inspect",
    "interact",
    "rest",
    "eat",
    "wait",
    "confront",
    "apologize",
    "ask",
    "leave",
}


@dataclass
class Event:
    turn: int
    actor: str
    action_type: str
    target: str | None
    action: str
    spoken: str
    motivation: str
    knowledge_used: list[str]
    consequence: str
    state_changes: dict[str, Any]

    def to_dict(self):
        return asdict(self)


class AutonomousWorld:
    def __init__(self, scenario: dict[str, Any]):
        self.state = deepcopy(scenario)
        self.turn = 0
        self.events: list[Event] = []
        self.rng = random.Random()
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("=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")
        )
        self.model = os.getenv("OPENAI_MODEL", "").strip()

        if not self.model:
            raise RuntimeError(
                "OPENAI_MODEL is not set. Put a valid API model ID in your .env file."
            )

    @property
    def characters(self):
        return self.state["characters"]

    def snapshot(self):
        return {
            "world": self.state["world"],
            "characters": self.characters,
            "relationships": self.state.get("relationships", {}),
            "events": [e.to_dict() for e in self.events],
            "turn": self.turn,
        }

    def recent_events(self, limit=8):
        return [e.to_dict() for e in self.events[-limit:]]

    def visible_state(self, actor_name: str) -> dict[str, Any]:
        actor = self.characters[actor_name]

        others = {}
        for name, character in self.characters.items():
            if name == actor_name:
                continue
            relationship = self.state["relationships"].get(actor_name, {}).get(name, {})
            others[name] = {
                "public_state": character["public_state"],
                "relationship_from_actor": relationship,
            }

        return {
            "world": self.state["world"],
            "self": actor,
            "others": others,
            "recent_events": self.recent_events(),
            "known_facts": actor.get("knowledge", []),
        }

    def choose_actor(self) -> str:
        # MVP scheduler: actors with unresolved goals get priority,
        # with a little variation so the sequence isn't perfectly mechanical.
        names = list(self.characters)
        if not names:
            raise RuntimeError("Scenario contains no characters.")

        candidates = []
        for name in names:
            goals = self.characters[name].get("goals", [])
            if goals:
                candidates.append(name)

        if not candidates:
            candidates = names

        return candidates[self.turn % len(candidates)]

    def decision_prompt(self, actor_name: str) -> str:
        visible = self.visible_state(actor_name)
        actor = self.characters[actor_name]

        return f"""
You are one autonomous character inside a persistent fictional-world simulation.

You are NOT the narrator.
You do NOT control other characters.
You do NOT write the plot.
You choose ONE plausible next action for your character.

Your character:
{json.dumps(actor, indent=2)}

What you can currently perceive/know:
{json.dumps(visible, indent=2)}

Rules:
1. Only use information this character plausibly knows.
2. Do not invent secret information.
3. Do not decide another character's reaction.
4. Do not force drama because drama would be entertaining.
5. Do not force reconciliation, conflict, romance, or cooperation.
6. Doing nothing, waiting, leaving, or observing can be valid.
7. Your action must fit the character's personality, goals, fears, relationships,
   current emotional state, and circumstances.
8. Small actions are preferred.
9. Consequences must be causal. Do not rewrite history.
10. The simulation state is authoritative.
11. If dialogue is used, keep it short and natural.
12. You may attempt an action even if it might fail, but do not claim success
    when the world state does not support it.

Return ONLY valid JSON with this exact shape:

{{
  "action_type": "one of: speak, move, inspect, interact, rest, eat, wait, confront, apologize, ask, leave",
  "action": "what the character attempts to do",
  "target": "another character name or null",
  "spoken": "dialogue if any, otherwise empty string",
  "motivation": "the immediate reason this character chose this action",
  "knowledge_used": ["specific facts from the character's knowledge or observations"],
  "intended_state_changes": {{
    "emotion": "optional short description",
    "relationship_effect": "optional short description",
    "world_effect": "optional short description"
  }}
}}
"""

    def ask_character(self, actor_name: str) -> dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.8,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are an autonomous character decision engine. Follow the supplied world state exactly.",
                },
                {"role": "user", "content": self.decision_prompt(actor_name)},
            ],
        )

        raw = response.choices[0].message.content or "{}"

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Defensive extraction if a model wraps JSON in text.
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                raise RuntimeError(f"Model returned invalid JSON: {raw}")
            data = json.loads(match.group(0))

        return self.validate_decision(actor_name, data)

    def validate_decision(self, actor_name: str, data: dict[str, Any]):
        action_type = data.get("action_type", "wait")
        if action_type not in ACTION_TYPES:
            action_type = "wait"

        target = data.get("target")
        if target and target not in self.characters:
            target = None

        action = str(data.get("action", "")).strip() or "waits and observes"
        spoken = str(data.get("spoken", "")).strip()
        motivation = str(data.get("motivation", "")).strip() or "responds to the current situation"

        knowledge = data.get("knowledge_used", [])
        if not isinstance(knowledge, list):
            knowledge = []

        # Keep only knowledge items that resemble actual known facts.
        known = self.characters[actor_name].get("knowledge", [])
        filtered_knowledge = [
            item for item in knowledge
            if isinstance(item, str) and any(item.lower() in k.lower() or k.lower() in item.lower() for k in known)
        ]

        return {
            "action_type": action_type,
            "action": action,
            "target": target,
            "spoken": spoken,
            "motivation": motivation,
            "knowledge_used": filtered_knowledge,
            "intended_state_changes": data.get("intended_state_changes", {}),
        }

    def apply_decision(self, actor_name: str, decision: dict[str, Any]) -> Event:
        actor = self.characters[actor_name]
        target = decision["target"]
        changes = decision.get("intended_state_changes", {})

        consequence = self.resolve_consequence(
            actor_name,
            decision["action_type"],
            target,
            decision["action"],
        )

        # Update actor's public/emotional state conservatively.
        emotion = changes.get("emotion")
        if emotion:
            actor["public_state"] = str(emotion)

        # Add a memory of what the actor actually experienced.
        memory = (
            f"Turn {self.turn}: {decision['action']}."
            + (f" {decision['spoken']}" if decision["spoken"] else "")
            + f" Result: {consequence}"
        )
        actor.setdefault("memory", []).append(memory)

        # Relationship effects are deliberately small and explicit.
        relationship_effect = changes.get("relationship_effect")
        if target and relationship_effect:
            rel = self.state["relationships"].setdefault(actor_name, {}).setdefault(
                target,
                {"trust": 0, "affection": 0, "tension": 0},
            )
            effect_text = str(relationship_effect).lower()

            if any(word in effect_text for word in ["trust", "reassure", "honest"]):
                rel["trust"] += 1
            if any(word in effect_text for word in ["angry", "hurt", "resent"]):
                rel["tension"] += 1
            if any(word in effect_text for word in ["closer", "affection", "care"]):
                rel["affection"] += 1

        event = Event(
            turn=self.turn,
            actor=actor_name,
            action_type=decision["action_type"],
            target=target,
            action=decision["action"],
            spoken=decision["spoken"],
            motivation=decision["motivation"],
            knowledge_used=decision["knowledge_used"],
            consequence=consequence,
            state_changes=changes,
        )

        self.events.append(event)

        # Share only publicly observable information.
        self._update_public_knowledge(actor_name, event)

        return event

    def resolve_consequence(self, actor_name, action_type, target, action):
        if action_type == "wait":
            return f"{actor_name} waits without forcing the situation."

        if action_type == "speak":
            if target:
                return f"{actor_name} addresses {target}; {target} can respond on a later turn."
            return f"{actor_name} speaks aloud."

        if action_type == "confront":
            if target:
                return f"{actor_name} confronts {target}; the confrontation changes the social situation."
            return f"{actor_name} prepares to confront someone."

        if action_type == "apologize":
            if target:
                return f"{actor_name} attempts an apology to {target}."
            return f"{actor_name} reflects on whether an apology is needed."

        if action_type == "leave":
            return f"{actor_name} leaves the immediate interaction."

        return f"{actor_name} attempts the action: {action}"

    def _update_public_knowledge(self, actor_name: str, event: Event):
        # Other characters can learn only what was observable.
        if event.spoken or event.action_type in {"confront", "apologize", "move"}:
            for name, character in self.characters.items():
                if name == actor_name:
                    continue

                fact = f"{actor_name} {event.action}"
                if fact not in character.setdefault("knowledge", []):
                    character["knowledge"].append(fact)

    def step(self):
        actor = self.choose_actor()
        decision = self.ask_character(actor)
        self.turn += 1
        event = self.apply_decision(actor, decision)
        return event.to_dict()

    def run(self, steps: int):
        events = []
        for _ in range(steps):
            events.append(self.step())
        return events

    def save(self, path: Path):
        path.write_text(json.dumps(self.snapshot(), indent=2), encoding="utf-8")


def load_scenario(name: str):
    if name != "harry_test":
        raise ValueError(f"Unknown scenario: {name}")

    return {
        "world": {
            "title": "Gryffindor Tower — After the First Task",
            "time": "Evening",
            "location": "Gryffindor common room",
            "premise": (
                "Harry and Ron have reconciled after the First Task and returned "
                "to Gryffindor Tower. Hermione has been caught between them during "
                "their weeks of conflict."
            ),
            "rules": [
                "Characters are autonomous.",
                "The user does not choose actions.",
                "There is no predetermined ending.",
                "Characters may disagree, forgive, confront, joke, withdraw, or do nothing.",
                "Characters may only act on information they plausibly know.",
                "Consequences persist.",
            ],
        },
        "relationships": {
            "Harry": {
                "Ron": {"trust": 7, "affection": 8, "tension": 2},
                "Hermione": {"trust": 8, "affection": 7, "tension": 1},
            },
            "Ron": {
                "Harry": {"trust": 6, "affection": 8, "tension": 3},
                "Hermione": {"trust": 8, "affection": 7, "tension": 1},
            },
            "Hermione": {
                "Harry": {"trust": 8, "affection": 7, "tension": 1},
                "Ron": {"trust": 7, "affection": 7, "tension": 3},
            },
        },
        "characters": {
            "Harry": {
                "personality": [
                    "brave",
                    "loyal",
                    "private",
                    "stubborn when hurt",
                    "uncomfortable with attention",
                ],
                "goals": [
                    "keep his friendships intact",
                    "survive the Tournament",
                    "have some normality",
                ],
                "fears": [
                    "losing people he loves",
                    "being seen as a liar or show-off",
                ],
                "public_state": "relieved, exhausted, emotionally raw",
                "memory": [
                    "Ron stopped speaking to him after the Goblet chose Harry.",
                    "Hermione believed Harry and stayed his friend.",
                    "Harry and Ron have now reconciled after the First Task.",
                ],
                "knowledge": [
                    "Ron has reconciled with Harry.",
                    "Hermione knows about the conflict.",
                    "The First Task is over.",
                    "They are in Gryffindor Tower.",
                ],
            },
            "Ron": {
                "personality": [
                    "loyal",
                    "funny",
                    "insecure",
                    "competitive",
                    "proud",
                    "deeply attached to Harry and Hermione",
                ],
                "goals": [
                    "repair his friendship with Harry",
                    "feel useful",
                    "avoid looking foolish",
                ],
                "fears": [
                    "being second-best",
                    "being left behind",
                    "losing Harry",
                ],
                "public_state": "relieved, embarrassed, excited",
                "memory": [
                    "Ron spent weeks angry and jealous.",
                    "Hermione was caught between Ron and Harry.",
                    "Ron realized he had treated Harry unfairly.",
                    "Ron and Harry have reconciled.",
                ],
                "knowledge": [
                    "Harry and Ron have reconciled.",
                    "Hermione knows about their conflict.",
                    "The First Task is over.",
                    "They are in Gryffindor Tower.",
                ],
            },
            "Hermione": {
                "personality": [
                    "intelligent",
                    "principled",
                    "compassionate",
                    "direct",
                    "organized",
                    "protective of her friends",
                ],
                "goals": [
                    "protect her friends",
                    "keep people honest",
                    "understand what is happening",
                ],
                "fears": [
                    "people hurting each other because they will not communicate",
                    "losing her friends",
                ],
                "public_state": "relieved that the conflict ended, but still frustrated",
                "memory": [
                    "Hermione was caught in the middle for weeks.",
                    "Hermione believed Harry when he explained himself.",
                    "Ron made the situation difficult for weeks.",
                    "Harry and Ron have reconciled.",
                ],
                "knowledge": [
                    "Harry and Ron have reconciled.",
                    "Hermione knows both sides of the conflict.",
                    "The First Task is over.",
                    "They are in Gryffindor Tower.",
                ],
            },
        },
    }


if __name__ == "__main__":
    world = AutonomousWorld(load_scenario("harry_test"))
    steps = int(os.getenv("SIMULATION_STEPS", "12"))
    events = world.run(steps)

    for event in events:
        print(
            f"\n[{event['turn']}] {event['actor']} — {event['action_type']}"
            f"\n  Action: {event['action']}"
            f"\n  Says: {event['spoken']}"
            f"\n  Why: {event['motivation']}"
            f"\n  Consequence: {event['consequence']}"
        )

    world.save(Path("simulation_result.json"))
    print("\nSaved simulation_result.json")
