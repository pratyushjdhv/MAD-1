from flask import flash, url_for, redirect
from lib_manager import db, login_manager
from flask_login import UserMixin, current_user, login_manager
from lib_manager import bcrypt
from functools import wraps
from flask_login import login_manager
from sqlalchemy import func

class readers(db.Model, UserMixin):
    username = db.Column(db.String(length=30), nullable=False, unique=True)
    email = db.Column(db.String(), primary_key=True)
    password1 = db.Column(db.String(length=65), nullable=False)    
    is_admin = db.Column(db.Boolean(), default=False)
    is_librarian = db.Column(db.Boolean(), default=False)
    books_limit = db.Column(db.Integer(), default=5)

    @property
    def password(self):
        return self.password

    @password.setter
    def password(self, plain_text_password):
        self.password1 = bcrypt.generate_password_hash(
            plain_text_password).decode('utf8')

    def check_password(self, attempted_password):
        return bcrypt.check_password_hash(self.password1, attempted_password)

    def get_id(self):
        return (self.email)

    @staticmethod
    def get_user(username):
        return readers.query.get(username)

    def issue_book(self):
        if self.books_limit > 0:
            self.books_limit -= 1
            db.session.commit()
        else :
            db.session.rollback()
        db.session.commit()

    def return_book(self):
        if self.books_limit < 5:
            self.books_limit += 1
            db.session.commit()
        else :
            db.session.rollback()
        db.session.commit()

def admin_or_lib_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()  # type:ignore
        if not current_user.is_admin and not current_user.is_librarian:
            flash('Access denied. You are not authorized to access this page.', 'danger')
            return redirect(url_for('home'))
        return func(*args, **kwargs)
    return wrapper


class bookshelf(db.Model):
    isbn_no = db.Column(db.Integer(), primary_key=True, nullable=False)
    title = db.Column(db.String(), nullable=False, unique=True)
    author = db.Column(db.String(), nullable=False)
    genre = db.Column(db.String(), nullable=False)
    synopsis = db.Column(db.String(), nullable=False)
    uploader = db.Column(db.Integer(), db.ForeignKey(readers.email))
    file_name = db.Column(db.String(120), unique=True, nullable=False)
    file_path = db.Column(db.String(), unique=True, nullable=False)

    @staticmethod
    def getbook_id(book_id):
        return bookshelf.query.get(book_id)
    

class requests(db.Model):
    request_id = db.Column(db.Integer(), primary_key=True, nullable=False)
    book_id = db.Column(db.Integer(), db.ForeignKey(bookshelf.isbn_no))
    reader_id = db.Column(db.String(), db.ForeignKey(readers.email))
    request_date = db.Column(db.Date(), nullable=False)
    issue_date = db.Column(db.Date(), nullable=True)
    return_date = db.Column(db.Date(), nullable=True)
    return_status = db.Column(db.Boolean(), default=False)
    borrowed_status = db.Column(db.Boolean(), default=False)  #delete in future
    book = db.relationship('bookshelf', backref='requested_books', lazy=True)
    reader = db.relationship('readers', backref='requested_books', lazy=True)

    @staticmethod
    def get_request_id(request_id):
        return requests.query.get(request_id)
    
    @staticmethod
    def admin_or_librarian(reader_id):
        reader = readers.query.get(reader_id)
        if reader and (reader.is_admin or reader.is_librarian):
            return True
        else:
            return False

    @staticmethod
    def get_request_by_reader(reader_email, book_id):
        return requests.query.filter_by(reader_id=reader_email, book_id=book_id, return_status=False).first()
    
    @staticmethod
    def get_top_books_by_count():
        return db.session.query(bookshelf.title, func.count(requests.book_id)).join(requests).group_by(requests.book_id).order_by(func.count(requests.book_id).desc()).limit(20).all()

    @staticmethod
    def get_book_count_of_reader(reader_id):
        return requests.query.filter_by(reader_id=reader_id).count()
    
    @staticmethod
    def get_issued_book_count_of_reader(reader_id):
        return requests.query.filter_by(reader_id=reader_id, return_status=False).count()
   
    @staticmethod
    def get_status(reader_id, book_id):
        request = requests.query.filter_by(reader_id=reader_id, book_id=book_id).first()
        if request:
            return request.borrowed_status
        else:
            return None

    def get_book_title(self):
        return self.book.title

    
