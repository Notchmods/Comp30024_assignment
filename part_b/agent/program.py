# COMP30024 Artificial Intelligence, Semester 1 2026
# Project Part B: Game Playing Agent

from referee.game import PlayerColor, Coord, Direction, \
    Action, PlaceAction, MoveAction, EatAction, CascadeAction
from dataclasses import dataclass, field
import time
import math

@dataclass(frozen=True)
class GameState:
    board: frozenset[tuple[Coord, tuple[PlayerColor, int]]]
    player_to_move: PlayerColor = PlayerColor.RED
    total_turn_count: int = 0
    play_phase_turns: int = 0
    # stores tuples of (board, player_to_move) for threefold
    past_states: tuple[tuple[frozenset, PlayerColor], ...] = field(default_factory=tuple)

    def to_dict(self):
        # convert back to dict
        return dict(self.board)

    @staticmethod
    def from_dict(board_dict: dict[Coord, tuple[PlayerColor, int]]):
        # create state from input
        return GameState(frozenset(board_dict.items()))

    def is_terminal(self, no_legal_moves: bool = False): # checks the game ending conditions
        # elimination
        red_exists = any(color == PlayerColor.RED for _, (color, _) in self.board)
        blue_exists = any(color == PlayerColor.BLUE for _, (color, _) in self.board)
        if self.total_turn_count>=8:
            if not red_exists or not blue_exists:
                return True
        
        # threefold repitition
        if self.play_phase_turns > 0:
            current_state_key = (self.board, self.player_to_move)
            past_dict=dict(self.past_states)

            # Count how many times this exact board + player combo has happened
            if past_dict.get(current_state_key,0) >= 2:
                return True
        
        # stalemate
        if no_legal_moves:
            return True
        
        # turn limit
        if self.play_phase_turns >= 300:
            return True
        return False
    
    def generate_next_state(self, new_board_dict: dict, next_player: PlayerColor):
        # create the next GameState with updated counters and history
        new_board_frozenset = frozenset(new_board_dict.items())
        # calculate new turn counters
        new_total_turns = self.total_turn_count + 1
        new_play_turns = self.play_phase_turns + 1 if new_total_turns > 8 else 0

        # update history
        new_past_states = self.past_states
        if new_play_turns > 0:
            current_state_key = (self.board, self.player_to_move)
            past_dict = dict(self.past_states)
            past_dict[current_state_key] = past_dict.get(current_state_key, 0) + 1
            new_past_states = tuple(past_dict.items())
        return GameState(
            board=new_board_frozenset,
            player_to_move=next_player,
            total_turn_count=new_total_turns,
            play_phase_turns=new_play_turns,
            past_states=new_past_states
        )
    
    @staticmethod
    def apply_move(b: dict, src: Coord, dest: Coord, color: PlayerColor):
        stack = b.pop(src)
        if dest in b:
            b[dest] = (color, stack[1] + b[dest][1]) # merge
        else:
            b[dest] = stack # relocate

    @staticmethod
    def apply_eat(b: dict, src: Coord, dest: Coord):
        b[dest] = b.pop(src) # eat

    @staticmethod
    def apply_cascade(b: dict, src: Coord, direction: Direction, color: PlayerColor):
        _, height = b.pop(src)
        step = src
        for _ in range(height):
            try: 
                step = step + direction
            except ValueError: 
                break 
            
            curr = step
            to_push = []
            # collect all stacks in the way
            while curr in b:
                to_push.append((curr, b.pop(curr)))
                try: curr = curr + direction
                except ValueError: break 
                
            # push
            for old_pos, stack in reversed(to_push):
                try: b[old_pos + direction] = stack
                except ValueError: pass 
            b[step] = (color, 1)

    def apply_action(self, color: PlayerColor, action: Action):
        # used by update() to track the real game
        b = self.to_dict()
        match action:
            case PlaceAction(coord):
                b[coord] = (color, 3)
            case MoveAction(coord, direction):
                self.apply_move(b, coord, coord + direction, color)
            case EatAction(coord, direction):
                self.apply_eat(b, coord, coord + direction)
            case CascadeAction(coord, direction):
                self.apply_cascade(b, coord, direction, color)
        next_player = PlayerColor.BLUE if color == PlayerColor.RED else PlayerColor.RED
        return self.generate_next_state(b, next_player)

def get_successors(state: GameState, current_player: PlayerColor):
    board_dict = state.to_dict()
    opponent = PlayerColor.BLUE if current_player == PlayerColor.RED else PlayerColor.RED
    successors = []

    # play phase logic
    eat_moves = []
    cascade_moves = []
    normal_moves = []

    # placement phase logic
    if state.total_turn_count < 8:
        # precalculate opponent coordinates for adjacency checks
        opponent_coords = {coord for coord, (color, _) in state.board if color == opponent}
        for r in range(8):
            for c in range(8):
                coord = Coord(r, c)
                if coord not in board_dict: # place on an empty cell
                    is_valid = True
                    
                    # adjacency restriction apply after the first turn of the game
                    if state.total_turn_count > 0:
                        for direction in (Direction.Up, Direction.Down, Direction.Left, Direction.Right):
                            try:
                                adj_coord = coord + direction
                                if adj_coord in opponent_coords:
                                    is_valid = False
                                    break
                            except ValueError:
                                pass # edge of the board
                    if is_valid:
                        new_b = board_dict.copy()
                        new_b[coord] = (current_player, 3) # place a stack of height 3
                        # generate next state
                        next_state = state.generate_next_state(new_b, opponent)
                        successors.append((next_state, PlaceAction(coord)))
        return successors

    #Check stack and its height in the board
    for coord, (color, height) in state.board:
        if color != current_player:
            continue
        
        #Get each direction that the board is trying to go to.
        for direction in (Direction.Up, Direction.Down, Direction.Left, Direction.Right):
            try: 
                #Calculate destination
                dest = coord + direction
            except ValueError:
                continue # edge of the board
            
            target = board_dict.get(dest)
            # move & merge
            if target is None or target[0] == current_player:
                new_b = board_dict.copy()
                GameState.apply_move(new_b, coord, dest, current_player)
                next_state = state.generate_next_state(new_b, opponent)
                normal_moves.append((next_state, MoveAction(coord, direction)))
                
            # eat
            elif target[0] != current_player and height >= target[1]: # must be an enemy stack, height >= enemy
                new_b = board_dict.copy()
                GameState.apply_eat(new_b, coord, dest)
                next_state = state.generate_next_state(new_b, opponent)
                eat_moves.append((next_state, EatAction(coord, direction)))
                    
            # cascade
            if height >= 2: # height >= 2
                new_b = board_dict.copy()
                GameState.apply_cascade(new_b, coord, direction, current_player)
                if new_b != board_dict: 
                    next_state = state.generate_next_state(new_b, opponent)
                    cascade_moves.append((next_state, CascadeAction(coord, direction)))                    
    # return in order for alpha-beta pruning
    return eat_moves + cascade_moves + normal_moves

class Agent:
    """
    This class is the "entry point" for your agent, providing an interface to
    respond to various Cascade game events.
    """

    def __init__(self, color: PlayerColor, **referee: dict):
        """
        This constructor method runs when the referee instantiates the agent.
        Any setup and/or precomputation should be done here.
        """
        self._color = color
        self._turn_count = 0
        self.time_used = 0.0
        match color:
            case PlayerColor.RED:
                print("Testing: I am playing as RED (first player)")
            case PlayerColor.BLUE:
                print("Testing: I am playing as BLUE")
        
        #Store board state and players color
        self.color=color #Player's color
        
        #Store opponent's color
        if(self.color==PlayerColor.BLUE): 
            self.opponent=PlayerColor.RED
        elif(self.color==PlayerColor.RED):
            self.opponent=PlayerColor.BLUE


        #Initialise game state
        self.state = GameState(frozenset())

    def action(self, **referee: dict) -> Action:
        """
        This method is called by the referee each time it is the agent's turn
        to take an action. It must always return an action object.
        """

        # Below we have hardcoded actions to be played depending on whether
        # the agent is playing as BLUE or RED. Obviously this won't work beyond
        # the initial moves of the game, so you should use some game playing
        # technique(s) to determine the best action to take.
        TIME_LIMIT=1.0 #Lower limit 

        turn_start_time = time.time()

        #Clear transposition table to save memory
        transposition_table.clear() 

        # During placement phase
        successors = get_successors(self.state, self.color)
        if not successors:
            raise ValueError("Stalemate: No legal moves available")
        
        # search game tree to find the best legal move
        SEARCH_DEPTH = 1
        while True:
            elapsed_time = time.time() - turn_start_time
            if elapsed_time >= TIME_LIMIT:
                break
        
            score, action = minimax(self.state, SEARCH_DEPTH, float('-inf'), float('inf'), True, self.color,
                                     deadline=turn_start_time + TIME_LIMIT)
            # Callback if every move leads to a forced loss
            if action is not None: 
                best_action = action #Get the first successor

            #If we find a winning move, stop searching
            if score in (float('inf'), float('-inf')):
                break
        
            SEARCH_DEPTH+=1
        
        turn_end_time = time.time()
        elapsed_time = turn_end_time - turn_start_time
        self.time_used += elapsed_time
        print(f"[{self.color}] Turn {self._turn_count} took {elapsed_time:.3f}s (Total time used: {self.time_used:.3f}s)")
        return best_action

    def update(self, color: PlayerColor, action: Action, **referee: dict):
        """
        This method is called by the referee after a player has taken their
        turn. You should use it to update the agent's internal game state.
        """
        if color == self._color:
            self._turn_count += 1

        #Update game state
        self.state = self.state.apply_action(color,action)

        # There are four possible action types: PLACE, MOVE, EAT, and CASCADE.
        # Below we check which type of action was played and print out the
        # details of the action for demonstration purposes. You should replace
        # this with your own logic to update your agent's internal game state.
        match action:
            case PlaceAction(coord):
                print(f"Testing: {color} played PLACE action at {coord}")
            case MoveAction(coord, direction):
                print(f"Testing: {color} played MOVE action:")
                print(f"  Coord: {coord}")
                print(f"  Direction: {direction}")
            case EatAction(coord, direction):
                print(f"Testing: {color} played EAT action:")
                print(f"  Coord: {coord}")
                print(f"  Direction: {direction}")
            case CascadeAction(coord, direction):
                print(f"Testing: {color} played CASCADE action:")
                print(f"  Coord: {coord}")
                print(f"  Direction: {direction}")
            case _:
                raise ValueError(f"Unknown action type: {action}")

#Greedy Weighted evaluation
def evaluation(state: GameState, color: PlayerColor):

    #Determine the players and opponents
    if color == PlayerColor.RED:
        opponent=PlayerColor.BLUE
    else:
        opponent=PlayerColor.RED
    
    #Evaluation metrics
    height,opponent_height=0,0
    scores,opponent_scores=0,0
    eating_moves,opponent_eat_moves=0,0
    vulnerable_stacks,opponent_vulnerable=0,0

    #Store board state
    board=state.to_dict() 

    #Check every stacks within the board and evaluate based on the metrics
    for coord, (cell_color, stack_height) in state.board:
        #Count total stack height and number of stacks  for each player
        if cell_color == color:
            height += stack_height
            scores+=1
        else:
            opponent_height += stack_height
            opponent_scores += 1

        #Check mobility by counting adjacent empty of friendly cells
        for direction in (Direction.Up, Direction.Down, Direction.Left, Direction.Right):
            try:
                dest = coord + direction
            except ValueError:
                continue # edge of the board
            
            
            target=board.get(dest)
            
            if target is None:
                continue
                
            target_color, target_height = target

            if target!=cell_color and stack_height>=target_height:
                if target_color==color:
                    eating_moves+=target_height
                    opponent_vulnerable+=target_height
                else:
                    opponent_eat_moves+=target_height
                    vulnerable_stacks+=target_height
 
    #Calculate the final score based on the evaluation metrics with assigned weights (TBD)
    MATERIAL_WEIGHT=15
    POSITIONAL_WEIGHT=1
    CAPTURE_WEIGHT=35
    THREAT_PENALTY=12
    score=(
        MATERIAL_WEIGHT*(height-opponent_height)+
        POSITIONAL_WEIGHT*(scores-opponent_scores)+
        CAPTURE_WEIGHT*(eating_moves-opponent_eat_moves)-
        THREAT_PENALTY*(vulnerable_stacks-opponent_vulnerable)
    )

    return float(score)

#Memoization table storing previously evaluated state
transposition_table={} 


def minimax(state: GameState, depth: int, alpha: float, beta: float, maximizing_player: bool, 
            agent_color: PlayerColor,deadline=None):

     #If time has ran out bail the game out
    if deadline and time.time()>=deadline:
        return evaluation(state, agent_color), None
    
    # a minimax search with alpha-beta pruning
    if depth == 0: # depth limit check to avoid expensive successor generation at leaf nodes
        return evaluation(state, agent_color), None

    key=(state.board, state.player_to_move,depth)

    if key in transposition_table:
        return transposition_table[key]
   
    successors = get_successors(state, state.player_to_move) # fetch successors
    if state.is_terminal(no_legal_moves=len(successors) == 0): # check if the game is over
        red_exists = any(color == PlayerColor.RED for _, (color, _) in state.board)
        blue_exists = any(color == PlayerColor.BLUE for _, (color, _) in state.board)
        
        # elimination
        if red_exists and not blue_exists:
            return (float('inf') if agent_color == PlayerColor.RED else float('-inf')), None
        elif blue_exists and not red_exists:
            return (float('inf') if agent_color == PlayerColor.BLUE else float('-inf')), None
        
        # draw or turn limit conditions
        if state.play_phase_turns >= 300:
            return evaluation(state, agent_color), None 
        else: # stalemate or threefold repetition
            return 0.0, None 

    best_action = successors[0][1]
    if maximizing_player: # recursive alpha-beta search
        max_eval = float('-inf')
        for next_state, action in successors:
            eval_score, _ = minimax(next_state, depth - 1, alpha, beta, False, agent_color,deadline)
            if eval_score > max_eval:
                max_eval = eval_score
                best_action = action
            
            alpha = max(alpha, eval_score)
            if beta <= alpha: # beta cutoff
                break
        transposition_table[key] = (max_eval, best_action)
        return max_eval, best_action
        
    else:
        min_eval = float('inf')
        for next_state, action in successors:
            eval_score, _ = minimax(next_state, depth - 1, alpha, beta, True, agent_color,deadline)
            if eval_score < min_eval:
                min_eval = eval_score
                best_action = action
                
            beta = min(beta, eval_score)
            if beta <= alpha: # alpha cutoff
                break
    
    transposition_table[key]=(min_eval, best_action)

    return min_eval, best_action