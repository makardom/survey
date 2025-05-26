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
import asyncio

from telegram import Bot, Update
from telegram.ext import CommandHandler, ApplicationBuilder, ContextTypes
from telegram.ext import CallbackContext

def html_for_court(answers):
    return {
        'id': -2,
        'title': 'Судебное банкротство',
        'description': 'Рекомендуется процедура судебного банкротства'
    }

TELEGRAM_TOKEN = '5781751889:AAE6x0ivPQoq85c6QjChPNU0IZlbpLHTsM4'
CHAT_ID = 435066431 

bot = Bot(token=TELEGRAM_TOKEN)

async def send_answers_via_telegram(answers):
    message = "Новые ответы:\n" + "\n".join([f"Вопрос {k}: {v}" for k, v in answers.items()])
    await bot.send_message(chat_id=CHAT_ID, text=message)

async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to my awesome bot!")

async def get_user_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    app.logger.info("Получена команда /user_count")
    await update.message.reply_text(f"Количество пользователей в системе: 1000")
    # cursor = mysql.connection.cursor()
    # cursor.execute('SELECT COUNT(*) FROM form')
    # user_count = cursor.fetchone()[0]
    # cursor.close()
    # print(user_count)
    # await update.message.reply_text(f"Количество пользователей в системе: {user_count}")

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
        try:
            cursor = mysql.connection.cursor()
            user_id = session.get('id')  
            if user_id == None:
                user_id = 0
                cursor.execute('DELETE FROM result WHERE uid = 0')
            cursor.execute('INSERT INTO sessions (uid, session) \
                        SELECT %s, %s \
                        WHERE NOT EXISTS (SELECT * FROM sessions WHERE uid = %s);', (user_id, 0, user_id, ))
            cursor.execute('UPDATE sessions SET session = session + 1 \
                       WHERE uid = %s', (user_id,))
            mysql.connection.commit()
        
        except Exception as e:
            mysql.connection.rollback()
            app.logger.error(f"Error: {e}")
        finally:
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
        try:
            cursor = mysql.connection.cursor()
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

        except Exception as e:
            mysql.connection.rollback()
            app.logger.error(f"Error: {e}")
        finally:
            cursor.close()
        saved = get_saved_answers_from_database_form(session_num[0])
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
        cursor.execute('SELECT session FROM sessions where uid = %s', (user_id, ))
        session_number = cursor.fetchone()
        cursor.execute('INSERT INTO result (session, uid, qid, answer) VALUES (%s, %s, %s, %s)', (session_number, user_id, q_id, answer, ))
        mysql.connection.commit()
    except Exception as e:
        mysql.connection.rollback()
        app.logger.error(f"Failed to save answers to database: {e}")
    finally:
        cursor.close()


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

        # Отправка ответов в Telegram
        answers_dict = {question: text for question, text in saved_answers}
        asyncio.run(send_answers_via_telegram(answers_dict))

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
        try:
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
        except Exception as e:
            mysql.connection.rollback()
            app.logger.error(f"Error: {e}")
        finally:
            cursor.close()
    elif request.method == 'POST':
        msg = 'Поля должны быть заполнены!'
    return render_template('sign_up.html', msg=msg)


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('loggedin', None)
    session.pop('isAdmin', None)
    session.pop('id', None)
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
    pairs = input_string[0].split('; ')
    result = []
    for pair in pairs:
        if ', ' in pair:  
            question, answer = pair.split(', ', 1)  
            result.append((question.strip(), answer.strip()))  
        else:
            result.append((pair.strip(), ''))  
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
            answers = get_saved_answers_from_database(i)
            print(answers)
            if answers != [] and answers[0] != () and answers[1] != ():
                saved.append(parse_answers(answers[0][0]))
                # saved.append(answers[0])
                res_array.append(answers[1][0][0])
                date_array.append(answers[2][0][0])
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
        cursor.execute('SELECT group_concat(concat(questions.question, \", \", text) separator \"; \") \
                       FROM questions JOIN result ON questions.qid = result.qid \
                       JOIN answers ON result.answer = answers.aid \
                       WHERE result.uid = %s AND result.session = %s  group by result.uid', (user_id, session_num, ))
        saved_answers = cursor.fetchall()
        cursor.execute('SELECT DISTINCT questions.question \
                       FROM questions JOIN result ON questions.qid = result.qid \
                       WHERE result.uid = %s AND result.qid < 0 AND result.session = %s', (user_id, session_num, ))
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

# @app.route('/admin')
# def admin():
#     if 'isAdmin' in session and session['isAdmin'] == 1:
#         session['prev_page'] = 'admin'
#         page = request.args.get('page', 1, type=int)
#         per_page = 10
        
#         pagination = Form.query.paginate(
#             page=page,
#             per_page=per_page,
#             error_out=False
#         )
        
#         items = pagination.items

#         return render_template('admin.html',
#                              items=items,
#                              pagination=pagination)
#     else:
#         flash("У вас нет доступа к этой странице.")  # Сообщение об ошибке
#         prev_page = session.get('prev_page', None)
#         if prev_page and prev_page != 'admin':
#             return redirect(url_for(prev_page))
#         return redirect(url_for('home'))

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
        average_rating = None
        suitable_stats = None
        not_suitable_stats = None

        try:
            cursor = mysql.connection.cursor()
            cursor.execute("SHOW TABLES LIKE 'feedback'")
            if cursor.fetchone():
                # Расчет средней оценки по вопросу 1
                query = """
                    SELECT 
                        (SUM(anon_ratings.anon_sum) + SUM(user_ratings.user_sum)) / 
                        (COUNT(anon_ratings.anon_sum) + COUNT(user_ratings.user_sum)) AS average_rating
                    FROM 
                        (SELECT question_1 AS anon_sum FROM feedback WHERE uid = '0') AS anon_ratings,
                        (SELECT MAX(f1.question_1) AS user_sum 
                         FROM feedback f1 
                         WHERE f1.uid != '0' 
                         AND f1.date = (SELECT MAX(f2.date) FROM feedback f2 WHERE f2.uid = f1.uid)
                         GROUP BY f1.uid) AS user_ratings
                """
                cursor.execute(query)
                result = cursor.fetchone()
                average_rating = result['average_rating'] if result else None

                # Расчет статистики для пользователей, которым подходит банкротство
                query_suitable = """
                    SELECT 
                        SUM(CASE WHEN q2 = 'Да' THEN 1 ELSE 0 END) AS q2_yes,
                        SUM(CASE WHEN q2 = 'Да' THEN 0 ELSE 1 END) AS q2_no,
                        SUM(CASE WHEN q3 = 1 THEN 1 ELSE 0 END) AS q3_yes,
                        SUM(CASE WHEN q3 = 1 THEN 0 ELSE 1 END) AS q3_no,
                        COUNT(*) AS total
                    FROM (
                        SELECT 
                            f1.question_2 AS q2, 
                            f1.question_3 AS q3
                        FROM feedback f1
                        WHERE f1.question_2 = 'Да'
                        AND (f1.uid = '0' OR f1.date = (
                            SELECT MAX(f2.date) 
                            FROM feedback f2 
                            WHERE f2.uid = f1.uid
                        ))
                    ) AS filtered_data
                """
                cursor.execute(query_suitable)
                suitable_result = cursor.fetchone()
                
                if suitable_result and suitable_result['total'] > 0:
                    suitable_stats = {
                        'q2_yes': (suitable_result['q2_yes'] / suitable_result['total']) * 100,
                        'q2_no': (suitable_result['q2_no'] / suitable_result['total']) * 100,
                        'q3_yes': (suitable_result['q3_yes'] / suitable_result['total']) * 100,
                        'q3_no': (suitable_result['q3_no'] / suitable_result['total']) * 100
                    }

                # Расчет статистики для пользователей, которым НЕ подходит банкротство
                query_not_suitable = """
                    SELECT 
                        SUM(CASE WHEN q3 = 1 THEN 1 ELSE 0 END) AS q3_yes,
                        SUM(CASE WHEN q3 = 1 THEN 0 ELSE 1 END) AS q3_no,
                        COUNT(*) AS total
                    FROM (
                        SELECT 
                            f1.question_3 AS q3
                        FROM feedback f1
                        WHERE f1.question_2 = 'Банкротство не подходит'
                        AND (f1.uid = '0' OR f1.date = (
                            SELECT MAX(f2.date) 
                            FROM feedback f2 
                            WHERE f2.uid = f1.uid
                        ))
                    ) AS filtered_data
                """
                cursor.execute(query_not_suitable)
                not_suitable_result = cursor.fetchone()
                
                if not_suitable_result and not_suitable_result['total'] > 0:
                    not_suitable_stats = {
                        'q3_yes': (not_suitable_result['q3_yes'] / not_suitable_result['total']) * 100,
                        'q3_no': (not_suitable_result['q3_no'] / not_suitable_result['total']) * 100
                    }

        except Exception as e:
            print(f"Ошибка при получении данных feedback: {e}")
            average_rating = None
            suitable_stats = None
            not_suitable_stats = None

        return render_template('admin.html',
                            items=items,
                            pagination=pagination,
                            average_rating=average_rating,
                            suitable_stats=suitable_stats,
                            not_suitable_stats=not_suitable_stats)
    else:
        flash("У вас нет доступа к этой странице.")
        prev_page = session.get('prev_page', None)
        if prev_page and prev_page != 'admin':
            return redirect(url_for(prev_page))
        return redirect(url_for('home'))
    
@app.route('/survey')
def survey():
    session['prev_page'] = 'survey'
    return render_template('survey.html')

@app.route('/submit-survey', methods=['POST'])
def submit_survey():
    if not request.is_json:
        return jsonify({"error": "Invalid request format"}), 400
    
    data = request.get_json()
    uid = session.get('id', 0)  # 0 для неавторизованных пользователей
    current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        cursor = mysql.connection.cursor()
        
        if 'loggedin' in session:
            # Для авторизованных пользователей - обновляем существующую запись или создаем новую
            cursor.execute('''
                INSERT INTO feedback 
                (uid, question_1, question_2, question_3, date)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                question_1 = VALUES(question_1),
                question_2 = VALUES(question_2),
                question_3 = VALUES(question_3),
                date = VALUES(date) 
            ''', (uid, data['question1'], data['question2'], data['question3'], current_datetime))
        else:
            # Для неавторизованных - всегда создаем новую запись
            cursor.execute('''
                INSERT INTO feedback 
                (uid, question_1, question_2, question_3, date)
                VALUES (%s, %s, %s, %s, %s)
            ''', (uid, data['question1'], data['question2'], data['question3'], current_datetime))
        
        mysql.connection.commit()
        return jsonify({"message": "Survey submitted successfully"}), 200
        
    except Exception as e:
        mysql.connection.rollback()
        app.logger.error(f"Error saving survey results: {e}")
        return jsonify({"error": "Failed to save survey results"}), 500
    finally:
        cursor.close()

def run_flask():
    app.run(debug=True, port=80, host='0.0.0.0')

def run_telegram():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler('start', start_callback))
    application.add_handler(CommandHandler('user_count', get_user_count))
    application.run_polling()

if __name__ == "__main__":
    run_flask()
    run_telegram()