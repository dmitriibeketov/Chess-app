import sqlalchemy
from .db_session import SqlAlchemyBase
from flask_login import UserMixin


class Movement_in_db(SqlAlchemyBase, UserMixin):
    __tablename__ = 'movements'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    game_number = sqlalchemy.Column(sqlalchemy.Integer)
    movement_number = sqlalchemy.Column(sqlalchemy.Integer)
    white_movement = sqlalchemy.Column(sqlalchemy.String)
    black_movement = sqlalchemy.Column(sqlalchemy.String, nullable=True)
