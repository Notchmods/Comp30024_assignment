# COMP30024 Artificial Intelligence, Semester 1 2026
# Project Part B: Game Playing Agent

from referee.game import PlayerColor, Coord, Direction, \
    Action, PlaceAction, MoveAction, EatAction, CascadeAction
from dataclasses import dataclass, field

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
        if not red_exists or not blue_exists:
            return True
        
        # threefold repitition
        if self.play_phase_turns > 0:
            current_state_key = (self.board, self.player_to_move)
            # Count how many times this exact board + player combo has happened
            if self.past_states.count(current_state_key) >= 2:
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
            new_past_states = self.past_states + (current_state_key,)
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
        return GameState.from_dict(b)

def get_successors(state: GameState, current_player: PlayerColor):
    board_dict = state.to_dict()
    opponent = PlayerColor.BLUE if current_player == PlayerColor.RED else PlayerColor.RED
    successors = []

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
                        for direction in Direction:
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

    # play phase logic
    eat_moves = []
    cascade_moves = []
    normal_moves = []

    #Check stack and its height in the board
    for coord, (color, height) in state.board:
        if color != current_player:
            continue
        
        #Get each direction that the board is trying to go to.
        for direction in Direction:
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

        # During placement phase (first 8 turns total, 4 per player)
        # TODO: repace with minimax/alpha-beta search
        if self._turn_count < 4:
            match self._color:
                case PlayerColor.RED:
                    print("Testing: RED is playing a PLACE action")
                    return PlaceAction(Coord(0, self._turn_count))
                case PlayerColor.BLUE:
                    print("Testing: BLUE is playing a PLACE action")
                    return PlaceAction(Coord(7, self._turn_count))

        # During play phase
        # Generate successors of state (To be used in minimax)
        successors = get_successors(self.state, self.color)

        #Get the first successor
        best_action=successors[0][1]

        best_val=0

        #Search next state to determine best course of action
        for next_state in successors:
            value=minimax(next_state[0], 2, False, self.color) # depth 2 minimax
            if value>best_val:
                best_val=value
                best_action=next_state[1]
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
            
def evaluation(state: GameState, color: PlayerColor):
    

    #Determine the players and opponents
    if color == PlayerColor.RED:
        opponent=PlayerColor.BLUE
    else:
        opponent=PlayerColor.RED
    
    #Evaluation metrics
    opponent=0

    height=0
    opponent_height=0
    stacks=0
    opponent_stacks=0
    eating_moves=0
    opponent_eat_moves=0
    mobility=0
    opponent_mobility=0
    vulnerable_stacks=0
    opponent_vulnerable=0

    board=state.to_dict()

    #Check every stacks within the board and evaluate based on the metrics
    for coord, (cell_color, stack_height) in state.board:
        if cell_color == color:
            height += stack_height
            stacks += 1
            mobility += len(get_successors(state, color))
            if stack_height >= 2:
                vulnerable_stacks += 1
        else:
            opponent_height += stack_height
            opponent_stacks += 1
            opponent_mobility += len(get_successors(state, opponent))
            if stack_height >= 2:
                opponent_vulnerable += 1

        #Check for mobility and eat opportunities
        for direction in Direction:
            try:
                dest = coord + direction
            except ValueError:
                continue # edge of the board
            
            
            target=board.get(dest)
            
            #For mobility, try to find adjacent squares
            if target is None or target[0]== cell_color:
                if cell_color == color:
                    mobility += 1
                else:
                    opponent_mobility += 1
            
            #For eat opportunities, check if the stack can eat an opponent's stack
            elif target[0]!=cell_color:
                target_color,target_height=target
                if height>target_height and target_color == color:
                    eating_moves += 1
                    opponent_vulnerable += 1
                else:
                    opponent_eat_moves += 1
                    vulnerable_stacks += 1
        
            
        
    score=(
        10*(stack_height-opponent_height)+
        25*(stack_height-opponent_stacks)+
        5*(mobility-opponent_mobility)+
        40*(eating_moves-opponent_eat_moves)-
        30*(vulnerable_stacks-opponent_vulnerable)
    )

    return float(score)

def minimax(state: GameState, depth: int, maximizing_player: bool, agent_color: PlayerColor):
    # a basic minimax search
    successors = get_successors(state, state.player_to_move) # fetch successors
    if state.is_terminal(no_legal_moves=len(successors) == 0): # check if the game is over
        red_exists = any(color == PlayerColor.RED for _, (color, _) in state.board)
        blue_exists = any(color == PlayerColor.BLUE for _, (color, _) in state.board)
        
        # elimination
        if red_exists and not blue_exists:
            return float('inf') if agent_color == PlayerColor.RED else float('-inf')
        elif blue_exists and not red_exists:
            return float('inf') if agent_color == PlayerColor.BLUE else float('-inf')
        
        # draw or turn limit conditions
        if state.play_phase_turns >= 300:
            return evaluation(state, agent_color) 
        else: # stalemate or threefold repetition
            return 0.0 

    if depth == 0: # reach depth limit
        return evaluation(state, agent_color)

    if maximizing_player: # recursive
        max_eval = float('-inf')
        for next_state, _ in successors:
            eval_score = minimax(next_state, depth - 1, False, agent_color)
            max_eval = max(max_eval, eval_score)
        return max_eval
    else:
        min_eval = float('inf')
        for next_state, _ in successors:
            eval_score = minimax(next_state, depth - 1, True, agent_color)
            min_eval = min(min_eval, eval_score)
        return min_eval





                
                

    