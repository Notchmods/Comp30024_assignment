# COMP30024 Artificial Intelligence, Semester 1 2026
# Project Part B: Game Playing Agent

from referee.game import PlayerColor, Coord, Direction, \
    Action, PlaceAction, MoveAction, EatAction, CascadeAction
from dataclasses import dataclass

@dataclass(frozen=True)
class GameState:
    board: frozenset[tuple[Coord, tuple[PlayerColor, int]]] 

    def to_dict(self):
        # convert back to dict
        return dict(self.board)

    @staticmethod
    def from_dict(board_dict: dict[Coord, tuple[PlayerColor, int]]):
        # create state from input
        return GameState(frozenset(board_dict.items()))

    def is_terminal(self):
        # checks if the game has ended via elimination
        red_exists = False
        blue_exists = False
        for _, (color, _) in self.board:
            if color == PlayerColor.RED:
                red_exists = True
            elif color == PlayerColor.BLUE:
                blue_exists = True
            if red_exists and blue_exists:
                return False
        # exit the loop when one of the colors is eliminated
        return True
    
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

def get_successors(state: GameState, current_player: PlayerColor = PlayerColor.RED):
    eat_moves = []
    cascade_moves = []
    normal_moves = []
    board_dict = state.to_dict()

    for coord, (color, height) in state.board:
        if color != current_player:
            continue
        
        for direction in Direction:
            try: 
                dest = coord + direction
            except ValueError:
                continue # edge of the board
            
            target = board_dict.get(dest)
            # move & merge
            if target is None or target[0] == current_player:
                new_b = board_dict.copy()
                GameState.apply_move(new_b, coord, dest, current_player)
                normal_moves.append((GameState.from_dict(new_b), MoveAction(coord, direction)))
                
            # eat
            elif target[0] != current_player and height >= target[1]: # must be an enemy stack, height >= enemy
                new_b = board_dict.copy()
                GameState.apply_eat(new_b, coord, dest)
                eat_moves.append((GameState.from_dict(new_b), EatAction(coord, direction)))
                    
            # cascade
            if height >= 2: # height >= 2
                new_b = board_dict.copy()
                GameState.apply_cascade(new_b, coord, direction, current_player)
                new_fs = frozenset(new_b.items())
                if new_fs != state.board: # add the cascade action only if it changed the board
                    cascade_moves.append((GameState(new_fs), CascadeAction(coord, direction)))                    
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
        if self._turn_count < 4:
            match self._color:
                case PlayerColor.RED:
                    print("Testing: RED is playing a PLACE action")
                    return PlaceAction(Coord(0, self._turn_count))
                case PlayerColor.BLUE:
                    print("Testing: BLUE is playing a PLACE action")
                    return PlaceAction(Coord(7, self._turn_count))

        # During play phase
        # Generate sucessors of state (To be used in minmax)
        successors= get_successors(self.state,self.color)

        #pick a random move
        next_state,action=successors[0]

        return action

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