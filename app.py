from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash, jsonify
from flask_mysqldb import MySQL
from flask_sqlalchemy import SQLAlchemy
from flask_sqlalchemy.pagination import Pagination
import MySQLdb.cursors
import re
import hashlib
import json
import logging
from datetime import datetime
import os


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './uploads/'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

app.secret_key = ' key'
app.logger.setLevel(logging.DEBUG)

app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'user'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'LOGIN'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://user:@localhost/LOGIN'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

mysql = MySQL(app)

with open('questions.json', 'r', encoding='utf8') as f:
    data = json.load(f)
questions = {q['id']: q for q in data['Questions']}

with open('results.json', 'r', encoding='utf8') as f:
    data = json.load(f)
results = {r['id']: r for r in data['Results']}

current_datetime = ''
@app.route('/form', methods=['GET', 'POST'])
def form():
    if 'history' not in session:
        session['history'] = []
    if 'answers' not in session:
        session['answers'] = {}
    session['prev_page'] = 'form'
    if request.method == 'POST':
        if request.form.get('next'):
            next_id = int(request.form.get('next'))
            answer = 'yes' if next_id - 100 == int(questions[int(session['history'][-1])]['next'].get('yes', 0)) else 'no'
            if 'end' in questions[int(session['history'][-1])]['next'] and next_id == int(questions[int(session['history'][-1])]['next']['end']):
                answer = 'end'
            if 'again' in questions[int(session['history'][-1])]['next'] and next_id == int(questions[int(session['history'][-1])]['next']['again']):
                answer = 'again'
            if next_id > 90:
                next_id -= 100
            session['answers'][str(session['history'][-1])] = answer
            save_answers_to_database(str(session['history'][-1]), answer)
            session['history'].append(str(next_id))
            session.modified = True

    else:
        question_id = int(request.args.get('question_id', 1))
        if str(question_id) not in session['history']:
            session['history'].append(str(question_id))
        session.modified = True

    question_id = int(session['history'][-1])
    question = questions[question_id]
    if question_id == 1:
        current_datetime = datetime.now().strftime('%d-%m-%Y %H:%M')
        print(current_datetime)
        cursor = mysql.connection.cursor()
        user_id = session.get('id')  
        if user_id == None:
            user_id = 0
            cursor.execute('DELETE FROM result WHERE uid = 0')
            mysql.connection.commit()
        cursor.execute('INSERT INTO sessions (uid, session) \
                        SELECT %s, %s \
                        WHERE NOT EXISTS (SELECT * FROM sessions WHERE uid = %s);', (user_id, 0, user_id, ))
        cursor.execute('UPDATE sessions SET session = session + 1 \
                       WHERE uid = %s', (user_id,))
        mysql.connection.commit()
        cursor.close()
    elif question_id < 0:
        print(session['history'])
        user_id = session.get('id') 
        if user_id == None:
            user_id = 0 
        if question_id == -2:
            res = html_for_court(session['answers'])
        else:
            res = results[int(session['history'][-2])]
        cursor = mysql.connection.cursor()
        #print(user_id)
        save_answers_to_database(question_id, 'NULL')
        cursor.execute('SELECT session FROM sessions WHERE uid = %s', (user_id,))
        session_num = cursor.fetchone()
        print(session_num)
        current_datetime = datetime.now().strftime('%d-%m-%Y %H:%M')
        cursor.execute('UPDATE result SET date = %s \
                       WHERE session = %s', (current_datetime, session_num[0],))
        cursor.execute('DELETE FROM result WHERE id NOT IN (\
                        SELECT MAX(id)\
                        FROM (select * from result) as res \
                        GROUP BY qid, session)')
        mysql.connection.commit()
        cursor.close()
        saved = get_saved_answers_from_database_form(session_num[0])
        #print(saved)
        if ('17' in session['answers'] and session['answers']['17'] == 'yes' or '18' in session['answers'] and session['answers']['18'] == 'no') and '3' in session['answers'] and session['answers']['3'] == 'yes':
            answer_17 = False
        else:
             answer_17 = True
        return render_template('form.html', question=question, res=res, saved=saved, answer_17=answer_17, answers=session['answers'])
    return render_template('form.html', question=question)

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

@app.route('/get-files')
def get_files():
    try:
        files = os.listdir(app.config['UPLOAD_FOLDER'])
    except FileNotFoundError:
        files = []
    return jsonify(files)

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
            if account['isAdmin'] == 1:
                session['isAdmin'] = True
            else:
                session['isAdmin'] = False
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
            registration_date = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('INSERT INTO form (username, password, isAdmin, registration_date) VALUES (%s, %s, %s, %s)',
                           (username, hashed_password, 0, registration_date))
            mysql.connection.commit()
            msg = 'Регистрация прошла успешно!'
            return redirect(url_for('sign_in'))
    elif request.method == 'POST':
        msg = 'Поля должны быть заполнены!'
    return render_template('sign_up.html', msg=msg)


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('loggedin', None)
    session.pop('isAdmin', None)
    return redirect(url_for('home'))

@app.route('/back', methods=['GET'])
def back():
    if len(session['history']) > 1:
        session['history'].pop()
        session.modified = True
    return redirect(url_for('form', question_id=session['history'][-1]))

@app.route('/judicial_bankruptcy')
def judicial_bankruptcy_info():
    session['prev_page'] = 'judicial_bankruptcy_info'
    return render_template('judicial_bankruptcy.html')  


@app.route('/out-of-court_bankruptcy')
def out_of_court_bankruptcy_info():
    session['prev_page'] = 'out_of_court_bankruptcy_info'
    return render_template('out-of-court_bankruptcy.html')


def parse_answers(input_string):
    # Разделим строку по разделителю '; '
    # Также позаботимся о лишних пробелах
    pairs = input_string.split('; ')
    
    # Создадим список кортежей из пар "вопрос, ответ"
    result = []
    for pair in pairs:
        # Разделим каждую пару по разделителю ', '
        if ', ' in pair:  # Проверим, есть ли разделитель
            question, answer = pair.split(', ', 1)  # Только первое разделение
            result.append((question.strip(), answer.strip()))  # Убираем лишние пробелы
        else:
            # Если разделитель не найден, можем добавить с пустым ответом
            result.append((pair.strip(), ''))  # или можете пропустить, в зависимости от вашей логики

    return result

@app.route('/profile', methods=['GET'])
def profile():
    session['prev_page'] = 'profile'
    saved = []
    cursor = mysql.connection.cursor()
    user_id = session.get('id')
    cursor.execute('SELECT session FROM sessions WHERE uid = %s', (user_id,))
    num_of_sessions = cursor.fetchall()
    print(num_of_sessions)
    cursor.close()
    date_array = []
    res_array = []
    if num_of_sessions != ():
        for i in range(1, num_of_sessions[0][0] + 1):
            if get_saved_answers_from_database(i)[0] != () and get_saved_answers_from_database(i)[1] != ():
                saved = parse_answers(get_saved_answers_from_database(i)[0])
                res_array.append(get_saved_answers_from_database(i)[1][0][0])
                date_array.append(get_saved_answers_from_database(i)[2][0][0])
        return render_template('profile.html', session_data=(zip(date_array, saved, res_array)))
    return render_template('profile.html', user_id=session.get('id'))

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part', 400
    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400
    if file:
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
        return redirect(url_for('admin'))

@app.route('/files')
def list_files():
    try:
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        app.logger.debug(f"Files in uploads: {files}")
    except FileNotFoundError:
        files = []
        app.logger.error("Uploads folder not found.")
    return render_template('files.html', files=files)

@app.route('/uploads/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

def get_saved_answers_from_database(session_num):
    try:
        user_id = session.get('id')
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT results \
                       FROM res_denorm \
                       WHERE uid = %s AND session = %s', (user_id, session_num, ))
        saved_answers = cursor.fetchall()
        cursor.execute('SELECT group_concat(concat(questions.question, ', ', text) separator "; ") \
                       FROM questions JOIN result ON questions.qid = result.qid \
                       JOIN answers ON result.answer = answers.aid\
                       WHERE result.uid = %s AND result.session = %s group by result.uid', (user_id, session_num, ))
        result = cursor.fetchall()
        cursor.execute('SELECT DISTINCT date FROM result WHERE uid = %s AND session = %s', (user_id, session_num, ))
        date = cursor.fetchall()
        cursor.close() 
        return [saved_answers,result,date]
    except Exception as e:
        app.logger.error(f"Failed to get saved answers from database: {e}")
        return []

db = SQLAlchemy(app)
class Form(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    isAdmin = db.Column(db.Boolean, nullable=False)

@app.route('/admin')
def admin():
    if 'isAdmin' in session and session['isAdmin'] == 1:
        session['prev_page'] = 'admin'
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        pagination = Form.query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        items = pagination.items

        return render_template('admin.html',
                             items=items,
                             pagination=pagination)
    else:
        flash("У вас нет доступа к этой странице.")  # Сообщение об ошибке
        prev_page = session.get('prev_page', None)
        if prev_page and prev_page != 'admin':
            return redirect(url_for(prev_page))
        return redirect(url_for('home'))

if __name__ == "__main__":
    #app.run(debug=True)
    app.run(debug=True, port=80, host='0.0.0.0')