import os

from flask import Flask, render_template, request, redirect, url_for, make_response, flash
from werkzeug.utils import secure_filename
from tools import DatabaseWorker, check_hash, make_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = 'static'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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

        if user and check_hash(password, user[3]):
            user_id = user[0]
            response = make_response(redirect(url_for('home')))
            response.set_cookie('user_id', str(user[0]))
            db.close()
            return response

        flash('Invalid username or password')
    return render_template('login.html')



@app.route('/home')
def home():
    db = DatabaseWorker('Reddit.db')
    posts = db.search("SELECT * FROM posts", multiple=True)
    print(posts)
    db.close()
    return render_template('home.html', posts=posts)


@app.route('/logout')
def logout():
    response = make_response(redirect(url_for('login')))
    response.set_cookie('user_id', "", expires=0)
    return response


@app.route('/profile/<int:user_id>')
def profile(user_id):
    db = DatabaseWorker('Reddit.db')

    # Fetch user details
    user = db.search(query=f"SELECT username, description FROM users WHERE id={user_id}", multiple=False)

    # Fetch subreddits followed by user
    subreddits = db.search(
        query=f"SELECT subreddits.name FROM subreddits JOIN user_subreddits ON subreddits.id = user_subreddits.subreddit_id WHERE user_subreddits.user_id={user_id}",
        multiple=True)

    # Fetch users followed by user
    following = db.search(
        query=f"SELECT users.username FROM users JOIN user_followers ON users.id = user_followers.follower_id WHERE user_followers.user_id={user_id}",
        multiple=True)

    # Fetch followers of the user
    followers = db.search(
        query=f"SELECT users.username FROM users JOIN user_followers ON users.id = user_followers.user_id WHERE user_followers.follower_id={user_id}",
        multiple=True)

    # Fetch posts created by the user
    posts = db.search(query=f"SELECT id, title, content, post_time FROM posts WHERE user_id={user_id}", multiple=True)

    db.close()
    return render_template('profile.html', user=user, subreddits=subreddits, following=following, followers=followers,
                           posts=posts)


@app.route('/post/<int:post_id>', methods=['GET', 'POST'])
def view_post(post_id):
    db = DatabaseWorker('Reddit.db')
    post = db.search(query=f'SELECT posts.id, posts.title, posts.content, posts.image_url, users.username, posts.post_time FROM posts JOIN users ON posts.user_id = users.id WHERE posts.id={post_id}', multiple=False)
    comments = db.search(query=f'SELECT comments.id, comments.content, users.username, comments.created_at FROM comments JOIN users ON comments.user_id = users.id WHERE comments.post_id={post_id}', multiple=True)

    if request.method == 'POST':
        content = request.form.get('comment')
        user_id = request.cookies.get('user_id')
        db.run_query(query=f"INSERT INTO comments (post_id, user_id, content) VALUES ({post_id}, {user_id}, '{content}')")
        db.close()
        return redirect(url_for('view_post', post_id=post_id))

    db.close()
    return render_template('view_post.html', post=post, comments=comments)


@app.route('/post/<int:post_id>/edit_comment/<int:comment_id>', methods=['GET', 'POST'])
def edit_comment(post_id, comment_id):
    db = DatabaseWorker('Reddit.db')
    comment = db.search(query=f'SELECT content FROM comments WHERE id={comment_id}', multiple=False)

    if request.method == 'POST':
        new_content = request.form.get('content')
        db.run_query(query=f"UPDATE comments SET content='{new_content}' WHERE id={comment_id}")
        db.close()
        return redirect(url_for('view_post', post_id=post_id))

    db.close()
    return render_template('edit_comment.html', post_id=post_id, comment_id=comment_id, content=comment[0])

@app.route('/post/<int:post_id>/delete_comment/<int:comment_id>', methods=['POST'])
def delete_comment(post_id, comment_id):
    db = DatabaseWorker('Reddit.db')
    db.run_query(query=f"DELETE FROM comments WHERE id={comment_id}")
    db.close()
    return redirect(url_for('view_post', post_id=post_id))



@app.route('/create_post', methods=['GET', 'POST'])
def create_post():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        subreddit = request.form.get('subreddit')
        user_id = request.cookies.get('user_id')
        file = request.files['image']

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            image_url = url_for('static', filename='uploads/' + filename)
        else:
            image_url = None

        db = DatabaseWorker('Reddit.db')
        db.run_query(
            query=f"INSERT INTO posts (title, content, user_id, upvotes, downvotes, subreddit, image_url) VALUES ('{title}', '{content}', {user_id}, 0, 0, '{subreddit}', '{image_url}')")
        db.close()
        return redirect(url_for('home'))

    db = DatabaseWorker('Reddit.db')
    subreddits = db.search(query='SELECT name FROM subreddits', multiple=True)
    db.close()
    return render_template('create_post.html', subreddits=subreddits)
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
