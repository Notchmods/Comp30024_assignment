# COMP30024 Artificial Intelligence, Semester 1 2026
# Project Part A: Single Player Cascade

from .core import CellState, Coord, Direction, Action, MoveAction, EatAction, CascadeAction, PlayerColor
from .utils import render_board
from dataclasses import dataclass
import heapq
from itertools import count

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
    
    for coord, cell in state.board:
        if cell.color == current_player:
            for direction in Direction: # dest in board
                try: 
                    dest = coord + direction
                except ValueError: 
                    continue
                
                target = board_dict.get(dest)

                # move & merge
                if target is None or target.color == current_player:
                    new_b = board_dict.copy()
                    del new_b[coord]
                    if target: # merge
                        new_b[dest] = CellState(current_player, cell.height + target.height)
                    else: # relocate
                        new_b[dest] = cell
                    successors.append((GameState.from_dict(new_b), MoveAction(coord, direction)))
                    
                # eat
                elif target.color != current_player:
                    if cell.height >= target.height:
                        new_b = board_dict.copy()
                        del new_b[coord]
                        new_b[dest] = cell # replace blue
                        successors.append((GameState.from_dict(new_b), EatAction(coord, direction)))
                        
                # cascade
                if cell.height >= 2:
                     # check if cascade help to reach blue
                    hit_something = False
                    curr_scan = coord
                    for _ in range(cell.height):
                        try: curr_scan = curr_scan + direction
                        except ValueError: break
                        if curr_scan in board_dict:
                            hit_something = True
                            break
                    
                    if hit_something:
                        new_b = board_dict.copy()
                        del new_b[coord]
                        step_pos = coord # keep track of current position

                        for _ in range(cell.height):
                            try: step_pos = step_pos + direction
                            except ValueError: break 
                            
                            # push stack
                            curr = step_pos
                            to_push = []
                            while curr in new_b: # collect stacks in the cascade direction
                                to_push.append((curr, new_b.pop(curr)))
                                try: curr = curr + direction
                                except ValueError: break # hit the board edge
                                    
                            for old_pos, stack in reversed(to_push): # move collected stacks one cell further
                                try:
                                    new_pos = old_pos + direction
                                    new_b[new_pos] = stack
                                except ValueError: pass
                            new_b[step_pos] = CellState(current_player, 1)        
                        
                        # add cascade action as a succesor if valid and changes the board
                        new_fs = frozenset(new_b.items())
                        if new_fs != state.board:
                            successors.append((GameState(new_fs), CascadeAction(coord, direction)))                    
    return successors

def search(
    board: dict[Coord, CellState]
) -> list[Action] | None:
    #A* search algorithm- With a combined heuristic of max-min travel distance and independent targets
    start_state = GameState.from_dict(board) # starting state
    if start_state.is_goal(): # check blue tokens
        return []

    pq=[] #Use a priority queue instead (Min-heap edition)
    tie=count() #5Tie breaker to avoid comparison issues when total costs are equal
    came_from = {}

    #Cheapest known path cost
    best_g={start_state:0}

    #Heap items
    h, b_count = Heuristics(start_state) # Get the heuristics for the start state
    #heap consists of (f(n), blue_count, h(n), tie_breaker ,g(n), state)
    heapq.heappush(pq, (h, b_count, h, next(tie), 0, start_state))

    #While there are still items within queue
    while pq:
        f, b_left, h_val, ti, g, current_state = heapq.heappop(pq)

        #If path costs > best path cost then ignore this state
        if g>best_g.get(current_state,float("inf")):
            continue

        #If the state is in the goal state then return the solutions
        if current_state.is_goal():
            return reconstruct_path(came_from, current_state)
        
        #Iterate through successor states
        for next_state,action in get_successors(current_state,PlayerColor.RED):
            #Each action has cost of 1, so g(n)/ path cost increases by 1 
            new_g=g+1

            #If new path cost is less than best path cost
            if new_g < best_g.get(next_state,float("inf")):
                new_h, new_b_left = Heuristics(next_state)
                if new_h == float('inf'):
                    continue # prune dead ends

                #Select this state
                best_g[next_state]=new_g
                #Extend action sequence
                came_from[next_state] = (current_state, action)
                
                # prioritize clearing blues when f costs are tied
                #f(n)=g(n)+h(n)
                heapq.heappush(pq, (new_g + new_h, new_b_left, new_h, next(tie), new_g, next_state))

    return  None

def Heuristics(state: GameState):
    reds = []
    blues = []
    for coord, cell in state.board:
        if cell.color == PlayerColor.RED:
            reds.append((coord, cell.height))
        else:
            blues.append(coord)
    #  prune dead ends
    if not blues: return 0, 0
    if not reds: return float('inf'), len(blues) 
        
    # find the minimum distance required to reach the furthest blue stack
    max_min_moves = 0
    for b in blues:
        best_r_moves = float('inf')
        for r_coord, r_height in reds:
            dist = abs(r_coord.r - b.r) + abs(r_coord.c - b.c)
            moves = (dist + r_height - 1)//r_height # divide by height to ensure cascade speed never overestimated
            if moves < best_r_moves:
                best_r_moves = moves
        if best_r_moves > max_min_moves:
            max_min_moves = best_r_moves
            
    # find how many blue exist that share no rows or columns
    used_rows, used_cols = set(), set()
    indep_blues = 0
    for b in blues:
        if b.r not in used_rows and b.c not in used_cols:
            indep_blues += 1
            used_rows.add(b.r)
            used_cols.add(b.c)
    # true cost includes at least travel distance or destruction actions
    return max(max_min_moves, indep_blues), len(blues)

def reconstruct_path(came_from, current_state):
    path = []
    while current_state in came_from:
        current_state, action = came_from[current_state]
        path.append(action)
    return path[::-1] # reverse the path to return actions in the correct chronological order