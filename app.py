from flask import Flask

app = Flask(__name__)


@app.route('/login')
def login():
    pass


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
