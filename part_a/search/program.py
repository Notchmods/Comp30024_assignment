# COMP30024 Artificial Intelligence, Semester 1 2026
# Project Part A: Single Player Cascade

from .core import CellState, Coord, Direction, Action, MoveAction, EatAction, CascadeAction, PlayerColor
from .utils import render_board
from dataclasses import dataclass
from collections import deque
import heapq
from itertools import count
import time

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
    board_dict = dict(state.board) 
    
    for coord, cell in state.board:
        if cell.color == current_player:
            for direction in Direction: # dest safely
                try: dest = coord + direction
                except ValueError: continue
                
                # move
                if dest not in board_dict or board_dict[dest].color == current_player:
                    new_b = apply_move(board_dict, coord, dest) #New board state
                    move_act = MoveAction(coord, direction)
                    successors.append((GameState(frozenset(new_b.items())), move_act))
                    
                # eat
                elif board_dict[dest].color != current_player:
                    if cell.height >= board_dict[dest].height:
                        new_b = apply_eat(board_dict, coord, dest)
                        eat_act = EatAction(coord, direction)
                        successors.append((GameState(frozenset(new_b.items())), eat_act))
                        
                # Cascade
                if cell.height >= 2 and blue_checks(board_dict,coord,direction,cell.height):
                    new_b = apply_cascade(board_dict, coord, direction, cell.height, cell.color) # type: ignore

                    #Only add cascade action as a succesor if it's valid and changes theb oard
                    if new_b is not None and new_b!=board_dict:
                        cascade_act = CascadeAction(coord, direction)
                        successors.append((GameState(frozenset(new_b.items())), cascade_act))                    
    return successors

#Check if Cascade might help to reach blue stacks 
def blue_checks(board_dict, coord, direction, height):
    curr = coord #Red stack's current positions

    #Check for blue stack within the stack height
    for _ in range(height):
        try:
            curr = curr + direction #Step forward
        except ValueError:
            return False
        #Check whether the square that it cascades to contain blue stacks   
        if curr in board_dict and board_dict[curr].color == PlayerColor.BLUE:
            return True
    return False #Return if there's no blue square found

def apply_move(board_dict: dict, coord: Coord, dest: Coord):
    new_board = board_dict.copy()
    moving_stack = new_board.pop(coord)
    
    if dest in new_board: # merge
        existing = new_board[dest]
        new_board[dest] = CellState(moving_stack.color, moving_stack.height + existing.height)
    else: # relocate
        new_board[dest] = moving_stack
    return new_board

def apply_eat(board_dict: dict, coord: Coord, dest: Coord):
    new_board = board_dict.copy()
    attacker_stack = new_board.pop(coord)    
    new_board[dest] = attacker_stack # replace blue
    return new_board

def apply_cascade(board_dict: dict, coord: Coord, direction: Direction, height: int, color: PlayerColor):   

    new_board = board_dict.copy()
    del new_board[coord]
    step_pos = coord # keep track of current position

    for _ in range(height):
        try:
            step_pos = step_pos + direction
        except ValueError: # token falls off the board
            break 
        
        # push stack
        curr = step_pos
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
        
        new_board[step_pos] = CellState(color, 1)        
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

    #A* search algorithm- With distance to blue stack as heuristics

    #Calculate Heuristic




    start_state = GameState.from_dict(board) # starting state
    if start_state.is_goal(): # check blue tokens
        return []
    

    pq=[] #Use a priority queue instead (Min-heap edition)
    tie=count() #5Tie breaker to avoid comparison issues when total costs are equal
    came_from = {}

    #Cheapest known path cost
    best_g={start_state:0}

    #Heap items
    start_h= Heuristics(start_state) #Get the heuristics for the start state
    #heap consists of (f(n), tie_breaker ,g(n) , state, path)
    heapq.heappush(pq,(start_h,next(tie),0,start_state))

    # DEBUG
    start_time = time.time()
    nodes_expanded = 0

    #While there are still items within queue
    while pq:
        f,ti,g,current_state = heapq.heappop(pq)

        #If path costs > best path cost then ignore this state
        if g>best_g.get(current_state,float("inf")):
            continue
        
        # DEBUG
        nodes_expanded += 1

        #If the state is in the goal state then return the solutions
        if current_state.is_goal():
            
            # DEBUG (Time taken and node expanded+ number of moves made)
            end_time = time.time()
            print(f"Time taken: {end_time - start_time:.4f} seconds")
            print(f"Nodes expanded: {nodes_expanded}")
            print(f"Solution length: {len(reconstruct_path(came_from, current_state))} moves\n")

            return reconstruct_path(came_from, current_state)
        
        #Iterate through successor states
        for next_state,action in get_successors(current_state,PlayerColor.RED):
            #Each action has cost of 1, so g(n)/ path cost increases by 1 
            new_g=g+1

            #If new path cost is less than best path cost
            if new_g < best_g.get(next_state,float("inf")):
                #Select this state
                best_g[next_state]=new_g
                #Extend action sequence
                came_from[next_state] = (current_state, action)

                #f(n)=g(n)+h(n)
                new_f = new_g+ Heuristics(next_state)
                heapq.heappush(pq,(new_f,next(tie),new_g,next_state))
    
    # DEBUG
    end_time = time.time()
    print(f"\nSEARCH FAILED")
    print(f"Time taken: {end_time - start_time:.4f} seconds")
    print(f"Nodes expanded: {nodes_expanded}\n")

    return  None

#Manhattan distance calculator 
def Manhattan_Distance(reds,blues):
    return abs(reds.r - blues.r)+abs(reds.c-blues.c)
    
def Heuristics(state):
    # iterate directly on frozenset
    reds = [coord for coord, cell in state.board if cell.color == PlayerColor.RED]
    blues = [coord for coord, cell in state.board if cell.color == PlayerColor.BLUE]
    if not blues or not reds:
        return 0
    
    # find the minimum distance required to reach the furthest blue stack
    max_min_dist = 0
    for blue in blues:
        dist_to_closest_red = min(Manhattan_Distance(red, blue) for red in reds)
        if dist_to_closest_red > max_min_dist:
            max_min_dist = dist_to_closest_red        
    return max_min_dist

def reconstruct_path(came_from, current_state):
    path = []
    while current_state in came_from:
        current_state, action = came_from[current_state]
        path.append(action)
    return path[::-1] # reverse it to get start -> goal