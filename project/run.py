from lib_manager import app

#checks if the run.py file has been executed directly and not imported

if __name__ == '__main__':
    app.run(debug=True)