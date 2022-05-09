from data import db_session
from data.players import Player
from data.movements import Movement_in_db
from data.games import Game
from flask_login import current_user


def recording(movement, board):
    db_sess = db_session.create_session()
    game_number = db_sess.query(Game).filter((Game.white_player_id == current_user.id) |
                                             (Game.black_player_id == current_user.id)).filter(
        Game.result == None).first().game_number
    collection = db_sess.query(Movement_in_db).filter(Movement_in_db.game_number == game_number)
    if collection.all():
        movement_number = collection.all()[-1].movement_number + 1
    else:
        movement_number = 1
    if board.move == "black":
        db_sess.add(Movement_in_db(game_number=game_number, movement_number=movement_number,
                                   white_movement=movement))
    else:
        collection.filter(
            Movement_in_db.movement_number == movement_number - 1).first().black_movement = movement
    db_sess.commit()
    db_sess.close()
