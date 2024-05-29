from flask import Flask
from flask import Flask, render_template, request, redirect, url_for, make_response
from tools import DatabaseWorker
from datetime import datetime

app = Flask(__name__)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form.get('uname')
        password = request.form.get('psw')
        db = DatabaseWorker('Reddit.db')
        user = db.search(f"SELECT * FROM users WHERE username='{uname}'")
        if user:
            if user[2] == password:
                response = make_response(redirect(url_for('get_all_posts')))
                response.set_cookie('user_id', str(user[0]))
                db.close()
                return response


@app.route('/register')
def register():
    pass

@app.route('/recover')


@app.route('/feed/home')


@app.route('/feed/top')


@app.route('/subreddit/<str:sub_name>/')


@app.route('/subreddit/<str:sub_name>/comments/<str:post_name>/')


@app.route('/subreddit/<str:sub_name>/submit_post')


@app.route('/user/<str:user_name>/')


@app.route('/profile')


@app.route('/profile/edit')


@app.route('/search')

if __name__ == '__main__':
    app.run()
