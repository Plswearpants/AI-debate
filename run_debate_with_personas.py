"""
Run a debate with a fixed persona file.

Special-case utility:
- Keeps normal pipeline untouched
- Overrides persona generation for this run only

Usage:
    python run_debate_with_personas.py "Your topic here"
    python run_debate_with_personas.py "Your topic here" --persona-file persona_example.md
"""

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

from src.config import Config
from src.moderator import DebateModerator


def _extract_json_payload(text: str) -> str:
    """Extract JSON payload from markdown fenced block or raw JSON text."""
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1)
    return text.strip()


def _load_personas_from_file(path: str, crowd_size: int) -> List[Dict[str, Any]]:
    """Load and normalize personas from persona markdown/json file."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Persona file not found: {file_path}")

    raw_text = file_path.read_text(encoding="utf-8")
    payload = _extract_json_payload(raw_text)
    data = json.loads(payload)

    templates = data.get("personas", [])
    if not templates:
        raise ValueError("Persona file contains no personas")

    personas: List[Dict[str, Any]] = []
    for i in range(crowd_size):
        template = templates[i % len(templates)]
        suffix = f" (#{i // len(templates) + 1})" if crowd_size > len(templates) and i >= len(templates) else ""
        life_exp = str(template.get("life_experience", "")).strip()
        personas.append(
            {
                "id": f"v_{i+1:03d}",
                "name": f"{template.get('name', f'Persona {i+1}')}{suffix}",
                "type": str(template.get("type", "general")),
                "dimensions": template.get("dimensions", {}),
                "life_experience": life_exp,
                "description": life_exp,
            }
        )

    return personas


async def run_debate_with_personas(topic: str, persona_file: str = "persona_example.md") -> str:
    """Run debate while forcing personas from file for this one run."""
    print(f"\n{'='*60}")
    print("AI DEBATE PLATFORM (CUSTOM PERSONAS)")
    print(f"{'='*60}")
    print(f"Topic: {topic}")
    print(f"Persona file: {persona_file}")
    print(f"{'='*60}\n")

    config = Config.from_files()
    config.validate()
    personas = _load_personas_from_file(persona_file, config.crowd_size)
    print(f"[OK] Loaded {len(personas)} personas from {persona_file}")

    moderator = DebateModerator(topic=topic, config=config)

    async def _custom_generate(_topic: str, _crowd_size: int) -> List[Dict[str, Any]]:
        # Special-case override for this run.
        return personas

    # Override only for this process/run.
    moderator._generate_crowd_personas = _custom_generate  # type: ignore[attr-defined]

    print(f"Debate ID: {moderator.debate_id}")
    print(f"Output directory: debates/{moderator.debate_id}/\n")
    return await moderator.run_debate()


if __name__ == "__main__":
    args = sys.argv[1:]
    persona_file = "persona_example.md"

    if "--persona-file" in args:
        idx = args.index("--persona-file")
        if idx + 1 >= len(args):
            raise ValueError("Missing value for --persona-file")
        persona_file = args[idx + 1]
        del args[idx:idx + 2]

    if args:
        topic = " ".join(args)
    else:
        topic = "Should universal basic income be implemented?"
        print(f"No topic provided, using default:\n  \"{topic}\"")

    asyncio.run(run_debate_with_personas(topic=topic, persona_file=persona_file))
