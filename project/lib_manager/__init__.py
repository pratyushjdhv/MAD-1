from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import secrets
from flask_bcrypt import Bcrypt
import os 
from lib_manager.admin import *


app = Flask(__name__)
bcrypt = Bcrypt(app)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///library_database.sqlite3"
app.secret_key = secrets.token_hex(16)


db = SQLAlchemy(app)
login_manager = LoginManager(app)

login_manager.login_view = "login"                     #type: ignore                       
login_manager.login_message_category= 'info'


from lib_manager.model import readers, requests
        
@login_manager.user_loader
def load_user(user_id):    
    user = readers.query.get(user_id)
    if user:
        return user
        
with app.app_context(): 
    db.create_all()
    admin = readers.query.filter_by(username=os.environ['admin_username']).first()

    if not admin:
        admin = readers(username=os.environ['admin_username'], email='admin@gmail.com', is_admin=True, is_librarian=True) #type: ignore
        admin.password = os.environ['admin_password']  
        db.session.add(admin)
        db.session.commit()

        
from lib_manager.routes import *
from lib_manager import app
import os
from datetime import date
from lib_manager import db

base_dir = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(base_dir, 'books')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def clean_up_files():
    # Get all the filenames of the books in the bookshelf
    book_filenames = [book.file_name for book in bookshelf.query.all()]
    #print(1,book_filenames)
    
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)        
        if os.path.isfile(file_path):
            # Extract the filename without the extension
            base_filename = os.path.splitext(filename)[0]+'.pdf'            
            # Check if the book exists in the bookshelf
            if base_filename not in book_filenames:                
                # If the book does not exist, delete the file
                os.remove(file_path)




def delete_expired_requests():
    expired_requests = requests.query.filter_by(borrowed_status=True).all()

    for request in expired_requests:
        if date.today() > request.return_date:
            db.session.delete(request)
            db.session.commit()


with app.app_context():
    clean_up_files()
    delete_expired_requests()

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


