#CMS demo:

from flask import Flask, jsonify, request, g
from langchain_openai import ChatOpenAI
from mlxtend.frequent_patterns import apriori, association_rules
import openpyxl
import sqlite3
import argparse
import os
import pandas as pd
import pickle

app = Flask(__name__)
DATABASE = 'codes.db'
ASSOCIATIONS = 'association_rules.pkl'

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
    cursor.execute("SELECT code, description FROM codes WHERE code LIKE ?", (f"%{id}%",))
    rows = cursor.fetchall()
    cursor.close()
    toReturn = []
    if rows:
        results = [{'code': row[0], 'description': row[1]} for row in rows]
        return jsonify(results)
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

def create_associations():
    df = pd.read_csv('codes/transactions.csv')
    df = df.set_index('Transaction_ID')

    frequent_itemsets = apriori(df, min_support=0.05, use_colnames=True)

    # Generate association rules and pickle them for future use.
    rules = association_rules(frequent_itemsets, metric='confidence', min_threshold=0.6)
    with open(ASSOCIATIONS, 'wb') as f:
        pickle.dump(rules, f)

# API endpoint to search for a code based on a phrase
@app.route('/relationship', methods=['GET'])
def relationships():
    codes = request.args.get('codes').split()
    input_set = set(codes)

    with open('association_rules.pkl', 'rb') as f:
        rules = pickle.load(f)
    recommendations = []
    try:
        for index, rule in rules.iterrows():
            # Get the antecedent and consequent of the rule
            antecedent = set(rule['antecedents'])
            consequent = set(rule['consequents'])
            
            # Check if the input items match the antecedent of the rule
            if antecedent.issubset(input_set):
                recommendations.append(consequent)

        # Combine all recommendations into a set to remove duplicates
        recommendations = set.union(*recommendations)
        # Remove input items from recommendations to avoid suggesting items the user already has
        recommendations.difference_update(input_set)

        return list(recommendations)
    except Exception as e:
        return jsonify('error: this feature is just a sample, and doesnt support all codes. Try "71100" or "86950 86930" as inputs'), 501 


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
    parser = argparse.ArgumentParser(description='server flags')
    parser.add_argument('--recreateDb', action='store_true', help='Flag to recreate the database')
    parser.add_argument('--recreateAssociation', action='store_true', help='Flag to recreate the associations')
    parser.add_argument('--debug', action='store_true', help='Flag to start flask in debug mode')
    args = parser.parse_args()

    if args.recreateAssociation:
        print("Association requested to be recreated")
        if os.path.exists(ASSOCIATIONS):
            os.remove(ASSOCIATIONS)
            print("Old association deleted")
    if not os.path.exists(ASSOCIATIONS):
        print("Creating new association")
        create_associations()
        print("New association created")
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
