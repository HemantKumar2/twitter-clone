from flask import url_for,render_template,url_for,flash,redirect, request
from sqlalchemy.sql import func
from project import app,db,bcrypt
from project.forms import RegisterationForm,LoginForm,AnchorForm,CreateNewsForm,DeleteNewsForm,UpdateAccountForm,ChangePasswordForm
from project.model import User,Post,Follow,Like,News
from flask_login import login_user, current_user, logout_user, login_required
import os, secrets
from PIL import Image
from functools import wraps
from werkzeug.security import check_password_hash,generate_password_hash
from flask_bcrypt import check_password_hash
import random
from datetime import datetime
from sqlalchemy import or_,and_

def logout_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            return redirect(url_for('home'))  
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@logout_required
def welcome():
    news1=News.query.all()
    suggested_users = db.session.query(User).order_by(func.random()).limit(5).all()
    return render_template("main.html",news=news1,suggested_users=suggested_users)



@app.route('/home')
@login_required
def home():
    user = current_user
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    followed_ids = db.session.query(Follow.following).filter_by(follower=current_user.id).subquery()
    #feed_posts = Post.query.filter((Post.user_id == current_user.id) | (Post.user_id.in_(followed_ids))).order_by(Post.date_posted.desc()).all()
    feed_post = Post.query.filter(
    or_(
        Post.user_id == current_user.id,  # Posts by the logged-in user (public or private)
        and_(Post.is_public == True, Post.user_id.in_(
            db.session.query(Follow.following).filter_by(follower=current_user.id)
        ))
    )
).order_by(Post.date_posted.desc()).all()

    non_followed = User.query.filter(User.id.notin_(followed_ids), User.id != current_user.id).all()
    suggested_users = random.sample(non_followed, min(5, len(non_followed)))

    liked_posts_query = db.session.query(Like.post_id).filter_by(user_id=user.id).all()
    liked_posts = [post_id for post_id, in liked_posts_query]


    return render_template("home.html",suggested_users=suggested_users,user=user,image_file=image_file,liked_posts=liked_posts,feed_post=feed_post)

@app.route('/register', methods=['GET','POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegisterationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', title='Register', form=form)

@app.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            print('logged in')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for("welcome"))


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account',
                           image_file=image_file, form=form)

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn




@app.route('/anchor',methods=['GET','POST'])
def anchor():
    form=AnchorForm()
    if form.validate_on_submit():
        if form.email.data == 'twitter@gmail.com' and form.password.data == 'password':
            flash('You have been logged in!', 'success')
            return redirect(url_for('create_news'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template("anchor.html",form=form)

@app.route("/create_news")
def create_news():
    return render_template("create_news.html")

@app.route("/create",methods=['GET','POST'])
def create():
    form=CreateNewsForm()
    if form.validate_on_submit():
        news=News(title=form.title.data,news=form.news.data)
        db.session.add(news)
        db.session.commit()
        flash("News Created ",'success')
        return redirect(url_for('create_news'))

    return render_template("create.html",form=form)



@app.route("/delete_news", methods=['GET', 'POST'])
def delete_news():
    news_list = News.query.all()  
    try:
        news_id = int(request.form.get('news_id'))  
        news_item = News.query.get(news_id)  

        if news_item:
            db.session.delete(news_item)
            db.session.commit()
            flash(f'News with ID {news_id} deleted successfully.', 'success')
        else:
            flash(f'News with ID {news_id} not found.', 'error')
    except (ValueError, TypeError):
        flash('Invalid ID. Please enter a number.', 'error')
    return render_template("delete_news.html", news=news_list)

@app.route("/news/<int:news_id>")
def news(news_id):
    news_item = News.query.get_or_404(news_id)  
    return render_template("news_article.html", news=news_item)


@app.route('/followers/<username>', methods=['GET', 'POST'])
@login_required
def followers(username):
    user = User.query.filter_by(username=username).first_or_404()
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    followers = [User.query.get(f.follower) for f in user.followers.all()] 
    return render_template('followers.html', user=user, followers=followers, image_file=image_file)



@app.route('/followings/<username>', methods=['GET', 'POST'])
@login_required
def followings(username):
    user = User.query.filter_by(username=username).first_or_404()
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    following_users = [User.query.get(f.following) for f in user.followings.all()] 
    return render_template('followings.html', user=user, following=following_users, image_file=image_file)


@app.route("/dashboard",methods=['GET','POST'])
@login_required
def dashboard():
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    #if username != current_user.username:
     #   abort(403)
    user_posts = Post.query.filter_by(user_id=current_user.id).order_by(Post.date_posted.desc()).all()
    user = current_user
    # user = User.query.filter_by(username=username).first_or_404()
    liked_posts_query = db.session.query(Like.post_id).filter_by(user_id=user.id).all()
    liked_posts = [post_id for post_id, in liked_posts_query]
    return render_template("dashboard.html",image_file=image_file,user=user,posts=user_posts,liked_posts=liked_posts)

@app.route("/change_password",methods=['GET','POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if check_password_hash(current_user.password, form.current_password.data):
            current_user.password = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
            db.session.commit()
            flash('Your password has been updated successfully.', 'success')
            return redirect(url_for('account'))
        else:
            flash('Current password is incorrect.', 'danger')
    return render_template('change_password.html', form=form)


@app.route("/search", methods=['GET', 'POST'])
@login_required
def search():
    user = current_user
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    suggested_users = db.session.query(User).filter(User.id != current_user.id).order_by(func.random()).limit(5).all()
    query = request.args.get('query')
    users = []
    if query:
        users = User.query.filter(User.username.ilike(f'%{query}%')).all()  
    return render_template("search.html", user=user, image_file=image_file, suggested_users=suggested_users, users=users,query=query)


@app.route('/user/<username>')
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    is_following = Follow.query.filter_by(follower=current_user.id, following=user.id).first() is not None
    return render_template('profile.html', user=user,is_following=is_following)

from flask import request, redirect, url_for, flash


@app.route('/follow/<username>', methods=['GET','POST'])
@login_required
def follow(username):
    user_to_follow = User.query.filter_by(username=username).first_or_404()

    if user_to_follow == current_user:
        flash("You cannot follow yourself.", category='warning')
        return redirect(url_for('profile', username=username))

    existing_follow = Follow.query.filter_by(follower=current_user.id, following=user_to_follow.id).first()

    if existing_follow:
        db.session.delete(existing_follow)
        flash(f"You have unfollowed {user_to_follow.username}.", category='info')
    else:
        new_follow = Follow(follower=current_user.id, following=user_to_follow.id)
        db.session.add(new_follow)
        flash(f"You are now following {user_to_follow.username}.", category='success')

    db.session.commit()

    return redirect(url_for('profile', username=username))

@app.route('/follow1/<username>', methods=['GET','POST'])
@login_required
def follow1(username):
    user_to_follow = User.query.filter_by(username=username).first_or_404()

    if user_to_follow == current_user:
        flash("You cannot follow yourself.", category='warning')
        return redirect(url_for('profile', username=username))

    existing_follow = Follow.query.filter_by(follower=current_user.id, following=user_to_follow.id).first()

    if existing_follow:
        db.session.delete(existing_follow)
        flash(f"You have unfollowed {user_to_follow.username}.", category='info')
    else:
        new_follow = Follow(follower=current_user.id, following=user_to_follow.id)
        db.session.add(new_follow)
        flash(f"You are now following {user_to_follow.username}.", category='success')

    db.session.commit()

    return redirect(url_for('home'))


@app.route('/tweet', methods=['POST'])
@login_required
def tweet():
    tweet_content = request.form.get('tweet_content')
    is_public = request.form.get('is_public') == 'on'
    if tweet_content:
        new_post = Post(content=tweet_content, user_id=current_user.id,is_public=is_public, date_posted=datetime.utcnow())
        db.session.add(new_post)
        db.session.commit()
        flash('Your tweet has been posted!', 'success')
    else:
        flash('Tweet content cannot be empty.', 'danger')

    return redirect(url_for('home'))


@app.route('/toggle_like/<int:post_id>', methods=['POST'])
@login_required
def toggle_like(post_id):
    post = Post.query.get_or_404(post_id)
    like = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()

    if like:
        db.session.delete(like)
        post.like_counter -= 1
    else:
        new_like = Like(user_id=current_user.id, post_id=post_id)
        db.session.add(new_like)
        post.like_counter += 1
    
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/edit_post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    if request.method == 'POST':
        post.content = request.form['content']
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('edit_post.html', post=post)


@app.route('/toggle_like1/<int:post_id>', methods=['POST'])
@login_required
def toggle_like1(post_id):
    post = Post.query.get_or_404(post_id)
    like = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()

    if like:
        db.session.delete(like)
        post.like_counter -= 1
    else:
        new_like = Like(user_id=current_user.id, post_id=post_id)
        db.session.add(new_like)
        post.like_counter += 1
    
    db.session.commit()
    return redirect(url_for('dashboard'))