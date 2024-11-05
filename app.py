from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
import hashlib
import json
import logging
from datetime import datetime


app = Flask(__name__)
app.secret_key = ' key'
app.logger.setLevel(logging.DEBUG)

app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'user'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'LOGIN'

mysql = MySQL(app)

def save_answers_to_database(q_id, answer):
    try:
        user_id = session.get('id')  
        print(user_id)
        cursor = mysql.connection.cursor()
        if user_id == None:
            user_id = 0
        cursor.execute('INSERT INTO sessions (uid, session) \
                        SELECT %s, %s \
                        WHERE NOT EXISTS (SELECT * FROM sessions WHERE uid = %s);', (user_id, 1, user_id, ))
        mysql.connection.commit()
        session_number = cursor.fetchone()
        cursor.close()
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT session FROM sessions where uid = %s', (user_id, ))
        session_number = cursor.fetchone()
        cursor.close()
        cursor = mysql.connection.cursor()
        cursor.execute('INSERT INTO result (session, uid, qid, answer) VALUES (%s, %s, %s, %s)', (session_number, user_id, q_id, answer, ))
        mysql.connection.commit()
        cursor.close()
    except Exception as e:
        app.logger.error(f"Failed to save answers to database: {e}")


def get_saved_answers_from_database_form(session_num):
    try:
        cursor = mysql.connection.cursor()
        user_id = session.get('id')
        if user_id == None:
            user_id = 0
        cursor.execute('SELECT DISTINCT questions.question, text \
                       FROM questions JOIN result ON questions.qid = result.qid \
                       JOIN answers ON result.answer = answers.aid\
                       WHERE result.uid = %s AND result.qid > 0 AND result.session = %s', (user_id, session_num, ))
        saved_answers = cursor.fetchall()
        #if user_id == 0:
           # cursor.execute('DELETE FROM result WHERE uid = 0')
           # mysql.connection.commit()
        cursor.close() 
        return saved_answers
    except Exception as e:
        app.logger.error(f"Failed to get saved answers from database: {e}")
        return []


@app.route('/')
def home():
    session['prev_page'] = 'home'
    if 'history' in session:
        session['history'] = []
    if 'answers' in session:
        session['answers'] = {}
    return render_template('home.html')  # Главная


@app.route('/need')
def need():
    session['prev_page'] = 'need'
    return render_template('need.html')  # Главная


@app.route('/sign-in', methods=['GET', 'POST'])
def sign_in():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        hashed_password = hashlib.sha256(request.form['password'].encode('utf-8')).hexdigest()
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM form WHERE username = %s AND password = %s', (username, hashed_password,))
        account = cursor.fetchone()
        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            return redirect(url_for(session['prev_page']))
        else:
            msg = 'Неверный логин/пароль!'
    return render_template('sign_in.html', msg=msg)


@app.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        hashed_password = hashlib.sha256(request.form['password'].encode('utf-8')).hexdigest()

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM form WHERE username = %s', (username,))
        account = cursor.fetchone()
        if account:
            msg = 'Такой аккаунт уже существует'
        elif not re.match(r'\w+[\w\.\_\-]+\w+\@\w+[\w\.]+\w+.\w{1,3}', username):
            msg = 'Введите корректный адрес электронной почты!'
        elif not username or not hashed_password:
            msg = 'Поля должны быть заполнены!'
        else:
            cursor.execute('INSERT INTO form (`username`, `password`) VALUES (%s, %s)',
                           (username, hashed_password,))
            mysql.connection.commit()
            msg = 'Регистрация прошла успешно!'
            return redirect(url_for('sign_in'))
    elif request.method == 'POST':
        msg = 'Поля должны быть заполнены!'
    return render_template('sign_up.html', msg=msg)


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('loggedin', None)
    return redirect(url_for(session['prev_page']))

if __name__ == "__main__":
    #app.run(debug=True)
    app.run(debug=True, port=80, host='0.0.0.0')