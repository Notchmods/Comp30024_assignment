import argparse
import sys
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# The local referee import may expect websockets even when this simple harness
# does not use the server pathway.
m = types.ModuleType("websockets")
m.serve = None
sys.modules.setdefault("websockets", m)

from referee.game import Board, PlayerColor
from agent_test.program import Agent, TRANSPOSITION_TABLE


def run_game(red_mode, blue_mode, max_turns, time_limit):
    TRANSPOSITION_TABLE.clear()
    board = Board()
    red = Agent(PlayerColor.RED, search_mode=red_mode)
    blue = Agent(PlayerColor.BLUE, search_mode=blue_mode)
    players = {PlayerColor.RED: red, PlayerColor.BLUE: blue}
    start = time.process_time()

    for _ in range(max_turns):
        if board.game_over:
            break

        color = board.turn_color
        player = players[color]
        remaining = max(0.0, time_limit - player.time_used)
        action = player.action(
            time_remaining=remaining,
            space_remaining=250.0,
            space_limit=250.0,
        )
        board.apply_action(action)
        red.update(color, action)
        blue.update(color, action)

    elapsed = time.process_time() - start
    print("red_mode:", red_mode)
    print("blue_mode:", blue_mode)
    print("turns:", board.turn_count)
    print("game_over:", board.game_over)
    print("winner:", board.winner_color if board.game_over else None)
    print("red_cpu:", f"{red.time_used:.3f}")
    print("blue_cpu:", f"{blue.time_used:.3f}")
    print("harness_cpu:", f"{elapsed:.3f}")
    print("tt_entries:", len(TRANSPOSITION_TABLE))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--red", default="abp_tt", choices=("abp_tt", "abp", "plain"))
    parser.add_argument("--blue", default="plain", choices=("abp_tt", "abp", "plain"))
    parser.add_argument("--turns", type=int, default=300)
    parser.add_argument("--time", type=float, default=180.0)
    args = parser.parse_args()
    run_game(args.red, args.blue, args.turns, args.time)


if __name__ == "__main__":
    main()
