# COMP30024 Artificial Intelligence, Semester 1 2026
# Project Part A: Single Player Cascade

from .core import CellState, Coord, Direction, Action, MoveAction, EatAction, CascadeAction, PlayerColor
from .utils import render_board
from dataclasses import dataclass
from collections import deque

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
    successors = []
    board_dict = state.to_dict() 
    
    for coord, cell in board_dict.items():
        if cell.color == current_player:
            for direction in Direction: # dest safely
                try: dest = coord + direction
                except ValueError: dest = None
                
                # move
                if dest is not None and (dest not in board_dict or board_dict[dest].color == current_player):
                    move_act = MoveAction(coord, direction)
                    new_b = apply_move(board_dict, move_act)
                    if new_b: successors.append((GameState.from_dict(new_b), move_act))
                    
                # eat
                if dest is not None and dest in board_dict and board_dict[dest].color != current_player:
                    if cell.height >= board_dict[dest].height:
                        eat_act = EatAction(coord, direction)
                        new_b = apply_eat(board_dict, eat_act)
                        if new_b: successors.append((GameState.from_dict(new_b), eat_act))
                        
                # cascade
                if cell.height >= 2:
                    cascade_act = CascadeAction(coord, direction)
                    new_b = apply_cascade(board_dict, cascade_act)
                    if new_b: successors.append((GameState.from_dict(new_b), cascade_act))                    
    return successors

def apply_move(board_dict: dict, action: MoveAction):
    dest = action.coord + action.direction
    new_board = board_dict.copy()
    moving_stack = new_board.pop(action.coord)
    
    if dest in new_board: # merge
        existing = new_board[dest]
        new_board[dest] = CellState(moving_stack.color, moving_stack.height + existing.height)
    else: # relocate
        new_board[dest] = moving_stack
    return new_board

def apply_eat(board_dict: dict, action: EatAction):
    dest = action.coord + action.direction
    new_board = board_dict.copy()
    attacker_stack = new_board.pop(action.coord)
    
    new_board[dest] = attacker_stack # replace blue
    return new_board

def apply_cascade(board_dict: dict, action: CascadeAction):
    cascading_stack = board_dict.get(action.coord)
    
    if not cascading_stack or cascading_stack.height < 2:
        return None # height >= 2 can cascade

    new_board = board_dict.copy()
    new_board.pop(action.coord, None)
    h = cascading_stack.height
    color = cascading_stack.color
    direction = action.direction
    step_pos = action.coord # keep track of current position

    for i in range(1, h + 1):
        try:
            step_pos = step_pos + direction
            target_pos = step_pos
        except ValueError: # token falls off the board
            break 
        
        # push stack
        curr = target_pos
        to_push = []
        while curr in new_board: # collect stacks in the cascade direction
            to_push.append((curr, new_board.pop(curr)))
            try:
                curr = curr + direction
            except ValueError:
                break # hit the board edge
                
        for old_pos, stack in reversed(to_push): # move collected stacks one cell further
            try:
                new_pos = old_pos + direction
                new_board[new_pos] = stack
            except ValueError:
                pass
        
        new_board[target_pos] = CellState(color, 1)        
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

    # The render_board() function is handy for debugging. It will print out a
    # board state in a human-readable format. If your terminal supports ANSI
    # codes, set the `ansi` flag to True to print a colour-coded version!
    print(render_board(board, ansi=True))

    # Do some impressive AI stuff here to find the solution...
    # ...
    # ... (your solution goes here!)
    # ...
    
    # TODO: test with BFS to verify basic mechanics and handle simple test cases
    # will be updated to A* with heuristic later
    start_state = GameState.from_dict(board) # starting state
    if start_state.is_goal(): # check blue tokens
        return []

    queue = deque([(start_state, [])])
    visited = {start_state}

    # BFS Loop
    while queue:
        current_state, path = queue.popleft()
        # generate legal moves
        for next_state, action in get_successors(current_state, PlayerColor.RED):
            if next_state not in visited:
                new_path = path + [action]
                if next_state.is_goal(): # check goal state
                    return new_path
                visited.add(next_state)
                queue.append((next_state, new_path))                
    return None

    # Here we're returning "hardcoded" actions as an example of the expected
    # output format. Of course, you should instead return the result of your
    # search algorithm. Remember: if no solution is possible for a given input,
    # return `None` instead of a list.
    #return [
    #        MoveAction(Coord(3, 3), Direction.Down),
    #        EatAction(Coord(4, 3), Direction.Down),
    #]
