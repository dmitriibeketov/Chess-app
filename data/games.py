import sqlalchemy
from .db_session import SqlAlchemyBase
from flask_login import UserMixin


class Game(SqlAlchemyBase, UserMixin):
    __tablename__ = 'games'

    game_number = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    white_player_id = sqlalchemy.Column(sqlalchemy.String)
    black_player_id = sqlalchemy.Column(sqlalchemy.String)
    result = sqlalchemy.Column(sqlalchemy.String, nullable=True)
