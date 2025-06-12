from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length

class PostForm(FlaskForm):
    company = SelectField('Spółka', coerce=int, validators=[DataRequired()])
    title = StringField('Tytuł', validators=[DataRequired(), Length(max=200)])
    content = TextAreaField('Treść', validators=[DataRequired()])
    submit = SubmitField('Dodaj post')

class CommentForm(FlaskForm):
    content = TextAreaField('Treść', validators=[DataRequired()])
    submit = SubmitField('Dodaj komentarz')
