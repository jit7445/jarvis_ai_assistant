"""Ask Gemini to map a typed sentence onto a tool, and show whether Jarvis would accept it.

    python scripts/plan_test.py I need a place to keep my recipes
    python scripts/plan_test.py --run I need a place to keep my recipes

Needs GEMINI_API_KEY in the environment. Without --run nothing is executed.
"""
import argparse
import sys
import time

from jarvis.core.proposal import to_intent
from jarvis.planner import PlannerError, gemini
from jarvis.tools.executor import execute
from jarvis.tools.registry import InvalidIntent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", help="execute the accepted intent")
    parser.add_argument("sentence", nargs="+")
    args = parser.parse_args()
    planner = gemini.from_environment()
    if planner is None:
        print("GEMINI_API_KEY is not set.")
        return 1
    sentence = " ".join(args.sentence)
    start = time.monotonic()
    try:
        proposal = planner.propose(sentence)
    except PlannerError as error:
        print(f"planner failed: {type(error).__name__} after {time.monotonic() - start:.2f} s")
        return 1
    print(f"proposal ({time.monotonic() - start:.2f} s, {planner.model}): {proposal}")
    try:
        intent = to_intent(proposal)
    except (InvalidIntent, PermissionError) as error:
        print(f"refused: {type(error).__name__}")
        return 1
    if intent is None:
        print("no tool fits")
        return 0
    print(f"accepted: {intent.tool} {intent.args}")
    if args.run:
        print(execute(intent).message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
