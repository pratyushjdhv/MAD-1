from datetime import date, timedelta
from lib_manager import db, app
from flask import flash, render_template, redirect, request, url_for, current_app, send_from_directory
from lib_manager.forms import register_form, login_form, addbookform,  search_book
from lib_manager.model import requests, readers, bookshelf, admin_or_lib_required
from flask import flash, redirect, url_for
import os
from werkzeug.utils import secure_filename
from flask_login import login_user, logout_user, current_user, login_required
from sqlalchemy import func


@app.route('/')
@app.route('/home', methods=['GET', 'POST'])
def home():
    form = search_book()
    books = None

    if form.validate_on_submit():
        search_term = form.search_term.data
        search_by = form.search_by.data

        if search_by == 'isbn':
            books = bookshelf.query.filter(
                bookshelf.isbn_no.ilike(f"%{search_term}%")).all()
        elif search_by == 'title':
            books = bookshelf.query.filter(
                bookshelf.title.ilike(f"%{search_term}%")).all()
        elif search_by == 'author':
            books = bookshelf.query.filter(
                bookshelf.author.ilike(f"%{search_term}%")).all()
        elif search_by == 'genre':
            books = bookshelf.query.filter(
                bookshelf.genre.ilike(f"%{search_term}%")).all()
    else:
        books = bookshelf.query.all()  

    get_request_by_reader = requests.get_request_by_reader if current_user.is_authenticated else None
    get_status = requests.get_status if current_user.is_authenticated else None


    return render_template('home.html', form=form, books=books,get_request_by_reader=get_request_by_reader,get_status=get_status)


@app.route('/view_pdf/<path:filename>')
@login_required
def view_pdf(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path) and os.access(file_path, os.R_OK):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=False)
    else:
        return "File not found or no permission to read the file", 404
    

@app.route('/trending_books',  methods=['GET', 'POST'])
def trending_books():
    top_book_counts= requests.get_top_books_by_count()

    return render_template('trending.html', books=top_book_counts)


@app.route('/request_for_book', methods=['GET', 'POST'])
@login_required
@admin_or_lib_required
def request_for_book(): 
    if request.method == 'POST':
        book_id = request.form.get('book_id')  
    else:
        book_id = request.args.get('book_id')

    book_requests = requests.query.filter_by(book_id=book_id).all()    
    return render_template('book_req.html', book_requests=book_requests) 
 


@app.route('/request_book/<int:book_id>', methods=['POST'])
@login_required
def request_book(book_id):
    reader_id = current_user.email  
    reader = readers.query.get(reader_id)

    if reader and not reader.is_admin and not reader.is_librarian:
        # Check if the reader has already borrowed 5 books
        current_borrowed_count = requests.query.filter_by(reader_id=reader_id, return_status=False).count()
        if current_borrowed_count >= 5:
            flash('You cannot borrow more than 5 books.', 'danger')
            return redirect(url_for('home'))                
        else:
            new_request = requests(book_id=book_id,     #type:ignore
                                   reader_id=reader_id, 
                                   request_date=date.today()
                                   )
            db.session.add(new_request)
            db.session.commit()            

    return redirect(url_for('home'))

@app.route('/accept_request/<int:book_id>/<string:reader_id>', methods=['POST'])
@login_required
@admin_or_lib_required
def accept_request(book_id, reader_id):
    current_page_url = request.referrer
    requests_to_accept = requests.query.filter_by(book_id=book_id, reader_id=reader_id, return_status=False).all()
    if requests_to_accept:
        for request_id in requests_to_accept:
            request_id.borrowed_status = True
            request_id.issue_date = date.today()
            return_date = date.today() + timedelta(days=7)
            request_id.return_date = return_date
            db.session.commit()
            
            user = readers.query.get(request_id.reader_id)
            if user:
                user.issue_book()
            else:
                flash('User not found', 'danger')
        
        flash('Requests accepted successfully', 'success')
    else:
        flash('Requests not found', 'danger')
    
    return redirect(current_page_url)


@app.route('/delete_request/<int:book_id>/<string:reader_id>', methods=['POST'])
@login_required
@admin_or_lib_required
def delete_request(book_id, reader_id):
    current_page_url = request.referrer

    request_to_delete = requests.query.filter_by(book_id=book_id, reader_id=reader_id, return_status=False).first()
    if request_to_delete:
        db.session.delete(request_to_delete)
        db.session.commit()
        flash('Request deleted successfully', 'success')
    else:
        flash('Request not found', 'danger')
    return redirect(current_page_url)


@app.route('/return_book/<int:book_id>/<string:reader_id>', methods=['POST', 'GET'])
@login_required
def return_book(book_id, reader_id):
    request_id = requests.query.filter_by(book_id=book_id, reader_id=reader_id, return_status=False).first()
    if request_id:
        db.session.delete(request_id)
        db.session.commit()

        user = readers.query.get(request_id.reader_id)
        if user:
                user.return_book()
        else:
            flash('User not found', 'danger')
        flash('Book returned successfully', 'success')
    else:
        flash('Request not found', 'danger')
    return redirect(url_for('book_request'))


@app.route('/info/<string:username>')
@login_required
def user_info(username):
    try:
        user = readers.query.filter_by(username='abc').first()    
        current_request = requests.query.filter_by(reader_id=user.email, return_status=False, borrowed_status=False).all()
        owned=requests.query.filter_by(reader_id=user.email, return_status=False, borrowed_status=True).all()
        return render_template('info.html', user=user, request=current_request,owned=owned)
    except:
        flash('User not found', 'danger')
        return redirect(url_for('home'))


admin = os.environ.get('admin_username')
admin_pw = os.environ.get('admin_password')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = register_form()
    if form.validate_on_submit():
        create_user = readers(username=form.username.data,              # type: ignore
                              email=form.email.data,
                              password=form.password.data,
                              )
        db.session.add(create_user)
        db.session.commit()

        print(f'Username: {create_user.username}')

        if create_user.username != 'admin':
            login_user(create_user)

        flash(f'Account created successfully! You are now logged in as {
              create_user.username} ', category='success')
        print(f'Username: {create_user.username}')
        return redirect(url_for('home'))

    elif form.errors:
        for error in form.errors.values():
            flash(error[0], category='danger')  # type: ignore

    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = login_form()
    if form.validate_on_submit():
        attempted_user = readers.query.filter_by(
            username=form.username.data).first()
        if attempted_user is None:
            flash(f'User does not exist : {
                  form.username.data}', category='danger')
        else:
            if attempted_user and attempted_user.check_password(attempted_password=form.password.data):
                login_user(attempted_user)
                flash(f'success! You are now logged in as : {
                      attempted_user.username}', category='success')
                return redirect(url_for('home'))
            else:
                flash('Username or password is incorrect', category='danger')

    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    username = current_user.username if current_user.is_authenticated else "User"
    logout_user()
    flash(f'"{username}" You have been logged out', category='info')
    return redirect(url_for('home'))


@app.route('/admin/delete_user/<string:user_email>', methods=['POST'])
def delete_user(user_email):
    user = readers.query.filter_by(email=user_email).first()
    if user:
        db.session.delete(user)
        db.session.commit()
        flash(f"{user.username}'s account was deleted successful",
              category='success')
    else:
        flash(f"user's account not found", category='danger')
    return redirect(url_for('user_list'))


@app.route('/admin/make_librarian/<string:user_email>', methods=['POST'])
def make_librarian(user_email):
    librarian = readers.query.filter_by(email=user_email).first()
    if librarian:
        librarian.is_librarian = True
        db.session.commit()
        flash(f'{librarian.username} now has librarian access',
              category='success')
    else:
        flash(f'username not found', category='danger')
    return redirect(url_for('user_list'))


@app.route('/admin/delete_librarian/<string:user_email>', methods=['POST'])
def delete_librarian(user_email):
    librarian = readers.query.filter_by(email=user_email).first()
    if librarian:
        librarian.is_librarian = False
        db.session.commit()
        flash(
            f"{librarian.username}'s librarian access has been revoked", category='danger')
    return redirect(url_for('librarian_list'))


@app.route('/admin/user_list')
def user_list():
    users = readers.query.filter(readers.username != 'admin').all()
    return render_template('user.html', users=users)


@app.route('/admin/librarian_list')
def librarian_list():
    librarians = readers.query.filter(
        readers.is_librarian == True, readers.username != 'admin').all()
    return render_template('librarians.html', librarians=librarians)


@app.route('/book_request')
@login_required
@admin_or_lib_required
def book_request():
    request=requests.query.all()
    return render_template('request.html', request=request)


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


allowed_file = {'txt', 'pdf'}

def allowed(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_file

@app.route('/admin/add_book', methods=['GET', 'POST'])
@login_required
@admin_or_lib_required
def add_book():
    form = addbookform()
    form.uploader.data = current_user.username
    if form.validate_on_submit():
        isbn_no = form.isbn_no.data
        title = form.title.data
        isbn_err = bookshelf.query.filter_by(isbn_no=isbn_no).first()
        title_err = bookshelf.query.filter_by(title=title).first()

        if isbn_err:
            flash(f'Book with ISBN number "{
                  isbn_no}" already exists in the library', category='danger')
        elif title_err:
            flash(f'Book with title "{
                  title}" already exists in the library. Please choose a different title.', category='danger')

        else:
            try:
                upload_folder = current_app.config['UPLOAD_FOLDER']
                book_file = form.book_file.data
                if book_file and allowed(book_file.filename):
                    file_name = secure_filename(book_file.filename)
                    file_path = os.path.join(upload_folder, file_name)
                    book_file.save(os.path.join(upload_folder, file_name))

                new_book_entry = bookshelf(  # type:ignore
                    title=form.title.data,
                    author=form.author.data,
                    genre=form.genre.data,
                    isbn_no=form.isbn_no.data,
                    uploader=current_user.username,
                    synopsis=form.synopsis.data,
                    file_name=file_name,  # Save the filename
                    file_path=file_path
                )

                db.session.add(new_book_entry)
                db.session.commit()
                flash('Book added successfully!', 'success')
                return redirect(url_for('add_book'))
            except Exception as err:
                flash(f'Something went wrong while adding the book: {
                      str(err)}', category='danger')
                db.session.rollback()

    return render_template('add_book.html', form=form)


@app.route('/admin/delete_book/<int:isbn_no>', methods=['POST'])
@login_required
@admin_or_lib_required
def delete_book(isbn_no):
    book = bookshelf.query.get(isbn_no)
    if book:
        db.session.delete(book)
        db.session.commit()
        flash(f'Book "{book.title}" has been deleted successfully!', 'success')

        # To Delete the book file from the system
        file_path = os.path.join(
            current_app.config['UPLOAD_FOLDER'], book.file_name)
        if os.path.exists(file_path):
            os.remove(file_path)

    else:
        flash(f'Book not found', 'danger')
    return redirect(url_for('home'))


