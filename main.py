from flask import Flask, render_template, redirect
from data import db_session
from data.players import Player
from data.movements import Movement_in_db
from data.games import Game
from forms.player import RegisterForm, LoginForm
from forms.movement import Movement
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import chess
import requests


class Control:
    def __init__(self):
        self.games = {}
        self.passive_gamer = None
        self.local_games = {}


control = Control()


app = Flask(__name__)
app.config['SECRET_KEY'] = 'chess_secret_key'


login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_player(player_id):
    db_sess = db_session.create_session()
    result = db_sess.query(Player).get(player_id)
    db_sess.close()
    return result


@app.route('/register', methods=['GET', 'POST'])
def reqister():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация', form=form, message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(Player).filter(Player.name == form.name.data).first():
            return render_template('register.html', title='Регистрация', form=form,
                                   message="Такой пользователь уже есть")
        player = Player(name=form.name.data)
        player.set_password(form.password.data)
        db_sess.add(player)
        db_sess.commit()
        db_sess.close()
        return redirect('/')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        player = db_sess.query(Player).filter(Player.name == form.name.data).first()
        db_sess.close()
        if player and player.check_password(form.password.data):
            login_user(player, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html', message="Неправильное имя или пароль", form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/', methods=['GET', 'POST'])
def basic():
    return render_template("base.html")


@app.route('/look_over', methods=['GET', 'POST'])
def look_over():
    db_sess = db_session.create_session()
    games_list = db_sess.query(Game).filter((Game.white_player_id == current_user.id) |
                                            (Game.black_player_id == current_user.id)).all()
    games_list1 = {}
    for game in games_list:
        movements = db_sess.query(Movement_in_db).filter(Movement_in_db.game_number == game.game_number).all()
        enemies = f"{db_sess.query(Player).filter(Player.id == game.white_player_id).first().name} - " \
                  f"{db_sess.query(Player).filter(Player.id == game.black_player_id).first().name}"
        game1 = {}
        for movement in movements:
            if movement.black_movement:
                game1[len(game1)] = (movement.white_movement, movement.black_movement)
            else:
                game1[len(game1)] = (movement.white_movement, "")
        if game.result:
            games_list1[len(games_list1)] = (enemies, game1, game.result)
        else:
            games_list1[len(games_list1)] = (enemies, game1, "Партия ещё не окончена")
    db_sess.close()
    return render_template("games_recording.html", games_list=games_list1)


@app.route('/local_game',  methods=['GET', 'POST'])
@login_required
def local_game():
    if current_user.id not in control.local_games:
        db_sess = db_session.create_session()
        for game1 in db_sess.query(Game).filter(Game.result == None).filter(
                (Game.white_player_id == current_user.id) | (Game.black_player_id == current_user.id) |
                (Game.white_player_id == control.passive_gamer) | (Game.black_player_id == control.passive_gamer)):
            game1.result = "Партия прервана"
        global_games_list = list(filter(lambda game: current_user.id in game or control.passive_gamer in game,
                                        control.games.keys()))
        local_games_list = list(filter(lambda game: game in [current_user.id, control.passive_gamer],
                                       control.games.keys()))
        for key in global_games_list:
            del control.games[key]
        for key in local_games_list:
            del control.local_games[key]
        control.local_games[current_user.id] = chess.Management()
        if db_sess.query(Game).all():
            game_number = db_sess.query(Game).all()[-1].game_number + 1
        else:
            game_number = 1
        db_sess.add(Game(white_player_id=current_user.id, black_player_id=current_user.id, game_number=game_number))
        db_sess.commit()
        db_sess.close()

    board = control.local_games[current_user.id].cells
    form = Movement()
    if form.validate_on_submit():
        movement = str(form.content)[54:-2]
        message = control.local_games[current_user.id].making_move(movement)

        if message != "Невозможный ход! Сделайте другой ход.":
            db_sess = db_session.create_session()
            game_number = db_sess.query(Game).filter(Game.white_player_id == Game.black_player_id).\
                filter(Game.black_player_id == current_user.id).filter(Game.result == None).first().game_number
            collection = db_sess.query(Movement_in_db).filter(Movement_in_db.game_number == game_number)
            if message in ["Пат", "Теоретическая ничья", "Ничья по правилу 75 ходов", "Мат"]:
                if message in ["Пат", "Теоретическая ничья", "Ничья по правилу 75 ходов"]:
                    result = "Ничья"
                elif control.local_games[current_user.id].move == "white":
                    result = "Победа чёрных"
                else:
                    result = "Победа белых"
                db_sess.query(Game).filter(Game.game_number == game_number).first().result = result
                db_sess.commit()

                message += "! А знаете ли вы, что только что разыграли "
                white = collection.filter(Movement_in_db.movement_number == 1).first().white_movement
                black = collection.filter(Movement_in_db.movement_number == 1).first().black_movement
                if white == "d2-d4" and black == "d7-d5" or white == "e2-e4" and black == "e7-e5":
                    determinant = black
                else:
                    determinant = white
                message += (requests.get("http://dmitrybeketov.pythonanywhere.com/").json()[determinant] + "?")

                db_sess.close()
                del control.local_games[current_user.id]
                return render_template("waiting.html", board=board, message=message)
            db_sess.commit()
            db_sess.close()

        return render_template("game.html", board=board, message=message, form=form)
    return render_template("game.html", board=board, message="Сделайте ход", form=form)


@app.route('/game',  methods=['GET', 'POST'])
@login_required
def game():
    if not list(filter(lambda x: current_user.id in x, control.games.keys())):
        if control.passive_gamer and control.passive_gamer != current_user.id:
            db_sess = db_session.create_session()
            for game1 in db_sess.query(Game).filter(Game.result == None).filter(
                    (Game.white_player_id == current_user.id) | (Game.black_player_id == current_user.id) |
                    (Game.white_player_id == control.passive_gamer) | (Game.black_player_id == control.passive_gamer)):
                game1.result = "Партия прервана"
            global_games_list = list(filter(lambda game: current_user.id in game or control.passive_gamer in game,
                                            control.games.keys()))
            local_games_list = list(filter(lambda game: game in [current_user.id, control.passive_gamer],
                                           control.games.keys()))
            for key in global_games_list:
                del control.games[key]
            for key in local_games_list:
                del control.local_games[key]
            control.games[(control.passive_gamer, current_user.id)] = chess.Management()
            if db_sess.query(Game).all():
                game_number = db_sess.query(Game).all()[-1].game_number + 1
            else:
                game_number = 1
            db_sess.add(Game(white_player_id=control.passive_gamer, black_player_id=current_user.id,
                             game_number=game_number))
            db_sess.commit()
            db_sess.close()

            control.passive_gamer = None
        else:
            control.passive_gamer = current_user.id

            return render_template("waiting.html", board=chess.Management().cells,
                                   message="Мы скоро подберём вам противника")
    key = list(filter(lambda x: current_user.id in x, control.games.keys()))[0]
    if control.games[key].move == "white" and key[1] == current_user.id or control.games[key].move == "black" and \
            key[0] == current_user.id:
        return render_template("waiting.html", board=control.games[key].cells,
                               message="Подождите, пока ваш противник сделает ход")
    form = Movement()
    if form.validate_on_submit():
        movement = str(form.content)[54:-2]
        message = control.games[key].making_move(movement)
        board = control.games[key]

        if message != "Невозможный ход! Сделайте другой ход.":
            db_sess = db_session.create_session()
            game_number = db_sess.query(Game).filter((Game.white_player_id == current_user.id) |
                                                     (Game.black_player_id == current_user.id)).filter(
                Game.result == None).first().game_number
            collection = db_sess.query(Movement_in_db).filter(Movement_in_db.game_number == game_number)
            if message in ["Пат", "Теоретическая ничья", "Ничья по правилу 75 ходов", "Мат"]:
                if message in ["Пат", "Теоретическая ничья", "Ничья по правилу 75 ходов"]:
                    result = "Ничья"
                elif board.move == "white":
                    result = "Победа чёрных"
                else:
                    result = "Победа белых"
                db_sess.query(Game).filter(Game.game_number == game_number).first().result = result
                db_sess.commit()

                message += "! А знаете ли вы, что только что разыграли "
                white = collection.filter(Movement_in_db.movement_number == 1).first().white_movement
                black = collection.filter(Movement_in_db.movement_number == 1).first().black_movement
                if white == "d2-d4" and black == "d7-d5" or white == "e2-e4" and black == "e7-e5":
                    determinant = black
                else:
                    determinant = white
                message += (requests.get("http://dmitrybeketov.pythonanywhere.com/").json()[determinant] + "?")

                db_sess.close()
                del control.games[key]
                return render_template("waiting.html", board=board.cells, message=message)
            db_sess.commit()
            db_sess.close()
            return render_template("waiting.html", board=board.cells,
                                   message="Подождите, пока ваш противник сделает ход")
        return render_template("game.html", board=board.cells, message=message, form=form)

    return render_template("game.html", board=control.games[key].cells, message="Сделайте ход", form=form)


def main():
    db_session.global_init("db/players_passwords.db")
    app.run(port=8000)


if __name__ == '__main__':
    main()
