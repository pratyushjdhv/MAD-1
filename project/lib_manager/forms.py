
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField,TextAreaField, FileField,SelectField
from wtforms import validators as val
from lib_manager.model import readers

class register_form(FlaskForm):

    def validate_username(self, username):
        reader = readers.query.filter_by(username=username.data).first()
        if reader:
            raise val.ValidationError('Username already in use')

    def validate_email(self, email):
        existing_email = readers.query.filter_by(email=email.data).first()
        if existing_email:
            raise val.ValidationError('Email already in use')
        
    username = StringField(label='User Name:', validators=[val.Length(min=2, max=30), val.DataRequired()])
    email = StringField(label='Email Address:', validators=[val.Email(), val.DataRequired()])
    password = PasswordField('Password:', validators=[val.DataRequired(), val.Length(min=6)])
    confirm_password = PasswordField(label='Confirm Password:', validators=[val.EqualTo('password'), val.DataRequired()])
    submit = SubmitField(label='Create Account')



class login_form(FlaskForm):
    username = StringField('Username', validators=[val.DataRequired()])
    password = PasswordField('Password', validators=[val.DataRequired()])
    submit = SubmitField(label='Sign In')


class addbookform(FlaskForm):
    isbn_no = StringField(label='ID:' , validators=[val.DataRequired()])
    title = StringField(label='Name:', validators=[val.DataRequired()])
    author = StringField(label='Author:', validators=[val.DataRequired()])
    genre = StringField(label='Genre:', validators=[val.DataRequired()])    
    uploader = StringField(label='Uploader:', validators=[val.DataRequired()])
    synopsis = TextAreaField(label='Synopsis:', validators=[val.DataRequired()])
    book_file = FileField(label='Upload Book')
    


class search_book(FlaskForm):
    search_term = StringField(label='Search :')
    search_by = SelectField(label='Search By :', choices=[('isbn', 'ISBN'), ('title', 'Title'), ('author', 'Author'), ('genre', 'Genre')]) 