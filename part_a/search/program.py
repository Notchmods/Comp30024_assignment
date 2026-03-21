# COMP30024 Artificial Intelligence, Semester 1 2026
# Project Part A: Single Player Cascade

from .core import CellState, Coord, Direction, Action, MoveAction, EatAction, CascadeAction, PlayerColor
from .utils import render_board
from dataclasses import dataclass

@dataclass(frozen=True)
class GameState:
    board: frozenset[tuple[Coord, CellState]] 

    def to_dict(self):
        # convert back to dict
        return dict(self.board)

    @staticmethod
    def from_dict(board_dict: dict[Coord, CellState]):
        # create state from input
        return GameState(frozenset(board_dict.items()))

    def is_goal(self):
        # no blue left
        return not any(cell.color == PlayerColor.BLUE for _, cell in self.board)
    
def get_successors(state: GameState, current_player: PlayerColor = PlayerColor.RED):
    # generate valid next states and actions
    successors = []
    board_dict = state.to_dict() 
    
    for coord, cell in board_dict.items():
        if cell.color == current_player:
            for direction in Direction:
                # move
                move_action = MoveAction(coord, direction)
                new_board_move = apply_move(board_dict, move_action)
                if new_board_move is not None:
                    successors.append((GameState.from_dict(new_board_move), move_action))
                    
                # eat
                eat_action = EatAction(coord, direction)
                new_board_eat = apply_eat(board_dict, eat_action)
                if new_board_eat is not None:
                    successors.append((GameState.from_dict(new_board_eat), eat_action))
                    
                # cascade
                cascade_action = CascadeAction(coord, direction)
                new_board_cascade = apply_cascade(board_dict, cascade_action)
                if new_board_cascade is not None:
                    successors.append((GameState.from_dict(new_board_cascade), cascade_action))                   
    return successors

def apply_move(board_dict: dict, action: MoveAction):
    try: # bounds check
        dest = action.coord + action.direction
    except ValueError:
        return None # move off board

    attacker = board_dict[action.coord]
    if dest in board_dict and board_dict[dest].color != attacker.color:
        return None # target must not be an enemy stack

    new_board = board_dict.copy()
    moving_stack = new_board.pop(action.coord)
    
    if dest in new_board: # merge
        existing = new_board[dest]
        new_board[dest] = CellState(moving_stack.color, moving_stack.height + existing.height)
    else: # relocate
        new_board[dest] = moving_stack
    return new_board

def apply_eat(board_dict: dict, action: EatAction):
    try: # bounds check
        dest = action.coord + action.direction
    except ValueError:
        return None # target off board

    attacker = board_dict[action.coord]
    target = board_dict.get(dest)
    if not target or target.color == attacker.color:
        return None # target must be an enemy stack
    if attacker.height < target.height:
        return None # attacking stack height >= target stack height

    new_board = board_dict.copy()
    attacker_stack = new_board.pop(action.coord)
    new_board[dest] = attacker_stack # replace blue
    return new_board
    
def apply_cascade(board_dict: dict, action):
    new_board = board_dict.copy()

    return new_board

def search(
    board: dict[Coord, CellState]
) -> list[Action] | None:
    """
    This is the entry point for your submission. You should modify this
    function to solve the search problem discussed in the Part A specification.
    See `core.py` for information on the types being used here.

    Parameters:
        `board`: a dictionary representing the initial board state, mapping
            coordinates to `CellState` instances (each with a `.color` and
            `.height` attribute).

    Returns:
        A list of actions (MoveAction, EatAction, or CascadeAction), or `None`
        if no solution is possible.
    """
    queue=[]
    

    # The render_board() function is handy for debugging. It will print out a
    # board state in a human-readable format. If your terminal supports ANSI
    # codes, set the `ansi` flag to True to print a colour-coded version!
    print(render_board(board, ansi=True))
    print(board)

    # Do some impressive AI stuff here to find the solution...
    # ...
    # ... (your solution goes here!)
    # ...

    # Here we're returning "hardcoded" actions as an example of the expected
    # output format. Of course, you should instead return the result of your
    # search algorithm. Remember: if no solution is possible for a given input,
    # return `None` instead of a list.
    return [
            MoveAction(Coord(3, 3), Direction.Down),
            EatAction(Coord(4, 3), Direction.Down),
    ]
