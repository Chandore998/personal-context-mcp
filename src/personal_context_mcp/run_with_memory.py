from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from personal_context_mcp.adapters import ClaudeCLIAdapter, CodexCLIAdapter
from personal_context_mcp.agent_wrapper import AgentContextWrapper, HttpContextBackend


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Codex or Claude behind the personal context wrapper.",
    )
    parser.add_argument("message", help="The user request to send to the selected agent.")
    parser.add_argument(
        "--agent",
        choices=["codex", "claude"],
        default="codex",
        help="Which agent adapter to use.",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL for the personal-context FastAPI backend.",
    )
    parser.add_argument(
        "--context-limit",
        type=int,
        default=5,
        help="How many relevant items to request from the context backend.",
    )
    parser.add_argument(
        "--print-meta",
        action="store_true",
        help="Print saved task outcome and memory metadata as JSON after the reply.",
    )
    parser.add_argument(
        "agent_args",
        nargs=argparse.REMAINDER,
        help="Extra arguments forwarded to the underlying agent CLI. Prefix with --.",
    )
    return parser


def normalize_agent_args(agent_args: Sequence[str]) -> list[str]:
    args = list(agent_args)
    if args and args[0] == "--":
        return args[1:]
    return args


def build_agent(agent_name: str, agent_args: Sequence[str]):
    extra_args = normalize_agent_args(agent_args)
    if agent_name == "claude":
        return ClaudeCLIAdapter(extra_args=extra_args)
    return CodexCLIAdapter(extra_args=extra_args)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    backend = HttpContextBackend(args.base_url)
    wrapper = AgentContextWrapper(backend=backend, context_limit=args.context_limit)
    agent = build_agent(args.agent, args.agent_args)

    try:
        result = wrapper.run(args.message, agent)
    except Exception as exc:  # pragma: no cover - CLI boundary
        print(str(exc), file=sys.stderr)
        return 1

    print(result.reply_text)

    if args.print_meta:
        meta = {
            "context_summary": result.context_summary,
            "saved_task_outcome": result.saved_task_outcome,
            "saved_memories": result.saved_memories,
        }
        print(json.dumps(meta, ensure_ascii=True, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
