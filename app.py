import os

from flask import Flask, render_template, request, redirect, url_for, make_response, flash
from werkzeug.utils import secure_filename
from tools import DatabaseWorker, check_hash, make_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = 'static/uploads/'
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
    posts = db.search(query='''SELECT posts.id, posts.title, posts.content, users.id AS user_id, users.username, posts.post_time, 
                               posts.upvotes - posts.downvotes, posts.subreddit, posts.image_url 
                               FROM posts 
                               JOIN users ON posts.user_id = users.id 
                               ORDER BY posts.post_time DESC''', multiple=True)
    subreddits = db.search(query='SELECT name FROM subreddits', multiple=True)
    db.close()
    return render_template('home.html', posts=posts, subreddits=subreddits)



@app.route('/logout')
def logout():
    response = make_response(redirect(url_for('login')))
    response.set_cookie('user_id', "", expires=0)
    return response


@app.route('/profile/<int:user_id>', methods=['GET'])
def profile(user_id):
    current_user_id = request.cookies.get('user_id')
    is_own_profile = current_user_id == str(user_id)
    db = DatabaseWorker('Reddit.db')
    user = db.search(query=f"SELECT username, description FROM users WHERE id={user_id}", multiple=False)
    subreddits = db.search(query=f"SELECT subreddits.name FROM subreddits JOIN user_subreddits ON subreddits.id = user_subreddits.subreddit_id WHERE user_subreddits.user_id={user_id}", multiple=True)
    following = db.search(query=f"SELECT users.username, users.id FROM users JOIN user_followers ON users.id = user_followers.user_id WHERE user_followers.follower_id={user_id}", multiple=True)
    followers = db.search(query=f"SELECT users.username, users.id FROM users JOIN user_followers ON users.id = user_followers.follower_id WHERE user_followers.user_id={user_id}", multiple=True)
    posts = db.search(query=f"SELECT id, title, content, post_time FROM posts WHERE user_id={user_id}", multiple=True)
    is_following = db.search(query=f"SELECT 1 FROM user_followers WHERE user_id={user_id} AND follower_id={current_user_id}", multiple=False) is not None
    db.close()
    return render_template('profile.html', user=user, subreddits=subreddits, following=following, followers=followers, posts=posts, is_own_profile=is_own_profile, is_following=is_following, user_id=user_id)

@app.route('/update_description/<int:user_id>', methods=['POST'])
def update_description(user_id):
    current_user_id = request.cookies.get('user_id')
    if current_user_id != str(user_id):
        return redirect(url_for('profile', user_id=user_id))

    description = request.form.get('description')
    db = DatabaseWorker('Reddit.db')
    db.run_query(query=f"UPDATE users SET description='{description}' WHERE id={user_id}")
    db.close()
    return redirect(url_for('profile', user_id=user_id))

@app.route('/toggle_follow_user/<int:user_id>', methods=['POST'])
def toggle_follow_user(user_id):
    current_user_id = request.cookies.get('user_id')
    if current_user_id == str(user_id):
        return redirect(url_for('profile', user_id=user_id))

    db = DatabaseWorker('Reddit.db')
    is_following = db.search(query=f"SELECT 1 FROM user_followers WHERE user_id={user_id} AND follower_id={current_user_id}", multiple=False) is not None
    if is_following:
        db.run_query(query=f"DELETE FROM user_followers WHERE user_id={user_id} AND follower_id={current_user_id}")
    else:
        db.run_query(query=f"INSERT INTO user_followers (user_id, follower_id) VALUES ({user_id}, {current_user_id})")
    db.close()
    return redirect(url_for('profile', user_id=user_id))


@app.route('/post/<int:post_id>', methods=['GET', 'POST'])
def view_post(post_id):
    current_user_id = request.cookies.get('user_id')
    db = DatabaseWorker('Reddit.db')
    post = db.search(query=f'SELECT posts.id, posts.title, posts.content, users.id AS user_id, posts.image_url, users.username, posts.post_time FROM posts JOIN users ON posts.user_id = users.id WHERE posts.id={post_id}', multiple=False)
    comments = db.search(query=f'SELECT comments.id, comments.content, users.id AS user_id, users.username, comments.created_at FROM comments JOIN users ON comments.user_id = users.id WHERE comments.post_id={post_id}', multiple=True)

    if request.method == 'POST':
        content = request.form.get('comment')
        user_id = request.cookies.get('user_id')
        db.run_query(query=f"INSERT INTO comments (post_id, user_id, content) VALUES ({post_id}, {user_id}, '{content}')")
        db.close()
        return redirect(url_for('view_post', post_id=post_id))

    db.close()
    return render_template('view_post.html', post=post, comments=comments, current_user_id=int(current_user_id))


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


@app.route('/post/<int:post_id>/vote/<string:vote>', methods=['POST'])
def vote_post(post_id, vote):
    user_id = request.cookies.get('user_id')
    if not user_id:
        flash('You must be logged in to vote.')
        return redirect(url_for('login'))

    db = DatabaseWorker('Reddit.db')
    existing_vote = db.search(query=f"SELECT * FROM votes WHERE user_id={user_id} AND post_id={post_id}", multiple=False)

    if existing_vote:
        if (existing_vote[3] == 1 and vote == 'up') or (existing_vote[3] == -1 and vote == 'down'):
            db.run_query(query=f"DELETE FROM votes WHERE user_id={user_id} AND post_id={post_id}")
            if vote == 'up':
                db.run_query(query=f"UPDATE posts SET upvotes = upvotes - 1 WHERE id={post_id}")
            else:
                db.run_query(query=f"UPDATE posts SET downvotes = downvotes - 1 WHERE id={post_id}")
        else:
            db.run_query(query=f"UPDATE votes SET vote = {1 if vote == 'up' else -1} WHERE user_id={user_id} AND post_id={post_id}")
            if vote == 'up':
                db.run_query(query=f"UPDATE posts SET upvotes = upvotes + 1, downvotes = downvotes - 1 WHERE id={post_id}")
            else:
                db.run_query(query=f"UPDATE posts SET upvotes = upvotes - 1, downvotes = downvotes + 1 WHERE id={post_id}")
    else:
        vote_value = 1 if vote == 'up' else -1
        db.run_query(query=f"INSERT INTO votes (user_id, post_id, vote) VALUES ({user_id}, {post_id}, {vote_value})")
        if vote == 'up':
            db.run_query(query=f"UPDATE posts SET upvotes = upvotes + 1 WHERE id={post_id}")
        elif vote == 'down':
            db.run_query(query=f"UPDATE posts SET downvotes = downvotes + 1 WHERE id={post_id}")

    db.close()
    return redirect(url_for('home'))


@app.route('/subreddit/<string:subreddit_name>', methods=['GET', 'POST'])
def view_subreddit(subreddit_name):
    user_id = request.cookies.get('user_id')
    db = DatabaseWorker('Reddit.db')
    subreddit = db.search(query=f"SELECT id, name, description FROM subreddits WHERE name='{subreddit_name}'", multiple=False)

    if not subreddit:
        flash('Subreddit not found.')
        return redirect(url_for('home'))

    subreddit_id = subreddit[0]
    followers = db.search(query=f"SELECT COUNT(*) FROM user_subreddits WHERE subreddit_id={subreddit_id}", multiple=False)[0]
    following = db.search(query=f"SELECT * FROM user_subreddits WHERE subreddit_id={subreddit_id} AND user_id={user_id}", multiple=False)

    posts = db.search(query=f'''SELECT posts.id, posts.title, posts.content, users.username, posts.post_time, 
                               posts.upvotes - posts.downvotes, posts.image_url 
                               FROM posts 
                               JOIN users ON posts.user_id = users.id 
                               WHERE posts.subreddit='{subreddit_name}' 
                               ORDER BY posts.post_time DESC''', multiple=True)

    subreddit_data = {
        'id': subreddit[0],
        'name': subreddit[1],
        'description': subreddit[2],
        'followers': followers,
        'following': bool(following)
    }

    db.close()
    return render_template('subreddit.html', subreddit=subreddit_data, posts=posts)

@app.route('/subreddit/<string:subreddit_name>/follow', methods=['POST'])
def follow_subreddit(subreddit_name):
    user_id = request.cookies.get('user_id')
    db = DatabaseWorker('Reddit.db')
    subreddit = db.search(query=f"SELECT id FROM subreddits WHERE name='{subreddit_name}'", multiple=False)
    if subreddit:
        subreddit_id = subreddit[0]
        db.run_query(query=f"INSERT INTO user_subreddits (user_id, subreddit_id) VALUES ({user_id}, {subreddit_id})")
    db.close()
    return redirect(url_for('view_subreddit', subreddit_name=subreddit_name))

@app.route('/subreddit/<string:subreddit_name>/unfollow', methods=['POST'])
def unfollow_subreddit(subreddit_name):
    user_id = request.cookies.get('user_id')
    db = DatabaseWorker('Reddit.db')
    subreddit = db.search(query=f"SELECT id FROM subreddits WHERE name='{subreddit_name}'", multiple=False)
    if subreddit:
        subreddit_id = subreddit[0]
        db.run_query(query=f"DELETE FROM user_subreddits WHERE user_id={user_id} AND subreddit_id={subreddit_id}")
    db.close()
    return redirect(url_for('view_subreddit', subreddit_name=subreddit_name))


if __name__ == '__main__':
    app.run()
