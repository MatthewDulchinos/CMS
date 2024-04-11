#CMS demo:

from flask import Flask, jsonify, request, g
from langchain_openai import ChatOpenAI
import openpyxl
import sqlite3
import argparse
import os

app = Flask(__name__)
DATABASE = 'codes.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/code/<string:id>', methods=['GET'])
def get_code(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT code, description FROM codes WHERE code=?", (id,))
    row = cursor.fetchone()
    cursor.close()
    if row:
        code, description = row
        return jsonify({'code': code, 'description': description})
    else:
        return jsonify({'error': 'Code not found'}), 404

# API endpoint to search for a code based on a phrase
@app.route('/search', methods=['GET'])
def search_code():
    search_phrase = '%'+'%'.join(request.args.get('phrase').split())+'%'
    if not search_phrase:
        return jsonify({'error': 'Search phrase is required'}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT code, description FROM codes WHERE description LIKE ?", (search_phrase,))
    rows = cursor.fetchall()
    cursor.close()

    if rows:
        codes_list = [{'code': row[0], 'description': row[1]} for row in rows]
        return jsonify(codes_list)
    else:
        return jsonify({'error': 'No codes found for the search phrase'}), 404

@app.route('/info/<string:id>', methods=['GET'])
def ask_chat_gpt(id):
    llm = ChatOpenAI(openai_api_key=request.args.get('OPEN_API_KEY'))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT code, description FROM codes WHERE code=?", (id,))
    row = cursor.fetchone()
    cursor.close()
    if row:
        code, description = row
        try:
            answer = llm.invoke(f"What does code: {code} and description: {description} mean from the HCPCS terminology?")
            return str(answer)
        except Exception as e:
            return jsonify({'error': str(e)}), 401
    else:
        return jsonify({'error': 'Code not found'}), 404


def create_codes_table(cursor):
    cursor.execute('''CREATE TABLE IF NOT EXISTS codes
                    (code TEXT,
                     description TEXT,
                     PRIMARY KEY (code))''')

def create_database(filepath, cursor):
    create_codes_table(cursor)
    rows = extract_rows_from_excel('codes/code_list.xlsx')
    for row in rows:
        cursor.execute("INSERT INTO codes (code, description) VALUES (?, ?)", (row[0], row[1]))

def extract_rows_from_excel(file_path):
    # Load the Excel workbook
    wb = openpyxl.load_workbook(file_path)
    sheet = wb.active

    #rows need to be a dictionary because there are duplicate records
    rows = {}
    for row in sheet.iter_rows(values_only=True):
        #only columns where the row[1] is not empty are 
        if row[1] is not None:
            rows[str(row[0])] = row
    return list(rows.values())

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Database recreation flag')
    parser.add_argument('--recreateDb', action='store_true', help='Flag to recreate the database')
    parser.add_argument('--debug', action='store_true', help='Flag to start flask in debug mode')
    args = parser.parse_args()

    if args.recreateDb:
        print("Database requested to be recreated")
        if os.path.exists(DATABASE):
            os.remove(DATABASE)
            print("Old database deleted")
    if not os.path.exists(DATABASE):
        print("Creating new database")
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        create_database('codes/code_list.xlsx',cursor)
        conn.commit()
        conn.close()
        print("New database created")
    app.run(debug=args.debug)
