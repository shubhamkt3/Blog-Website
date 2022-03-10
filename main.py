from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_bootstrap import Bootstrap
import sqlite3
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, URL
from flask_ckeditor import CKEditor, CKEditorField
from forms import RegisterForm, CreatePostForm, LoginForm, CommentForm
import datetime as dt
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from functools import wraps



app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
db = sqlite3.connect("posts.db", check_same_thread=False)
cursor = db.cursor()

login_manager = LoginManager()
login_manager.init_app(app)

# cursor.execute("CREATE TABLE user (id INTEGER PRIMARY KEY, email varchar(250) NOT NULL UNIQUE, password varchar(250) NOT NULL, name varchar(250) NOT NULL)")
# db.commit()

# cursor.execute('create table blog_post (id INTEGER PRIMARY KEY, title varchar(250) NOT NULL, date varchar(250), body varchar(250), author varchar(250), img_url varchar(250), subtitle varchar(250), author_id int , FOREIGN KEY (author_id) REFERENCES user(id))')
# db.commit()

# cursor.execute('create table comment (id INTEGER PRIMARY KEY, author_id int, author varchar(250) NOT NULL, post_id int, text varchar(250) NOT NULL, FOREIGN KEY (author_id) REFERENCES user(id), FOREIGN KEY (post_id) REFERENCES blog_post(id))')
# db.commit()


class User(UserMixin):
    def __init__(self, id, email, password, name):
          self.id = str(id)
          self.email = email
          self.password = password
          self.name = name
          self.authenticated = False
     
    def is_active(self):
          return self.is_active()
    def is_anonymous(self):
          return False
    def is_authenticated(self):
          return self.authenticated
    def get_id(self):
          return self.id     
#Line below only required once, when creating DB. 
# db.create_all()

def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id!="2":
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function

@login_manager.user_loader
def load_user(user_id):
    cursor.execute('Select * from user where id = ?', [user_id])
    lu = cursor.fetchone()
    if lu is None:
        return None
    else:
        return User(int(lu[0]), lu[1], lu[2], lu[3])


@app.route('/')
def get_all_posts():
    cursor.execute('Select * from blog_post')
    posts = cursor.fetchall()
    return render_template("index.html", all_posts=posts, logged_in=current_user.is_authenticated, user=current_user)


@app.route("/post/<int:index>", methods = ['POST', 'GET'])
def show_post(index):
    requested_post = None
    form = CommentForm()
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for("login"))
        
        cursor.execute('insert into comment (author_id, author, post_id, text) values (?,?,?,?)',[current_user.id, current_user.name, index, form.comment.data])
        db.commit()
   
    cursor.execute('Select * from comment where post_id=?',[index])
    all_comment = cursor.fetchall()
    posts = cursor.execute('Select * from blog_post')
    for blog_post in posts:
        if blog_post[0] == index:
            requested_post = blog_post
    return render_template("post.html", post=requested_post, logged_in=current_user.is_authenticated, user=current_user, form=form, comments=all_comment)

@app.route("/new-post", methods=['POST','GET'])
@admin_only
def new_post():
    if request.method=='GET':
        form = CreatePostForm()
        return render_template("make-post.html", form=form, is_edit=False, logged_in=current_user.is_authenticated)
    else:
        x = dt.datetime.now()
        form_data = (request.form.get("title"),x.strftime("%B %d,%Y"),request.form.get("body"),request.form.get("author"),request.form.get("img_url"),request.form.get("subtitle"),current_user.id)
        cursor.execute('Insert into blog_post (title,date,body,author,img_url,subtitle,author_id) values (?,?,?,?,?,?,?)',form_data)
        db.commit()
        return redirect("/")
    
	
@app.route("/edit-post/<post_id>", methods=['POST','GET'])
@admin_only
def edit_post(post_id):
    if request.method=='GET':
        requested_post = None
        post_data = cursor.execute('Select * from blog_post where id=?',[post_id])
        for n in post_data:
            requested_post= n
        form = CreatePostForm(
            title = requested_post[1],
            subtitle = requested_post[6],
            author = requested_post[4],
            img_url = requested_post[5],
            body = requested_post[3]
            )
        return render_template("make-post.html", form=form, is_edit=True, logged_in=current_user.is_authenticated)
    
    else:
        updated_data = (request.form.get("title"),request.form.get("body"),request.form.get("author"),request.form.get("img_url"),request.form.get("subtitle"),post_id)
        cursor.execute('update blog_post set title=?,body=?,author=?,img_url=?,subtitle=? where id=?', updated_data)
        db.commit()
        return redirect(url_for('show_post', index=post_id))

@app.route("/delete/<post_id>")
@admin_only
def delete_post(post_id):
    cursor.execute('Delete from blog_post where id=?',[post_id])
    db.commit()
    
    return redirect(url_for("get_all_posts"))
       
@app.route("/register", methods = ["POST","GET"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        cursor.execute('select * from user where email=?',[form.email.data])
        row = cursor.fetchone()
        if row is None:
            
            hash_and_salted_password = generate_password_hash(form.password.data, method='pbkdf2:sha256', salt_length=8 )
            cursor.execute('Insert into user (email,password,name) values (?,?,?)',[form.email.data, hash_and_salted_password, form.name.data])
            db.commit()
            
            return redirect(url_for("get_all_posts"))
        
        else:
            flash("You have already signed up with that email, log in instead")
            return redirect(url_for('login'))
    return render_template("register.html", form = form, logged_in=current_user.is_authenticated)

@app.route("/login", methods= ["POST","GET"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        
        cursor.execute('select * from user where email=?',[email])
        lu = cursor.fetchone()
        if lu is None:
            flash("That email does not exist, please try again")
            return redirect(url_for('login'))
        else:
            user = list(lu)
            Us = load_user(user[0])
            if check_password_hash(user[2], password):
                login_user(Us)
                return redirect(url_for("get_all_posts"))
            else:
                flash("Password incorrect, please try again")
                return redirect(url_for('login'))
    return render_template("login.html", form=form, logged_in=current_user.is_authenticated)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("get_all_posts"))
    
@app.route("/about")
def about():
    return render_template("about.html", logged_in=current_user.is_authenticated)


@app.route("/contact")
def contact():
    return render_template("contact.html", logged_in=current_user.is_authenticated)

if __name__ == "__main__":
    app.run(debug=True)