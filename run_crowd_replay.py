"""
Replay crowd voting step-by-step from a previous debate folder.

This script reuses a fixed transcript/latent state from a source debate and
re-runs crowd votes in the original livestream order for benchmarking.
"""

import argparse
import copy
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.agents.base import AgentContext, FileUpdateOperation
from src.agents.crowd import CrowdAgent
from src.config import Config
from src.utils.debate_logger import DebateLogger
from src.utils.file_manager import FileManager
from src.utils.raw_data_logger import RawDataLogger


def _parse_ts(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def _load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _resolve_source_dir(source_debate: str) -> Path:
    direct = Path(source_debate)
    if direct.exists() and direct.is_dir():
        return direct
    fallback = Path("debates") / source_debate
    if fallback.exists() and fallback.is_dir():
        return fallback
    raise FileNotFoundError(
        f"Source debate folder not found: {source_debate} "
        f"(tried '{direct}' and '{fallback}')"
    )


def _extract_crowd_steps(source_log_path: Path) -> List[Dict[str, Any]]:
    steps: List[Dict[str, Any]] = []
    with open(source_log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if entry.get("type") != "agent_turn":
                continue
            agent = entry.get("agent", {})
            if agent.get("name") != "crowd":
                continue
            response = entry.get("response", {})
            if response.get("success") is False:
                continue
            context = entry.get("context", {})
            steps.append(
                {
                    "timestamp": entry.get("timestamp", ""),
                    "phase": entry.get("phase", ""),
                    "round_number": int(entry.get("round_number", 0)),
                    "instructions": context.get("instructions", "Replay crowd vote"),
                }
            )
    if not steps:
        raise ValueError("No successful crowd agent_turn entries found in source debate_log.jsonl")
    return steps


def _slice_history_until(
    history_chat: Dict[str, Any],
    cutoff_ts: datetime,
) -> Dict[str, Any]:
    result = copy.deepcopy(history_chat)
    transcript = history_chat.get("public_transcript", [])
    result["public_transcript"] = [
        t for t in transcript
        if t.get("timestamp") and _parse_ts(str(t.get("timestamp"))) <= cutoff_ts
    ]
    # Team notes are not used by crowd prompts; keep empty to save context.
    result["team_notes"] = {"a": [], "b": []}
    return result


def _slice_latent_until(
    debate_latent: Dict[str, Any],
    cutoff_ts: datetime,
) -> Dict[str, Any]:
    result = copy.deepcopy(debate_latent)
    history = debate_latent.get("round_history", [])
    result["round_history"] = [
        r for r in history
        if r.get("analyzed_at") and _parse_ts(str(r.get("analyzed_at"))) <= cutoff_ts
    ]
    return result


def _load_personas(source_dir: Path) -> List[Dict[str, Any]]:
    personas_path = source_dir / "personas.json"
    if personas_path.exists():
        data = _load_json(personas_path)
        personas = data.get("personas", [])
        if personas:
            return personas

    crowd_path = source_dir / "crowd_opinion.json"
    if crowd_path.exists():
        data = _load_json(crowd_path)
        personas = data.get("personas", [])
        if personas:
            return personas

    raise ValueError("No personas found in source debate (personas.json or crowd_opinion.personas)")


def _select_personas(personas: List[Dict[str, Any]], crowd_size: Optional[int]) -> List[Dict[str, Any]]:
    if crowd_size is None:
        return personas
    if crowd_size < 1:
        raise ValueError("crowd_size override must be >= 1")
    if crowd_size > len(personas):
        raise ValueError(
            f"crowd_size override ({crowd_size}) exceeds source personas ({len(personas)}). "
            "Use a smaller or equal value."
        )
    return personas[:crowd_size]


def _apply_crowd_vote_update(file_manager: FileManager, update_data: Dict[str, Any]) -> None:
    data = file_manager._read_json("crowd_opinion")

    if "voters" not in data:
        data["voters"] = []
    if "vote_rounds" not in data:
        data["vote_rounds"] = []

    voters_by_id = {v.get("voter_id"): v for v in data["voters"]}
    for vote in update_data["votes"]:
        voter_id = vote["voter_id"]
        if voter_id not in voters_by_id:
            new_voter = {
                "voter_id": voter_id,
                "persona": vote.get("persona", "Unknown"),
                "persona_description": vote.get("persona_description", ""),
                "persona_type": vote.get("persona_type", "unknown"),
                "voting_history": [],
                "current_score": 0,
                "journal": "",
            }
            data["voters"].append(new_voter)
            voters_by_id[voter_id] = new_voter

        voter = voters_by_id[voter_id]
        voter["voting_history"].append(
            {
                "round": update_data["round"],
                "score": vote["score"],
                "rationale": vote.get("rationale", vote.get("reasoning", "")),
            }
        )
        voter["current_score"] = vote["score"]

        if "journal_entry" in vote and vote["journal_entry"]:
            current = voter.get("journal", "")
            voter["journal"] = f"{current}\n\n{vote['journal_entry']}".strip()

    data["vote_rounds"].append(
        {
            "round": update_data["round"],
            "average_score": update_data["average_score"],
            "vote_count": update_data["vote_count"],
            "timestamp": update_data["timestamp"],
        }
    )
    file_manager.write_by_moderator("crowd_opinion", data)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay crowd voting from a previous debate.")
    parser.add_argument("--source-debate", required=True, help="Source debate id or folder path")
    parser.add_argument("--replay-name", default=datetime.now().strftime("%Y%m%d_%H%M%S"), help="Replay label suffix")
    parser.add_argument("--crowd-model", default=None, help="Override crowd model id")
    parser.add_argument("--crowd-context-mode", default=None, choices=["full_transcript", "latest_plus_latent"])
    parser.add_argument("--crowd-temperature", type=float, default=None, help="Override crowd temperature")
    parser.add_argument("--crowd-size", type=int, default=None, help="Use first N personas from source")
    parser.add_argument("--max-steps", type=int, default=None, help="Replay first N crowd steps only")
    parser.add_argument("--force", action="store_true", help="Allow existing replay output folder")
    return parser.parse_args()


def _build_replay_config(base_config: Config, args: argparse.Namespace, crowd_size: int) -> Config:
    cfg = copy.deepcopy(base_config)
    cfg.crowd_size = crowd_size
    if args.crowd_model is not None:
        cfg.crowd_model = args.crowd_model
    if args.crowd_context_mode is not None:
        cfg.crowd_context_mode = args.crowd_context_mode
    if args.crowd_temperature is not None:
        cfg.crowd_temperature = args.crowd_temperature
    cfg.validate()
    return cfg


async def run_replay(args: argparse.Namespace) -> None:
    source_dir = _resolve_source_dir(args.source_debate)
    source_id = source_dir.name

    replay_id = f"{source_id}__replay_{args.replay_name}"
    replay_dir = Path("debates") / replay_id
    if replay_dir.exists() and not args.force:
        raise FileExistsError(f"Replay output already exists: {replay_dir} (use --force to overwrite)")

    config = Config.from_files()
    personas = _load_personas(source_dir)
    personas = _select_personas(personas, args.crowd_size)
    replay_config = _build_replay_config(config, args, crowd_size=len(personas))

    source_history = _load_json(source_dir / "history_chat.json")
    source_latent = _load_json(source_dir / "debate_latent.json")
    source_steps = _extract_crowd_steps(source_dir / "debate_log.jsonl")
    if args.max_steps is not None:
        source_steps = source_steps[: args.max_steps]

    file_manager = FileManager(str(replay_dir))
    file_manager.initialize_files(replay_id, source_history.get("topic", ""))

    # Fixed context artifacts for this replay.
    file_manager.write_by_moderator("history_chat", source_history)
    file_manager.write_by_moderator("debate_latent", source_latent)
    file_manager.write_by_moderator(
        "personas",
        {
            "debate_id": replay_id,
            "source_debate_id": source_id,
            "created_at": datetime.now().isoformat(),
            "personas": personas,
        },
    )
    file_manager.write_by_moderator(
        "crowd_opinion",
        {
            "debate_id": replay_id,
            "voters": [],
            "personas": personas,
            "vote_rounds": [],
        },
    )

    logger = DebateLogger(replay_id, replay_dir)
    raw_logger = RawDataLogger(replay_id, str(replay_dir))
    crowd = CrowdAgent(
        name="crowd",
        file_manager=file_manager,
        config=replay_config,
        raw_data_logger=raw_logger,
        personas=personas,
    )

    logger.log_moderator_action(
        action="crowd_replay_started",
        details={
            "source_debate": str(source_dir),
            "replay_id": replay_id,
            "step_count": len(source_steps),
            "crowd_model": replay_config.crowd_model,
            "crowd_context_mode": replay_config.crowd_context_mode,
            "crowd_temperature": replay_config.crowd_temperature,
            "crowd_size": replay_config.crowd_size,
        },
    )

    for idx, step in enumerate(source_steps, start=1):
        cutoff = _parse_ts(step["timestamp"])
        history_slice = _slice_history_until(source_history, cutoff)
        latent_slice = _slice_latent_until(source_latent, cutoff)
        crowd_state = file_manager.read_for_agent("crowd", "crowd_opinion")
        personas_state = file_manager.read_for_agent("crowd", "personas")

        context = AgentContext(
            debate_id=replay_id,
            topic=source_history.get("topic", ""),
            phase=step["phase"],
            round_number=step["round_number"],
            current_state={
                "history_chat": history_slice,
                "debate_latent": latent_slice,
                "crowd_opinion": crowd_state,
                "personas": personas_state,
            },
            instructions=step["instructions"],
            metadata={"replay_step": idx, "source_timestamp": step["timestamp"]},
        )

        logger.log_moderator_action(
            action="crowd_replay_step_started",
            details={
                "step": idx,
                "phase": step["phase"],
                "round_number": step["round_number"],
                "instructions": step["instructions"],
            },
        )

        response = await crowd.execute_turn(context)
        logger.log_agent_turn(
            agent_name="crowd",
            agent_role="crowd",
            phase=context.phase,
            round_number=context.round_number,
            context=asdict(context),
            response={
                "success": response.success,
                "output": response.output,
                "file_updates": [asdict(u) for u in response.file_updates],
                "metadata": response.metadata,
            },
            errors=response.errors if not response.success else None,
        )

        if not response.success:
            logger.log_error(
                error_type="crowd_replay_failure",
                message=", ".join(response.errors),
                context={"step": idx, "phase": step["phase"], "round_number": step["round_number"]},
            )
            raise RuntimeError(f"Crowd replay failed at step {idx}: {response.errors}")

        for update in response.file_updates:
            if update.operation != FileUpdateOperation.ADD_CROWD_VOTE:
                continue
            _apply_crowd_vote_update(file_manager, update.data)
            logger.log_file_update(
                file_type="crowd_opinion",
                operation=update.operation.value,
                data=update.data,
            )

        logger.log_moderator_action(
            action="crowd_replay_step_completed",
            details={
                "step": idx,
                "average_score": response.metadata.get("average_score"),
                "voter_count": response.metadata.get("voter_count"),
            },
        )

    replay_manifest = {
        "replay_id": replay_id,
        "source_debate": str(source_dir),
        "created_at": datetime.now().isoformat(),
        "steps_replayed": len(source_steps),
        "overrides": {
            "crowd_model": args.crowd_model,
            "crowd_context_mode": args.crowd_context_mode,
            "crowd_temperature": args.crowd_temperature,
            "crowd_size": args.crowd_size,
            "max_steps": args.max_steps,
        },
        "effective_config": {
            "crowd_model": replay_config.crowd_model,
            "crowd_context_mode": replay_config.crowd_context_mode,
            "crowd_temperature": replay_config.crowd_temperature,
            "crowd_size": replay_config.crowd_size,
        },
    }
    with open(replay_dir / "replay_manifest.json", "w", encoding="utf-8") as f:
        json.dump(replay_manifest, f, indent=2, ensure_ascii=False)

    logger.log_moderator_action(
        action="crowd_replay_completed",
        details={"steps_replayed": len(source_steps)},
    )

    print("\n" + "=" * 60)
    print("CROWD REPLAY COMPLETED")
    print("=" * 60)
    print(f"Source: {source_dir}")
    print(f"Replay: {replay_dir}")
    print(f"Steps replayed: {len(source_steps)}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio_args = _parse_args()
    import asyncio

    asyncio.run(run_replay(asyncio_args))
