from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mysqldb import MySQL
from functools import wraps
from flask import abort
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)

app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Zaq12wsx97!'
app.config['MYSQL_DB'] = 'USERS'
app.config['SECRET_KEY'] = 'bed'

mysql = MySQL(app)


def check_db_connection():
    try:
        with app.app_context():
            cur = mysql.connection.cursor()
            cur.execute('SELECT 1')
            cur.close()
            print('Connection to MySQL database successful!')
    except Exception as e:
        print(f'Error connecting to MySQL database: {e}')


login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)


class User(UserMixin):
    def __init__(self, id, email):
        self.id = id
        self.email = email


@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, email FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    if user:
        return User(id=user[0], email=user[1])
    return None


def has_role(email, role):
    return role in email

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if not has_role(current_user.email, role):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@app.route('/registr', methods=['GET', 'POST'])
@app.route("/", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            cur = mysql.connection.cursor()
            result = cur.execute("SELECT id, email FROM users WHERE email = %s AND password = %s", (email, password))

            if result > 0:
                user = cur.fetchone()
                login_user(User(id=user[0], email=user[1]))

                if 'service_manager' in user[1].lower():
                    flash('You are now logged in as a service manager', 'success')
                    return redirect(url_for('service_manager'))
                elif 'service_desc' in user[1].lower():
                    flash('You are now logged in as a service desc', 'success')
                    return redirect(url_for('Service_desc'))
                elif 'RrG_admin' in user[1]:
                    flash('You are now logged in as RG admin', 'success')
                    return redirect(url_for('rg_admin'))
                elif 'RG_manager' in user[1]:
                    flash('You are now logged in as RG manager', 'success')
                    return redirect(url_for('rg_manager'))
                elif 'Users' in user[1].lower():
                    flash('You are now logged in', 'success')
                    return redirect(url_for('Appeals'))
            else:
                flash('Invalid login', 'danger')
            cur.close()
        except Exception as e:
            print(f'Error during login: {e}')

    return render_template('registr.html')



@app.route("/index")
def index():
    if 'Service_manager' in current_user.email:
        return redirect(url_for('service_manager'))
    elif 'Service_desc' in current_user.email:
        return redirect(url_for('Service_desc'))
    elif 'RG_admin' in current_user.email:
        return redirect(url_for('rg_admin'))
    elif 'RG_manager' in current_user.email:
        return redirect(url_for('rg_manager'))
    elif 'Users' in current_user.email.lower():
        return redirect(url_for('index'))
    else:
        flash('Нет обращений для вашей роли', 'info')
        return redirect(url_for('index'))



@app.route("/Appeals", methods=['GET', 'POST'])
def submit_appeal():
    if request.method == 'POST':
        user_group = request.form['user_group']
        subject = request.form['subject']
        message = request.form['message']

        print(f'User Group: {user_group}')
        print(f'Subject: {subject}')
        print(f'Message: {message}')

        try:
            cur = mysql.connection.cursor()

            # Вставляем основное обращение
            cur.execute("INSERT INTO appeals (user_group, subject, message) VALUES (%s, %s, %s)",
                        (user_group, subject, message))
            mysql.connection.commit()
            print('Main appeal inserted successfully')

            # Уведомляем RG_manager, если пользовательская группа равна RG_manager
            if user_group == 'RG_Менеджеры процесса управления обращениями':
                cur.execute("INSERT INTO appeals (user_group, subject, message) VALUES (%s, %s, %s)",
                            ('RG_manager', subject, message))
                mysql.connection.commit()
                print('RG_manager notified')

            # Уведомляем RG_admin, если пользовательская группа отличается от RG_admin
            if user_group == 'RG_Администраторы':
                cur.execute("INSERT INTO appeals (user_group, subject, message) VALUES (%s, %s, %s)",
                            ('RG_admin', subject, message))
                mysql.connection.commit()
                print('RG_admin notified')

            if user_group == 'RG_Сервис-менеджеры':
                cur.execute("INSERT INTO appeals (user_group, subject, message) VALUES (%s, %s, %s)",
                            ('Service_manager', subject, message))
                mysql.connection.commit()
                print('Service_manager notified')

            if user_group == 'RG_Специалисты Сервис-Деск':
                cur.execute("INSERT INTO appeals (user_group, subject, message) VALUES (%s, %s, %s)",
                            ('Service_desc', subject, message))
                mysql.connection.commit()
                print('Service_desc notified')


            cur.close()
            flash('Appeal submitted successfully', 'success')
            return redirect(url_for('Appeals'))
        except Exception as e:
            print(f'Error during appeal submission: {e}')
            flash('Error submitting appeal', 'danger')
            return redirect(url_for('submit_appeal'))

    return render_template('Appeals.html')


@app.route("/RG_manager")
@role_required('RG_manager')
def rg_manager():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, subject, message FROM appeals WHERE user_group = %s", ('RG_manager',))
        appeals = cur.fetchall()
        cur.close()
        return render_template('RG_manager.html', appeals=appeals)
    except Exception as e:
        print(f'Error retrieving appeals: {e}')
        flash('Error retrieving appeals', 'danger')
        return redirect(url_for('index'))


@app.route("/delete_appeal/<int:appeal_id>", methods=['POST'])
def delete_appeal(appeal_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM appeals WHERE id = %s", (appeal_id,))
        mysql.connection.commit()
        cur.close()
        flash('Appeal deleted successfully', 'success')
    except Exception as e:
        print(f'Error deleting appeal: {e}')
        flash('Error deleting appeal', 'danger')
    referer = request.headers.get('Referer')
    return redirect(referer)


@app.route("/Service_manager")
@role_required('Service_manager')
def service_manager():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, subject, message FROM appeals WHERE user_group = %s", ('Service_manager',))
        appeals = cur.fetchall()
        cur.close()
        return render_template('Service_manager.html', appeals=appeals)
    except Exception as e:
        print(f'Error retrieving appeals: {e}')
        flash('Error retrieving appeals', 'danger')
        return redirect(url_for('index'))


@app.route("/Service_desc")
@role_required('Service_desc')
def Service_desc():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, subject, message FROM appeals WHERE user_group = %s", ('Service_desc',))
        appeals = cur.fetchall()
        cur.close()
        return render_template('Service_desc.html', appeals=appeals)
    except Exception as e:
        print(f'Error retrieving appeals: {e}')
        flash('Error retrieving appeals', 'danger')
        return redirect(url_for('index'))


@app.route("/RG_admin")
@role_required('RG_admin')
def rg_admin():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, subject, message FROM appeals WHERE user_group = %s", ('RG_admin',))
        appeals = cur.fetchall()
        cur.close()
        return render_template('RG_admin.html', appeals=appeals)
    except Exception as e:
        print(f'Error retrieving appeals: {e}')
        flash('Error retrieving appeals', 'danger')
        return redirect(url_for('index'))


@app.route("/about")
def about():
    return render_template('about.html')


if __name__ == '__main__':
    with app.app_context():
        check_db_connection()
    app.run(debug=True)
