from flask import Flask
from flask import Flask, render_template, request, redirect, url_for, make_response, flash
from tools import DatabaseWorker, check_hash, make_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        uname = request.form.get('uname')
        password = request.form.get('psw')
        email = request.form.get('email')

        hashed_password = make_hash(password)

        db = DatabaseWorker('Reddit.db')
        existing_user = db.search(query=f"SELECT * FROM users WHERE username='{uname}'", multiple=False)

        if existing_user:
            db.close()
            flash('Username already exists. Please choose a different one.')
            return redirect(url_for('register'))

        db.run_query(query=f"INSERT INTO users (username, password, email) VALUES ('{uname}', '{hashed_password}', '{email}')")
        db.close()

        flash('Registration successful! You can now log in.')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form.get('uname')
        password = request.form.get('psw')
        db = DatabaseWorker('Reddit.db')
        user = db.search(f"SELECT * FROM users WHERE username='{uname}'")
        db.close()

        if user and check_hash(password, user[2]):
            user_id = user[0]
            response = make_response(redirect(url_for('home')))
            response.set_cookie('user_id', str(user[0]))
            db.close()
            return response

        flash('Invalid username or password')
    return render_template('login.html')




# @app.route('/recover')
#
#
@app.route('/home')
def home():
    db = DatabaseWorker('Reddit.db')
    posts = db.search("SELECT * FROM posts", multiple=True)
    db.close()
    return render_template('home.html', posts=posts)


# @app.route('/feed/top')
#
#
# @app.route('/subreddit/<str:sub_name>/')
#
#
# @app.route('/subreddit/<str:sub_name>/comments/<str:post_name>/')
#
#
# @app.route('/subreddit/<str:sub_name>/submit_post')
#
#
# @app.route('/user/<str:user_name>/')
#
#
# @app.route('/profile')
#
#
# @app.route('/profile/edit')
#
#
# @app.route('/search')

if __name__ == '__main__':
    app.run()
