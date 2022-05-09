from data import db_session
from data.players import Player
from data.movements import Movement_in_db
from data.games import Game
from flask_login import current_user
from data.db_recording import recording


class Cell:
    def __init__(self, figure, x, y):
        self.figure = figure
        self.x, self.y = x, y


def cell_under_attack(x, y, ex):
    for i in ex.cells:
        for j in i:
            if j.figure and j.figure.colour != ex.move and (type(j.figure) == Pawn and j.figure.beat_check(x, y) or
                                                            type(j.figure) != Pawn and j.figure.move_check(x, y, ex)):
                return True
    return False


def king_in_check(ex):
    for i in ex.cells:
        for j in i:
            if type(j.figure) == King and j.figure.colour == ex.move and cell_under_attack(j.x, j.y, ex):
                return True
    return False


def pat(ex):
    for i in ex.cells:
        for j in i:
            if j.figure and j.figure.colour == ex.move:
                for n in ex.cells:
                    for m in n:
                        if j != m:
                            figure1 = j.figure
                            figure2 = m.figure
                            last_queen_castling, last_king_castling = ex.queen_castling, ex.king_castling
                            last_castling1, last_opportunity1 = j.figure.castling, j.figure.opportunity
                            last_e_p = ex.e_p
                            last_reversible_move = ex.reversible_move
                            if m.figure:
                                last_castling2, last_opportunity2 = m.figure.castling, m.figure.opportunity

                            j.figure.move(m.x, m.y, ex)
                            if not figure2 and m.figure:
                                ex.move = "white" if ex.move == "black" else "black"
                                j.figure = figure1
                                m.figure = figure2
                                j.figure.x, j.figure.y = j.x, j.y
                                j.figure.castling, j.figure.opportunity = last_castling1, last_opportunity1
                                ex.e_p = last_e_p
                                if type(figure1) == King and j.x - m.x == 2:
                                    ex.cells[0][j.y].figure = Rook(figure1.colour, 0, j.y)
                                    ex.cells[2][j.y].figure = None
                                if type(figure1) == King and m.x - j.x == 2:
                                    ex.cells[7][j.y].figure = Rook(figure1.colour, 7, j.y)
                                    ex.cells[4][j.y].figure = None
                                if type(figure1) == Pawn and abs(m.x - j.x) == 1 and abs(m.y - j.y) == 1:
                                    colour = "white" if figure1.colour == "black" else "black"
                                    ex.cells[m.x][j.y].figure = Pawn(colour, m.x, j.y)
                                ex.queen_castling, ex.king_castling = last_queen_castling, last_king_castling
                                ex.reversible_move = last_reversible_move
                                return False

                            j.figure.beat(m.x, m.y, ex)
                            if not j.figure:
                                ex.move = "white" if ex.move == "black" else "black"
                                j.figure = figure1
                                m.figure = figure2
                                j.figure.x, j.figure.y = j.x, j.y
                                j.figure.castling, j.figure.opportunity = last_castling1, last_opportunity1
                                m.figure.x, m.figure.y = m.x, m.y
                                m.figure.castling, m.figure.opportunity = last_castling2, last_opportunity2
                                ex.queen_castling, ex.king_castling = last_queen_castling, last_king_castling
                                ex.reversible_move = last_reversible_move
                                return False
    return True


def theoretical_draw(ex):
    figures_list = []
    for i in ex.cells:
        figures_list += [cell.figure for cell in i if cell.figure and type(cell.figure) != King]
    figures_types_list = [type(figure) for figure in figures_list]
    if not figures_list:
        return True
    elif figures_types_list == [Elephant] or figures_types_list == [Horse]:
        return True
    elif figures_types_list == [Elephant, Elephant] and abs(figures_list[0].x % 2 - figures_list[0].y % 2) == \
            abs(figures_list[1].x % 2 - figures_list[1].y % 2):
        return True
    return False


class Figure:
    def __init__(self, colour, x, y):
        self.colour = colour
        self.castling = True
        self.opportunity = True
        self.x, self.y = x, y
        self.image = "static/" + {"white": "Бел", "black": "Чёрн"}[self.colour] + \
                     {Pawn: "ая пешка", Rook: "ая ладья", Horse: "ый конь", Elephant: "ый слон", Queen: "ый ферзь",
                      King: "ый король"}[type(self)] + ".jpg"

    def move(self, x, y, ex):
        if self.colour == ex.move and not ex.cells[x][y].figure and self.move_check(x, y, ex) and not ex.end:
            ex.cells[self.x][self.y].figure = None
            ex.cells[x][y].figure = self
            last_x, last_y, last_castling, last_opportunity = self.x, self.y, self.castling, self.opportunity
            last_reversible_move = ex.reversible_move
            self.x, self.y = x, y
            self.castling, self.opportunity = False, False
            if type(self) == Pawn:
                ex.reversible_move = False
            if king_in_check(ex):
                ex.cells[self.x][self.y].figure = None
                ex.cells[last_x][last_y].figure = self
                self.x, self.y, self.castling, self.opportunity = last_x, last_y, last_castling, last_opportunity
                ex.move = "white" if ex.move == "black" else "black"
                ex.reversible_move = last_reversible_move
                if type(self) == King and self.x - x == 2:
                    ex.cells[0][self.y].figure = Rook(self.colour, 0, self.y)
                    ex.cells[2][self.y].figure = None
                if type(self) == King and x - self.x == 2:
                    ex.cells[7][self.y].figure = Rook(self.colour, 7, self.y)
                    ex.cells[4][self.y].figure = None
            ex.move = "white" if ex.move == "black" else "black"
            if type(self) == Pawn and \
                    (self.y == 7 and self.colour == "white" or self.y == 0 and self.colour == "black"):
                ex.cells[self.x][self.y].figure = Queen(self.colour, self.x, self.y)

    def beat(self, x, y, ex):
        if self.colour == ex.move and ex.cells[x][y].figure and ex.cells[x][y].figure.colour != self.colour and not\
                ex.end and (type(self) == Pawn and self.beat_check(x, y) or
                            type(self) != Pawn and self.move_check(x, y, ex)):
            beaten_figure = ex.cells[x][y].figure
            last_castling1, last_opportunity1 = ex.cells[x][y].figure.castling, ex.cells[x][y].figure.opportunity
            ex.cells[self.x][self.y].figure = None
            ex.cells[x][y].figure = self
            last_x, last_y, last_castling, last_opportunity = self.x, self.y, self.castling, self.opportunity
            self.x, self.y = x, y
            self.castling, self.opportunity = False, False
            last_reversible_move = ex.reversible_move
            ex.reversible_move = False
            if king_in_check(ex):
                ex.cells[self.x][self.y].figure = beaten_figure
                ex.cells[self.x][self.y].figure.x, ex.cells[self.x][self.y].figure.y = \
                    ex.cells[self.x][self.y].x, ex.cells[self.x][self.y].y
                ex.cells[self.x][self.y].figure.castling, ex.cells[self.x][self.y].figure.opportunity = \
                    last_castling1, last_opportunity1
                ex.cells[last_x][last_y].figure = self
                self.x, self.y, self.castling, self.opportunity = last_x, last_y, last_castling, last_opportunity
                ex.move = "white" if ex.move == "black" else "black"
                ex.reversible_move = last_reversible_move
            ex.move = "white" if ex.move == "black" else "black"
            if type(self) == Pawn and \
                    (self.y == 7 and self.colour == "white" or self.y == 0 and self.colour == "black"):
                ex.cells[self.x][self.y].figure = Queen(self.colour, self.x, self.y)


class Pawn(Figure):
    def __init__(self, colour, x, y):
        super().__init__(colour, x, y)

    def move_check(self, x, y, ex):
        if x == self.x and ((y == self.y + 1 or y == self.y + 2 and self.opportunity and not ex.cells[x][y - 1].figure)
                            and self.colour == "white" or (y == self.y - 1 or y == self.y - 2 and self.opportunity and
                                                           not ex.cells[x][y + 1].figure) and self.colour == "black"):
            return True
        if self.beat_check(x, y):
            db_sess = db_session.create_session()
            game_number = db_sess.query(Game).filter(
                (Game.white_player_id == current_user.id) | (Game.black_player_id == current_user.id)
            ).filter(Game.result == None).first().game_number
            collection = db_sess.query(Movement_in_db).filter(Movement_in_db.game_number == game_number)
            if collection.all():
                movement_number = collection.all()[-1].movement_number
            else:
                db_sess.close()
                return False
            if ex.move == "black":
                move_script = collection.filter(Movement_in_db.movement_number ==
                                                movement_number).first().white_movement
            else:
                move_script = collection.filter(Movement_in_db.movement_number ==
                                                movement_number).first().black_movement
            db_sess.close()

            dictionary = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4, "f": 5, "g": 6, "h": 7}
            x1, y1 = dictionary[move_script[0]], int(move_script[1]) - 1
            x2, y2 = dictionary[move_script[3]], int(move_script[4]) - 1
            if type(ex.cells[x2][y2].figure) == Pawn and ex.cells[x2][y2].figure.colour != self.colour and \
                    abs(x1 - self.x) == 1 and x1 == x and abs(y1 - y2) == 2 and y1 + y2 == y * 2:
                ex.cells[x][self.y].figure = None
                ex.e_p = True
                return True
        return False

    def beat_check(self, x, y):
        if x in [self.x + 1, self.x - 1] and \
                (y == self.y + 1 and self.colour == "white" or y == self.y - 1 and self.colour == "black"):
            return True
        return False


class Rook(Figure):
    def __init__(self, colour, x, y):
        super().__init__(colour, x, y)

    def move_check(self, x, y, ex):
        if (x == self.x and y != self.y and
                not any([ex.cells[x][i].figure for i in range(min([y, self.y]) + 1, max([y, self.y]))])):
            return True
        elif (x != self.x and y == self.y and
              not any([ex.cells[i][y].figure for i in range(min([x, self.x]) + 1, max([x, self.x]))])):
            return True
        return False


class Horse(Figure):
    def __init__(self, colour, x, y):
        super().__init__(colour, x, y)

    def move_check(self, x, y, ex):
        if (x - self.x) ** 2 + (y - self.y) ** 2 == 5:
            return True
        return False


class Elephant(Figure):
    def __init__(self, colour, x, y):
        super().__init__(colour, x, y)

    def move_check(self, x, y, ex):
        if abs(self.x - x) == abs(self.y - y) != 0 and not \
                any([ex.cells[i][j].figure for i, j in zip(range(self.x, x, int(abs(self.x - x) / (x - self.x))),
                                                           range(self.y, y, int(abs(self.y - y) / (y - self.y))))][1:]):
            return True
        return False


class Queen(Figure):
    def __init__(self, colour, x, y):
        super().__init__(colour, x, y)

    def move_check(self, x, y, ex):
        if abs(self.x - x) == abs(self.y - y) != 0 and not \
                any([ex.cells[i][j].figure for i, j in zip(range(self.x, x, int(abs(self.x - x) / (x - self.x))),
                                                           range(self.y, y, int(abs(self.y - y) / (y - self.y))))][1:]):
            return True
        elif (x == self.x and y != self.y and
                not any([ex.cells[x][i].figure for i in range(min([y, self.y]) + 1, max([y, self.y]))])):
            return True
        elif (x != self.x and y == self.y and
              not any([ex.cells[i][y].figure for i in range(min([x, self.x]) + 1, max([x, self.x]))])):
            return True
        return False


class King(Figure):
    def __init__(self, colour, x, y):
        super().__init__(colour, x, y)

    def move_check(self, x, y, ex):
        if 0 < (self.x - x) ** 2 + (self.y - y) ** 2 < 3:
            return True
        elif self.x - x == 2 and y == self.y and self.castling and not ex.cells[x - 1][y].figure and not \
                ex.cells[x][y].figure and not ex.cells[x + 1][y].figure and type(ex.cells[x - 2][y].figure) == Rook \
                and ex.cells[x - 2][y].figure.castling and not cell_under_attack(x + 1, y, ex) and not \
                king_in_check(ex):
            ex.cells[x + 1][y].figure = Rook(self.colour, x + 1, y)
            ex.cells[x - 2][y].figure = None
            ex.queen_castling = True
            return True
        elif x - self.x == 2 and y == self.y and self.castling and not ex.cells[x - 1][y].figure and not \
                ex.cells[x][y].figure and type(ex.cells[x + 1][y].figure) == Rook and \
                ex.cells[x + 1][y].figure.castling and not cell_under_attack(x - 1, y, ex) and not \
                king_in_check(ex):
            ex.cells[x - 1][y].figure = Rook(self.colour, x - 1, y)
            ex.cells[x + 1][y].figure = None
            ex.king_castling = True
            return True
        return False


def initial_placement(ex):
    ex.cells = [[Cell(None, x, y) for y in range(8)] for x in range(8)]
    for i in range(8):
        ex.cells[i][1].figure = Pawn("white", i, 1)
        ex.cells[i][6].figure = Pawn("black", i, 6)
    for i, j in zip(range(0, 8, 7), ["white", "black"]):
        ex.cells[0][i].figure = Rook(j, 0, i)
        ex.cells[1][i].figure = Horse(j, 1, i)
        ex.cells[2][i].figure = Elephant(j, 2, i)
        ex.cells[3][i].figure = Queen(j, 3, i)
        ex.cells[4][i].figure = King(j, 4, i)
        ex.cells[5][i].figure = Elephant(j, 5, i)
        ex.cells[6][i].figure = Horse(j, 6, i)
        ex.cells[7][i].figure = Rook(j, 7, i)


class Management:
    def __init__(self):
        super().__init__()
        self.move = "white"
        self.end = False
        self.e_p = False
        self.fifty_moves_rule = 0
        self.reversible_move = True
        self.king_castling, self.queen_castling = False, False
        self.cells = [[Cell(None, i, j) for j in range(8)] for i in range(8)]

        initial_placement(self)

    def making_move(self, command):
        try:
            x1, y1, x2, y2 = command[0], command[1], command[3], command[4]
            x1 = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4, "f": 5, "g": 6, "h": 7}[x1]
            y1 = int(y1) - 1
            x2 = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4, "f": 5, "g": 6, "h": 7}[x2]
            y2 = int(y2) - 1
        except BaseException:
            return "Невозможный ход! Сделайте другой ход."
        if len(command) != 5 or command[2] != "-":
            return "Невозможный ход! Сделайте другой ход."
        if not self.cells[x1][y1].figure:
            return "Невозможный ход! Сделайте другой ход."

        last_self_move = self.move

        if self.cells[x2][y2].figure:
            self.cells[x1][y1].figure.beat(x2, y2, self)
        else:
            self.cells[x1][y1].figure.move(x2, y2, self)

        if self.move != last_self_move:
            x1 = {0: "a", 1: "b", 2: "c", 3: "d", 4: "e", 5: "f", 6: "g", 7: "h"}[x1]
            y1 = str(y1 + 1)
            x2 = {0: "a", 1: "b", 2: "c", 3: "d", 4: "e", 5: "f", 6: "g", 7: "h"}[x2]
            y2 = str(y2 + 1)
            recording(x1 + y1 + "-" + x2 + y2, self)

        self.e_p, self.king_castling, self.queen_castling = False, False, False
        if pat(self):
            self.end = True
            if king_in_check(self):
                return "Мат"
            else:
                return "Пат"
        if theoretical_draw(self):
            self.end = True
            return "Теоретическая ничья"
        if self.move == last_self_move:
            return "Невозможный ход! Сделайте другой ход."
        if self.move == "white":
            if not self.reversible_move:
                self.fifty_moves_rule = 0
            else:
                self.fifty_moves_rule += 1
            if self.fifty_moves_rule == 75:
                self.end = True
                return "Ничья по правилу 75 ходов"
            self.reversible_move = True
        return "Сделайте ход"
