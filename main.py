from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import login_user, logout_user, login_required, UserMixin
import MySQLdb
import re

app = Flask(__name__)

# Change this to your secret key (can be anything, it's for extra protection)
app.secret_key = '1a2b3c4d5e6d7g8h9i10'

# Enter your database connection details below
db_config = {
    'host': 'localhost',
    'user': 'root',
    'passwd': '111222333',  # Replace with your database password.
    'db': 'loginapp'
}

# http://localhost:5000/login - this will be the login page, we need to use both GET and POST requests
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Output message if something goes wrong...
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']

        # Connect to the database
        db = MySQLdb.connect(**db_config)
        cursor = db.cursor(MySQLdb.cursors.DictCursor)

        # Check if account exists using MySQL
        cursor.execute('SELECT * FROM accounts WHERE username = %s AND password = %s', (username, password))
        # Fetch one record and return result
        account = cursor.fetchone()

        # Close the cursor and connection
        cursor.close()
        db.close()

        # If account exists in accounts table in our database
        if account:
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            # Redirect to home page
            return redirect(url_for('home'))
        else:
            # Account doesn't exist or username/password incorrect
            flash("Incorrect username/password!", "danger")
    return render_template('auth/login.html', title="登录 | Fudan EGA")


# http://localhost:5000/register
# This will be the registration page, we need to use both GET and POST requests
@app.route('/register', methods=['GET', 'POST'])
def register():
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        email = request.form['email']

        # Connect to the database
        db = MySQLdb.connect(**db_config)
        cursor = db.cursor(MySQLdb.cursors.DictCursor)

        # Check if account exists using MySQL
        cursor.execute("SELECT * FROM accounts WHERE username LIKE %s", [username])
        account = cursor.fetchone()

        # If account exists show error and validation checks
        if account:
            flash("Account already exists!", "danger")
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash("Invalid email address!", "danger")
        elif not re.match(r'[A-Za-z0-9]+', username):
            flash("Username must contain only characters and numbers!", "danger")
        elif not username or not password or not email:
            flash("Please fill out the form!", "danger")
        elif password != confirm_password:  # Check if passwords match
            flash("Passwords do not match!", "danger")
        else:
            # Account doesn't exist and the form data is valid, now insert new account into accounts table
            cursor.execute('INSERT INTO accounts (username, email, password) VALUES (%s, %s, %s)',
                           (username, email, password))
            db.commit()
            flash("You have successfully registered!", "success")
            return redirect(url_for('login'))

        # Close the cursor and connection
        cursor.close()
        db.close()

    elif request.method == 'POST':
        # Form is empty... (no POST data)
        flash("Please fill out the form!", "danger")

    # Show registration form with message (if any)
    return render_template('auth/register.html', title="注册 | Fudan EGA")


# http://localhost:5000/
# This will be the home page, only accessible for logged-in users
@app.route('/')
def home():
    # Check if user is logged in
    logged_in = 'loggedin' in session
    if logged_in:
        username = session['username']
    else:
        username = None

    # 从数据库读取文章数据
    db = MySQLdb.connect(**db_config)
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT id, title, published_date, url FROM article')
    articles = cursor.fetchall()
    print(articles)

    # 关闭游标和连接
    cursor.close()
    db.close()

    return render_template('home/home.html', username=username, title="首页 | Fudan EGA", logged_in=logged_in, articles=articles)


@app.route('/profile')
def profile():
    # Check if user is logged in
    if 'loggedin' in session:
        # Connect to the database
        db = MySQLdb.connect(**db_config)
        cursor = db.cursor(MySQLdb.cursors.DictCursor)

        # Get user's account details from the database
        cursor.execute('SELECT * FROM accounts WHERE id = %s', (session['id'],))
        account = cursor.fetchone()

        # Close the cursor and connection
        cursor.close()
        db.close()

        # Pass the account details to the template
        return render_template('auth/profile.html',
                               username=account['username'],
                               email=account['email'],
                               password=account['password'],
                               title="Profile")

    # User is not logged in, redirect to login page
    return redirect(url_for('login'))


# http://localhost:5000/logout
@app.route('/logout')
def logout():
    # Clear all data in session, this will log out the user
    session.clear()
    # Redirect to home page after logging out
    flash("You have been logged out!", "success")
    return redirect(url_for('home'))

# 处理文章列表的View functions
@app.route('/add_article', methods=['POST'])
def add_article():
    if 'loggedin' in session:
        title = request.form['title']
        published_date = request.form['published_date']
        url = request.form['url']
        try:
            db = MySQLdb.connect(**db_config)  # 连接到数据库
            cursor = db.cursor()
            cursor.execute('INSERT INTO article (title, published_date, url) VALUES (%s, %s, %s)', (title, published_date, url))
            db.commit()  # 提交事务
            flash("Article added successfully!", "success")
        except MySQLdb.Error as e:
            db.rollback()  # 回滚事务
            flash(f"An error occurred while adding the article: {str(e)}", "danger")
        finally:
            cursor.close()  # 确保游标关闭
            db.close()  # 确保数据库连接关闭
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/edit_article/<int:id>', methods=['GET', 'POST'])
def edit_article(id):
    db = MySQLdb.connect(**db_config)  # 连接到数据库
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST':
        title = request.form['title']
        published_date = request.form['published_date']
        try:
            cursor.execute('UPDATE article SET title = %s, published_date = %s WHERE id = %s',
                           (title, published_date, id))
            db.commit()  # 提交事务
            flash("Article updated successfully!", "success")
        except MySQLdb.Error as e:
            db.rollback()  # 回滚事务
            flash(f"An error occurred while updating the article: {str(e)}", "danger")
        finally:
            cursor.close()  # 确保游标关闭
            db.close()  # 确保数据库连接关闭
        return redirect(url_for('home'))

    # 获取要编辑的文章信息
    cursor.execute('SELECT * FROM article WHERE id = %s', (id,))
    article = cursor.fetchone()
    cursor.close()  # 关闭游标
    db.close()  # 关闭数据库连接
    return render_template('home/edit.html', article=article, title="文章编辑 | Fudan EGA")

@app.route('/delete_article/<int:id>')
def delete_article(id):
    if 'loggedin' in session:  # 确保用户已登录
        try:
            db = MySQLdb.connect(**db_config)  # 连接到数据库
            cursor = db.cursor()
            cursor.execute('DELETE FROM article WHERE id = %s', (id,))
            db.commit()  # 提交事务
            flash("Article deleted successfully!", "success")
        except MySQLdb.Error as e:
            db.rollback()  # 回滚事务
            flash(f"An error occurred while deleting the article: {str(e)}", "danger")
        finally:
            cursor.close()  # 确保游标关闭
            db.close()  # 确保数据库连接关闭
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/activities')
def activities():

    logged_in = 'loggedin' in session

    # 连接到数据库
    db = MySQLdb.connect(**db_config)
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    # 执行查询
    cursor.execute('SELECT id, name, date, location, url FROM activities')
    activities = cursor.fetchall()

    # 关闭数据库连接
    cursor.close()
    db.close()

    # 将数据传递给模板
    return render_template('home/activities.html', logged_in=logged_in, activities=activities, title="活动 | Fudan EGA")

# 处理文章列表的View functions
@app.route('/add_activity', methods=['POST'])
def add_activity():
    if 'loggedin' in session:
        name = request.form['name']
        date = request.form['date']
        location = request.form['location']
        url = request.form['url']

        try:
            db = MySQLdb.connect(**db_config)  # 连接到数据库
            cursor = db.cursor()
            cursor.execute('INSERT INTO activities (name, date, location, url) VALUES (%s, %s, %s, %s)', (name, date, location, url))
            db.commit()  # 提交事务
            flash("Article added successfully!", "success")
        except MySQLdb.Error as e:
            db.rollback()  # 回滚事务
            flash(f"An error occurred while adding the activity: {str(e)}", "danger")
        finally:
            cursor.close()  # 确保游标关闭
            db.close()  # 确保数据库连接关闭
        return redirect(url_for('activities'))
    return redirect(url_for('login'))

@app.route('/edit_activity/<int:id>', methods=['GET', 'POST'])
def edit_activity(id):
    db = MySQLdb.connect(**db_config)  # 连接到数据库
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST':
        name = request.form['name']
        date = request.form['date']
        location = request.form['location']
        url = request.form['url']
        try:
            cursor.execute('UPDATE activities SET name = %s, date = %s, location = %s, url = %s WHERE id = %s',
                           (name, date, location, url, id))
            db.commit()  # 提交事务
            flash("Activity updated successfully!", "success")
        except MySQLdb.Error as e:
            db.rollback()  # 回滚事务
            flash(f"An error occurred while updating the activity: {str(e)}", "danger")
        finally:
            cursor.close()  # 确保游标关闭
            db.close()  # 确保数据库连接关闭
        return redirect(url_for('activities'))

    # 获取要编辑的文章信息
    cursor.execute('SELECT * FROM activities WHERE id = %s', (id,))
    activity = cursor.fetchone()
    cursor.close()  # 关闭游标
    db.close()  # 关闭数据库连接
    return render_template('home/act_edit.html', activity=activity, title="活动编辑 | Fudan EGA")

@app.route('/delete_article/<int:id>')
def delete_activity(id):
    if 'loggedin' in session:  # 确保用户已登录
        try:
            db = MySQLdb.connect(**db_config)  # 连接到数据库
            cursor = db.cursor()
            cursor.execute('DELETE FROM article WHERE id = %s', (id,))
            db.commit()  # 提交事务
            flash("Article deleted successfully!", "success")
        except MySQLdb.Error as e:
            db.rollback()  # 回滚事务
            flash(f"An error occurred while deleting the article: {str(e)}", "danger")
        finally:
            cursor.close()  # 确保游标关闭
            db.close()  # 确保数据库连接关闭
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(400)
def page_not_found(e):
    return render_template('errors/400.html'), 400


if __name__ == '__main__':
    app.run(debug=True)
