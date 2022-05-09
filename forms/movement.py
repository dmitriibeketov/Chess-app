from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField


class Movement(FlaskForm):
    content = StringField("Ход")
    submit = SubmitField('Совершить')
