from fasthtml.common import *
import json
from urllib.parse import quote, unquote
import uuid

app, rt = fast_app(hdrs=[Script(src="https://cdn.tailwindcss.com")])

def encode_board(board):
    # Convert board to a simple string: each cell as a digit (0,1,2)
    return ''.join(str(cell) for row in board for cell in row)

def decode_board(encoded):
    try:
        # Convert string back to 7x7 board
        if len(encoded) != 49:
            raise ValueError("Invalid board string")
        board = []
        for i in range(7):
            row = []
            for j in range(7):
                row.append(int(encoded[i * 7 + j]))
            board.append(row)
        return board
    except:
        return [[0 for _ in range(7)] for _ in range(7)]

def get_valid_moves(board, row, col):
    moves = []
    directions = [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]
    
    for dr, dc in directions:
        # Adjacent move (copy)
        nr1, nc1 = row + dr, col + dc
        if 0 <= nr1 < 7 and 0 <= nc1 < 7 and board[nr1][nc1] == 0:
            moves.append((nr1, nc1, 'copy'))
        
        # Jump move (2 spaces, no copy)
        nr2, nc2 = row + 2*dr, col + 2*dc
        if 0 <= nr2 < 7 and 0 <= nc2 < 7 and board[nr2][nc2] == 0:
            moves.append((nr2, nc2, 'jump'))
    
    return moves

def apply_move(board, from_row, from_col, to_row, to_col, current_player):
    new_board = [row[:] for row in board]
    
    # Check if it's a jump (2 spaces away)
    distance = max(abs(to_row - from_row), abs(to_col - from_col))
    
    if distance == 2:  # Jump move
        new_board[from_row][from_col] = 0  # Remove original
    else:  # Copy move
        new_board[from_row][from_col] = current_player  # Keep original
    
    new_board[to_row][to_col] = current_player
    
    # Convert adjacent enemy cells
    directions = [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]
    for dr, dc in directions:
        nr, nc = to_row + dr, to_col + dc
        if 0 <= nr < 7 and 0 <= nc < 7 and new_board[nr][nc] == 3 - current_player:
            new_board[nr][nc] = current_player
    
    return new_board

def count_cells(board):
    p1 = sum(row.count(1) for row in board)
    p2 = sum(row.count(2) for row in board)
    return p1, p2

def check_game_over(board):
    # Check if any player has no cells
    p1_count, p2_count = count_cells(board)
    if p1_count == 0 or p2_count == 0:
        return True
    
    # Check if any player can make a move
    for r in range(7):
        for c in range(7):
            if board[r][c] == 1 and get_valid_moves(board, r, c):
                return False
            if board[r][c] == 2 and get_valid_moves(board, r, c):
                return False
    
    return True

def get_all_possible_moves(board, player):
    moves = []
    for r in range(7):
        for c in range(7):
            if board[r][c] == player:
                valid_moves = get_valid_moves(board, r, c)
                for to_r, to_c, move_type in valid_moves:
                    moves.append((r, c, to_r, to_c))
    return moves

def evaluate_move(board, from_row, from_col, to_row, to_col, player):
    # Simulate the move and count resulting bacteria
    new_board = apply_move(board, from_row, from_col, to_row, to_col, player)
    p1_count, p2_count = count_cells(new_board)
    return p1_count if player == 1 else p2_count

def get_computer_move(board, player):
    # Get all possible moves
    possible_moves = get_all_possible_moves(board, player)
    
    if not possible_moves:
        return None
    
    # Evaluate each move and pick the best one
    best_move = None
    best_score = -1
    
    for from_r, from_c, to_r, to_c in possible_moves:
        score = evaluate_move(board, from_r, from_c, to_r, to_c, player)
        if score > best_score:
            best_score = score
            best_move = (from_r, from_c, to_r, to_c)
    
    return best_move

def render_game_content(board_state, selected, current_player, mode, game_id, encoded_board):
    p1_count, p2_count = count_cells(board_state)
    game_over = check_game_over(board_state)
    
    return Div(
        # Score display
        Div(
            Div(
                Span("Player 1 (Blue): ", cls="font-semibold"),
                Span(str(p1_count), cls="text-2xl font-bold text-blue-500"),
                cls="flex items-center gap-2"
            ),
            Div(
                Span("Player 2 (Red): ", cls="font-semibold"),
                Span(str(p2_count), cls="text-2xl font-bold text-red-500"),
                cls="flex items-center gap-2"
            ),
            cls="flex gap-8 mb-6"
        ),
        
        # Current player indicator
        Div(
            "Current Turn: ",
            Span(f"Player {current_player}", cls=f"font-bold {'text-blue-500' if current_player == 1 else 'text-red-500'}"),
            Span(f" ({'You' if current_player == 1 else 'Computer' if mode == 'computer' else 'Human'})", cls="text-gray-600"),
            cls="text-xl mb-6"
        ) if not game_over else None,
        
        # Game over message
        Div(
            H2("Game Over!", cls="text-3xl font-bold mb-4"),
            P(f"{'Player 1 (Blue)' if p1_count > p2_count else 'Player 2 (Red)'} Wins!" if p1_count != p2_count else "It's a tie!",
              cls="text-2xl"),
            cls="text-center mb-6"
        ) if game_over else None,
        
        # Game board
        Div(
            *[Div(
                *[render_cell(board_state, r, c, selected, current_player, encoded_board, mode, game_id) for c in range(7)],
                cls="flex gap-2"
            ) for r in range(7)],
            cls="flex flex-col gap-2 mb-8"
        ),
        
        id="game-content"
    )

def render_cell(board, row, col, selected, current_player, encoded_board, mode, game_id):
    cell_value = board[row][col]
    cell_id = f"cell-{row}-{col}"
    
    base_classes = "w-12 h-12 border-2 border-gray-400 rounded-lg flex items-center justify-center cursor-pointer transition-all duration-200 ease-in-out transform"
    
    if selected and selected[0] == row and selected[1] == col:
        base_classes += " ring-4 ring-yellow-400"
    
    if cell_value == 0:
        # Empty cell - check if it's a valid move
        if selected and (row, col, 'copy') in [(m[0], m[1], m[2]) for m in get_valid_moves(board, selected[0], selected[1])]:
            return A(
                Div(
                    Div(cls="w-2 h-2 bg-green-600 rounded-full opacity-50"),
                    cls=base_classes + " bg-green-200 hover:bg-green-300 hover:scale-110 hover:shadow-lg"
                ),
                href=f"/?board={encoded_board}&move={selected[0]},{selected[1]},{row},{col}&player={current_player}&mode={mode}&game_id={game_id}",
                id=cell_id
            )
        elif selected and (row, col, 'jump') in [(m[0], m[1], m[2]) for m in get_valid_moves(board, selected[0], selected[1])]:
            return A(
                Div(
                    Div(cls="w-3 h-3 bg-yellow-600 rounded-full opacity-50"),
                    cls=base_classes + " bg-yellow-200 hover:bg-yellow-300 hover:scale-110 hover:shadow-lg"
                ),
                href=f"/?board={encoded_board}&move={selected[0]},{selected[1]},{row},{col}&player={current_player}&mode={mode}&game_id={game_id}",
                id=cell_id
            )
        else:
            return Div(cls=base_classes + " bg-gray-100", id=cell_id)
    elif cell_value == 1:
        if current_player == 1:
            return A(
                Div(
                    Div(cls="w-8 h-8 bg-blue-500 rounded-full"),
                    cls=base_classes + " hover:ring-2 hover:ring-blue-300 hover:scale-105"
                ),
                href=f"/?board={encoded_board}&select={row},{col}&player={current_player}&mode={mode}&game_id={game_id}",
                id=cell_id
            )
        else:
            return Div(
                Div(cls="w-8 h-8 bg-blue-500 rounded-full"),
                cls=base_classes,
                id=cell_id
            )
    else:  # cell_value == 2
        if current_player == 2:
            return A(
                Div(
                    Div(cls="w-8 h-8 bg-red-500 rounded-full"),
                    cls=base_classes + " hover:ring-2 hover:ring-red-300 hover:scale-105"
                ),
                href=f"/?board={encoded_board}&select={row},{col}&player={current_player}&mode={mode}&game_id={game_id}",
                id=cell_id
            )
        else:
            return Div(
                Div(cls="w-8 h-8 bg-red-500 rounded-full"),
                cls=base_classes,
                id=cell_id
            )

@rt("/")
def index(board: str = None, select: str = None, move: str = None, player: int = 1, mode: str = "computer", game_id: str = None):
    # Generate game ID for new games
    if not game_id:
        game_id = str(uuid.uuid4())[:8]  # Short ID for readability
    
    # Initialize or decode board
    if board:
        board_state = decode_board(board)
    else:
        # Initial board setup
        board_state = [[0 for _ in range(7)] for _ in range(7)]
        board_state[0][0] = 1
        board_state[0][6] = 2
        board_state[6][0] = 2
        board_state[6][6] = 1
    
    current_player = int(player)
    selected = None
    
    # Handle selection
    if select:
        row, col = map(int, select.split(','))
        if board_state[row][col] == current_player:
            selected = (row, col)
    
    # Handle move
    if move:
        from_row, from_col, to_row, to_col = map(int, move.split(','))
        board_state = apply_move(board_state, from_row, from_col, to_row, to_col, current_player)
        current_player = 3 - current_player  # Switch player
        selected = None
        
        # If playing against computer and it's player 2's turn
        if mode == "computer" and current_player == 2 and not check_game_over(board_state):
            computer_move = get_computer_move(board_state, 2)
            if computer_move:
                from_r, from_c, to_r, to_c = computer_move
                board_state = apply_move(board_state, from_r, from_c, to_r, to_c, 2)
                current_player = 1  # Back to human player
    
    encoded_board = encode_board(board_state)
    p1_count, p2_count = count_cells(board_state)
    game_over = check_game_over(board_state)
    
    return Html(
        Head(
            Title("Bacteria Game - Strategic Multiplayer Board Game"),
            Script(src="https://cdn.tailwindcss.com"),
            
            # Open Graph meta tags
            Meta(property="og:title", content="Bacteria Game - Strategic Multiplayer Board Game"),
            Meta(property="og:description", content="Play a strategic bacteria conquest game! Spread your bacteria across the board by copying or jumping. Challenge the AI or play against a friend."),
            Meta(property="og:type", content="website"),
            Meta(property="og:image", content="/image.png"),
            Meta(property="og:image:width", content="1200"),
            Meta(property="og:image:height", content="630"),
            Meta(property="og:site_name", content="Bacteria Game"),
            
            # Twitter Card meta tags
            Meta(name="twitter:card", content="summary_large_image"),
            Meta(name="twitter:title", content="Bacteria Game - Strategic Multiplayer Board Game"),
            Meta(name="twitter:description", content="Play a strategic bacteria conquest game! Spread your bacteria across the board by copying or jumping. Challenge the AI or play against a friend."),
            Meta(name="twitter:image", content="/image.png"),
            
            # Additional meta tags
            Meta(name="description", content="Play a strategic bacteria conquest game! Spread your bacteria across the board by copying or jumping. Challenge the AI or play against a friend."),
            Meta(name="viewport", content="width=device-width, initial-scale=1.0"),
            Meta(charset="UTF-8")
        ),
        Body(
            Div(
                H1("Bacteria Game", cls="text-4xl font-bold mb-4"),
                Div(
                    P(f"Mode: {'vs Computer' if mode == 'computer' else 'vs Human'}", cls="text-lg text-gray-600"),
                    P(f"Game ID: {game_id}", cls="text-sm text-gray-500"),
                    cls="mb-6"
                ),
                
                # Score display
                Div(
                    Div(
                        Span("Player 1 (Blue): ", cls="font-semibold"),
                        Span(str(p1_count), cls="text-2xl font-bold text-blue-500"),
                        cls="flex items-center gap-2"
                    ),
                    Div(
                        Span("Player 2 (Red): ", cls="font-semibold"),
                        Span(str(p2_count), cls="text-2xl font-bold text-red-500"),
                        cls="flex items-center gap-2"
                    ),
                    cls="flex gap-8 mb-6"
                ),
                
                # Current player indicator
                Div(
                    "Current Turn: ",
                    Span(f"Player {current_player}", cls=f"font-bold {'text-blue-500' if current_player == 1 else 'text-red-500'}"),
                    Span(f" ({'You' if current_player == 1 else 'Computer' if mode == 'computer' else 'Human'})", cls="text-gray-600"),
                    cls="text-xl mb-6"
                ) if not game_over else None,
                
                # Game over message
                Div(
                    H2("Game Over!", cls="text-3xl font-bold mb-4"),
                    P(f"{'Player 1 (Blue)' if p1_count > p2_count else 'Player 2 (Red)'} Wins!" if p1_count != p2_count else "It's a tie!",
                      cls="text-2xl"),
                    cls="text-center mb-6"
                ) if game_over else None,
                
                # Game board
                Div(
                    *[Div(
                        *[render_cell(board_state, r, c, selected, current_player, encoded_board, mode, game_id) for c in range(7)],
                        cls="flex gap-2"
                    ) for r in range(7)],
                    cls="flex flex-col gap-2 mb-8"
                ),
                
                # Instructions
                Div(
                    H3("How to Play:", cls="text-xl font-semibold mb-2"),
                    Ul(
                        Li("Click on your bacteria to select it"),
                        Li("Green cells show where you can copy (move 1 space and duplicate)"),
                        Li("Yellow cells show where you can jump (move 2 spaces, no duplicate)"),
                        Li("Moving converts all adjacent enemy bacteria to your color"),
                        Li("Win by eliminating all enemy bacteria or blocking all their moves"),
                        cls="list-disc list-inside space-y-1"
                    ),
                    cls="text-gray-700"
                ),
                
                # Game mode buttons
                Div(
                    A(
                        Button("New Game vs Computer", cls="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"),
                        href=f"/?mode=computer&game_id={str(uuid.uuid4())[:8]}"
                    ),
                    A(
                        Button("New Game vs Human", cls="px-6 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600"),
                        href=f"/?mode=human&game_id={str(uuid.uuid4())[:8]}"
                    ),
                    cls="flex gap-4 mt-6"
                ),
                
                cls="max-w-4xl mx-auto p-8"
            ),
            cls="bg-gray-50 min-h-screen"
        )
    )

@rt("/image.png")
def social_image():
    return FileResponse("image.png")

serve()