# COMP30024 Artificial Intelligence, Semester 1 2026
# Project Part B: Game Playing Agent

from referee.game import PlayerColor, Coord, Direction, \
    Action, PlaceAction, MoveAction, EatAction, CascadeAction
import time
import random

class TimeoutException(Exception):
    pass

# a static heatmap values the center of the board highly and penalizes the edges
POSITION_WEIGHTS = [
    [ 0,  1,  2,  2,  2,  2,  1,  0],
    [ 1,  3,  4,  4,  4,  4,  3,  1],
    [ 2,  4,  6,  8,  8,  6,  4,  2],
    [ 2,  4,  8, 10, 10,  8,  4,  2],
    [ 2,  4,  8, 10, 10,  8,  4,  2],
    [ 2,  4,  6,  8,  8,  6,  4,  2],
    [ 1,  3,  4,  4,  4,  4,  3,  1],
    [ 0,  1,  2,  2,  2,  2,  1,  0]
]

POSITION_BY_COORD = {
    Coord(r, c): POSITION_WEIGHTS[r][c]
    for r in range(8)
    for c in range(8)
}

# maps a Coord to a list of valid (Direction, adjacent_Coord) tuples
VALID_ADJACENT = {}
for r in range(8):
    for c in range(8):
        coord = Coord(r, c)
        VALID_ADJACENT[coord] = []
        for d in (Direction.Up, Direction.Down, Direction.Left, Direction.Right):
            try:
                dest = coord + d
                VALID_ADJACENT[coord].append((d, dest))
            except ValueError:
                pass

# transposition table with zobrist hashing
ZOBRIST_RANDOM = random.Random(30024)
MAX_ZOBRIST_HEIGHT = 32
MAX_TRANSPOSITION_ENTRIES = 50_000
EXACT, LOWER_BOUND, UPPER_BOUND = 0, 1, 2
WIN_SCORE = 100000.0
ZOBRIST_STACK = {
    (Coord(r, c), color, height): ZOBRIST_RANDOM.getrandbits(64)
    for r in range(8)
    for c in range(8)
    for color in (PlayerColor.RED, PlayerColor.BLUE)
    for height in range(1, MAX_ZOBRIST_HEIGHT + 1)
}
ZOBRIST_TURN = {
    PlayerColor.RED: ZOBRIST_RANDOM.getrandbits(64),
    PlayerColor.BLUE: ZOBRIST_RANDOM.getrandbits(64),
}
ZOBRIST_OVERFLOW = ZOBRIST_RANDOM.getrandbits(64)
TRANSPOSITION_TABLE = {}

def zobrist_hash(state):
    h = ZOBRIST_TURN[state.player_to_move]
    for coord, (color, height) in state.board.items():
        if 1 <= height <= MAX_ZOBRIST_HEIGHT:
            h ^= ZOBRIST_STACK[(coord, color, height)]
        else:
            # This should not occur in normal Cascade play, but keeps hashing
            # deterministic if an unusual merged stack ever appears.
            h ^= ZOBRIST_OVERFLOW ^ (
                (coord.r + 1) * 1_000_003 ^
                (coord.c + 1) * 97_409 ^
                (color.value + 1) * 65_537 ^
                height * 257
            )
    return h

def current_repetition_count(state):
    if state.play_phase_turns <= 0:
        return 0
    state_key = (frozenset(state.board.items()), state.player_to_move)
    return state.history.get(state_key, 0)

def transposition_key(state, agent_color):
    h = zobrist_hash(state)
    is_placement = state.total_turn_count < 8
    turn_limit_risk = state.play_phase_turns if state.play_phase_turns > 280 else 0
    return (h, agent_color, is_placement, turn_limit_risk)

class GameState:
    def __init__(self, board: dict, player_to_move: PlayerColor = PlayerColor.RED, total_turn_count: int = 0, play_phase_turns: int = 0, history: dict = None):
        self.board = board  # standard dictionary: {Coord: (PlayerColor, height)}
        self.player_to_move = player_to_move
        self.total_turn_count = total_turn_count
        self.play_phase_turns = play_phase_turns
        self.history = history if history is not None else {}

    def is_terminal(self, no_legal_moves: bool = False):
        # elimination
        if self.total_turn_count >= 8:
            red_exists = any(color == PlayerColor.RED for color, _ in self.board.values())
            blue_exists = any(color == PlayerColor.BLUE for color, _ in self.board.values())
            if not red_exists or not blue_exists:
                return True
        
        # threefold repetition
        if self.play_phase_turns > 0:
            board_hash = frozenset(self.board.items())
            state_key = (board_hash, self.player_to_move)
            if self.history.get(state_key, 0) >= 2:
                return True
        
        # stalemate
        if no_legal_moves:
            return True
        
        # turn limit
        if self.play_phase_turns >= 300:
            return True
        return False
    
    def generate_next_state(self, new_board_dict: dict, next_player: PlayerColor):
        new_total_turns = self.total_turn_count + 1
        new_play_turns = self.play_phase_turns + 1 if new_total_turns > 8 else 0

        new_history = self.history.copy()
        if new_play_turns > 0:
            board_hash = frozenset(new_board_dict.items())
            state_key = (board_hash, next_player)
            new_history[state_key] = new_history.get(state_key, 0) + 1

        return GameState(
            board=new_board_dict,
            player_to_move=next_player,
            total_turn_count=new_total_turns,
            play_phase_turns=new_play_turns,
            history=new_history
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
        b = self.board.copy()
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
    board_dict = state.board
    opponent = PlayerColor.BLUE if current_player == PlayerColor.RED else PlayerColor.RED
    successors = []

    # placement phase logic
    if state.total_turn_count < 8:
        opponent_coords = {coord for coord, (color, _) in board_dict.items() if color == opponent}
        for r in range(8):
            for c in range(8):
                coord = Coord(r, c)
                if coord not in board_dict:
                    is_valid = True
                    if state.total_turn_count > 0:
                        for _, adj_coord in VALID_ADJACENT[coord]:
                            if adj_coord in opponent_coords:
                                is_valid = False
                                break
                    if is_valid:
                        new_b = board_dict.copy()
                        new_b[coord] = (current_player, 3)
                        next_state = state.generate_next_state(new_b, opponent)
                        successors.append((next_state, PlaceAction(coord)))
        return successors

    # play phase logic
    eat_moves = []
    cascade_moves = []
    normal_moves = []

    for coord, (color, height) in board_dict.items():
        if color != current_player:
            continue
        
        for direction, dest in VALID_ADJACENT[coord]:
            target = board_dict.get(dest)            
            # move & merge
            if target is None or target[0] == current_player:
                new_b = board_dict.copy()
                GameState.apply_move(new_b, coord, dest, current_player)
                next_state = state.generate_next_state(new_b, opponent)
                normal_moves.append((next_state, MoveAction(coord, direction)))
                
            # eat
            elif target[0] != current_player and height >= target[1]:
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
    def __init__(self, color: PlayerColor, **referee: dict):
        self.color = color
        self.opponent = PlayerColor.BLUE if color == PlayerColor.RED else PlayerColor.RED
        self._turn_count = 0
        self.time_used = 0.0
        print(f"Testing: I am playing as {self.color.name}")
        self.state = GameState({}) # initialize with empty dict

    def action(self, **referee: dict) -> Action:
        turn_start_time = time.process_time()
        time_rem = referee.get("time_remaining")
        space_rem = referee.get("space_remaining")
        space_limit = referee.get("space_limit")

        # calculate memory & time
        if space_limit is not None and space_rem is not None:
            mem_spent = f"{space_limit - space_rem:.2f}MB"
            mem_rem = f"{space_rem:.2f}MB"
        else:
            mem_spent = "N/A"
            mem_rem = "N/A"
        if time_rem is None:
            time_rem = max(0.0, 180.0 - self.time_used)
        time_rem_str = f"{time_rem:.3f}s" if time_rem is not None else "N/A"

        successors = get_successors(self.state, self.color)
        if not successors:
            raise ValueError("Stalemate: No legal moves available")
        
        TRANSPOSITION_TABLE.clear()
        TURN_TIME_LIMIT = max(0.1, min(2.0, time_rem*0.05)) # time management
        end_time = turn_start_time + TURN_TIME_LIMIT
        best_action = successors[0][1]
        best_score = 0.0  # track the score of the depth
        current_depth = 1
        
        try: # iterative deepening loop
            while True:
                score, current_best_action = minimax(self.state, current_depth, float('-inf'), float('inf'), True, self.color, end_time)
                if current_best_action is not None: # lock in the best move & score
                    best_action = current_best_action
                    best_score = score
                if score >= WIN_SCORE - 1000 or score <= -WIN_SCORE + 1000:
                    break
                current_depth += 1

        except TimeoutException:
            pass
        
        turn_end_time = time.process_time()
        elapsed_time = turn_end_time - turn_start_time
        self.time_used += elapsed_time
        final_depth = current_depth - 1 if current_depth > 1 else 1
        print(f"[{self.color.name} Turn {self._turn_count}] "
              f"Depth: {final_depth} | Score: {best_score} | "
              f"Time Spent: {elapsed_time:.3f}s | Time Rem: {time_rem_str} | "
              f"Mem Spent: {mem_spent} | Mem Rem: {mem_rem}")
        return best_action

    def update(self, color: PlayerColor, action: Action, **referee: dict):
        if color == self.color:
            self._turn_count += 1
        # update internal board with the moves
        self.state = self.state.apply_action(color, action)

MATERIAL_WEIGHT = 15.0
POSITION_WEIGHT = 1.0
THREAT_PENALTY = 8.0
ATTACK_BONUS = 4.0
def evaluation(state: GameState, color: PlayerColor):
    opponent = PlayerColor.BLUE if color == PlayerColor.RED else PlayerColor.RED
    my_material = opp_material = 0
    my_pos_score = opp_pos_score = 0.0
    attack_score = 0.0
    board = state.board
    is_play_phase = state.total_turn_count >= 8
    for coord, (piece_color, height) in board.items():
        effective_height = min(height, 5)
        position_value = POSITION_BY_COORD[coord] * effective_height
        if piece_color == color:
            my_material += height
            my_pos_score += position_value
            if not is_play_phase:
                continue
            for _, adj_coord in VALID_ADJACENT[coord]:
                adj_piece = board.get(adj_coord)
                if adj_piece is not None and adj_piece[0] == opponent and adj_piece[1] >= height:
                    my_pos_score -= height * THREAT_PENALTY
                    break
        else:
            opp_material += height
            opp_pos_score += position_value
            if not is_play_phase:
                continue
            for _, adj_coord in VALID_ADJACENT[coord]:
                adj_piece = board.get(adj_coord)
                if adj_piece is not None and adj_piece[0] == color and adj_piece[1] >= height:
                    attack_score += height
                    break

    if state.total_turn_count < 8:
        score = (
            MATERIAL_WEIGHT * (my_material - opp_material) +
            POSITION_WEIGHT * (my_pos_score - opp_pos_score)
        )
    else:
        score = (
            MATERIAL_WEIGHT * (my_material - opp_material) +
            POSITION_WEIGHT * (my_pos_score - opp_pos_score) +
            ATTACK_BONUS * attack_score
        )
    return float(score)

def minimax(state: GameState, depth: int, alpha: float, beta: float, maximizing_player: bool, agent_color: PlayerColor, end_time: float):
    # a minimax search with alpha-beta pruning
    if time.process_time() >= end_time:
        raise TimeoutException()
    if depth == 0: # depth limit check to avoid expensive successor generation at leaf nodes
        return evaluation(state, agent_color), None

    alpha_original = alpha
    beta_original = beta
    tt_key = transposition_key(state, agent_color)
    tt_entry = TRANSPOSITION_TABLE.get(tt_key)
    tt_action = None
    if tt_entry is not None:
        stored_depth, stored_score, stored_flag, stored_action = tt_entry
        tt_action = stored_action
        if stored_depth >= depth:
            if stored_flag == EXACT:
                return stored_score, stored_action
            if stored_flag == LOWER_BOUND:
                alpha = max(alpha, stored_score)
            elif stored_flag == UPPER_BOUND:
                beta = min(beta, stored_score)
            if alpha >= beta:
                return stored_score, stored_action
    
    successors = get_successors(state, state.player_to_move) # fetch successors
    if state.is_terminal(no_legal_moves=len(successors) == 0): # check if the game is over
        if state.total_turn_count >= 8:
            red_exists = any(color == PlayerColor.RED for color, _ in state.board.values())
            blue_exists = any(color == PlayerColor.BLUE for color, _ in state.board.values())
            # elimination
            if red_exists and not blue_exists:
                return (WIN_SCORE + depth if agent_color == PlayerColor.RED else -WIN_SCORE - depth), None
            elif blue_exists and not red_exists:
                return (WIN_SCORE + depth if agent_color == PlayerColor.BLUE else -WIN_SCORE - depth), None
        
        # draw or turn limit conditions
        if state.play_phase_turns >= 300:
            return evaluation(state, agent_color), None 
        else: # stalemate or threefold repetition
            return 0.0, None 

    best_action = successors[0][1]
    if tt_action is not None:
        for i, (_, action) in enumerate(successors):
            if action == tt_action:
                successors[0], successors[i] = successors[i], successors[0]
                break

    if maximizing_player: # recursive alpha-beta search
        max_eval = float('-inf')
        for next_state, action in successors:
            eval_score, _ = minimax(next_state, depth - 1, alpha, beta, False, agent_color, end_time)
            if eval_score > max_eval:
                max_eval = eval_score
                best_action = action
            alpha = max(alpha, eval_score)
            if beta <= alpha: # beta cutoff
                break
        best_score = max_eval
        
    else:
        min_eval = float('inf')
        for next_state, action in successors:
            eval_score, _ = minimax(next_state, depth - 1, alpha, beta, True, agent_color, end_time)
            if eval_score < min_eval:
                min_eval = eval_score
                best_action = action
            beta = min(beta, eval_score)
            if beta <= alpha: # alpha cutoff
                break
        best_score = min_eval

    if best_score <= alpha_original:
        flag = UPPER_BOUND
    elif best_score >= beta_original:
        flag = LOWER_BOUND
    else:
        flag = EXACT

    if len(TRANSPOSITION_TABLE) < MAX_TRANSPOSITION_ENTRIES:
        TRANSPOSITION_TABLE[tt_key] = (depth, best_score, flag, best_action)
    return best_score, best_action