from flask import Flask, request, render_template,flash,session,redirect,url_for
import sqlite3
import secrets
from Blockchain import blockchain
import base64
from datetime import datetime
from sqlite3 import IntegrityError
from ecc_utils import *
from cryptography.hazmat.primitives.serialization import load_pem_private_key,load_pem_public_key
import json
import time
import os

bchain=blockchain()
app = Flask(__name__)
app.secret_key="a91fd9e4b60b40bfa7763d39d124b87b" # some fatures in flask needs the secret_key
DATABASE = 'ECCdb.db' 

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # This makes the rows behave like dictionaries
    return conn

def create_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS admin(
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT NOT NULL,
                        role TEXT NOT NULL CHECK (role IN ('admin', 'voter')),
                        voter_id TEXT UNIQUE NOT NULL,
                        public_key TEXT NOT NULL,
                        private_key TEXT NOT NULL)''')
    cursor.execute('''CREATE TRIGGER IF NOT EXISTS admin_limit
                        BEFORE INSERT ON admin
                        WHEN(SELECT COUNT(*) FROM admin)>=1
                        BEGIN
                            SELECT RAISE(ABORT,'ONLY ONE ADMIN ALLOWED');
                        END;''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS voters (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT NOT NULL,
                        role TEXT NOT NULL CHECK (role IN ('admin', 'voter')),
                        voter_id TEXT UNIQUE NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Candidates(
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        party TEXT NOT NULL,       
                        description TEXT,
                        image TEXT,
                        vote_count INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

create_table() 
    
@app.route("/")
def Welcome():
    return render_template('Welcome.html')

def gen_time():
    start=time.time()

    private_key=ec.generate_private_key(ec.SECP384R1())
    public_key=private_key.public_key()

    #serialise to text-based format to store in the database
    pri_pem=private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
    ).decode()

    pub_pem=public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()

    end=time.time()

    keygen_time=end-start
    return keygen_time
import tracemalloc
def gen_men_usage():
    tracemalloc.start()
    for _  in range(10):
        private_key=ec.generate_private_key(ec.SECP384R1())
        public_key=private_key.public_key()

        #serialise to text-based format to store in the database
        pri_pem=private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
        ).decode()

        pub_pem=public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        current,peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    return peak/1024

@app.route('/form', methods=['GET','POST'])
def form():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        role=request.form.get('role','voter') # by default role will be voter
        

        private_key=ec.generate_private_key(ec.SECP384R1())
        public_key=private_key.public_key()

        #serialise to text-based format to store in the database
        pri_pem=private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
        ).decode()

        pub_pem=public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()

        
        if not name or not email or not role:
            flash("PLease enter all the fields",'error')
            return redirect(url_for('form'))

        conn = get_db_connection()
        cursor = conn.cursor()
        #check if admin or not
        if role.lower()=='admin':
            voter_id=secrets.token_hex(4)
            try:
                cursor.execute('INSERT INTO admin(name,email,role,voter_id,public_key,private_key) VALUES(?,?,?,?,?,?)',(name,email,role,voter_id,pub_pem,pri_pem))
                conn.commit()
                flash('Data inserted successfully!')
                return render_template('reg_success.html', voter_id=voter_id)
            except IntegrityError as e:
                if 'ONLY ONE ADMIN ALLOWED' in str(e):
                    flash('Only one admin is allowed')
                else:
                    flash(f'Error: {str(e)}')
            finally:
                conn.close()
        else:
            #check if the user already exist
            cursor.execute('SELECT * FROM voters WHERE name=? AND email=?',(name,email))
            if cursor.fetchone():
                conn.close()
                return redirect(url_for('Welcome'))
            else:
                voter_id=secrets.token_hex(4)
                cursor.execute(
                    'INSERT INTO voters (name, email,role,voter_id,has_voted,public_key,private_key) VALUES (?,?,?,?,?,?,?)', (name, email,role,voter_id,0,pub_pem,pri_pem))
                conn.commit()  # Save the changes
                conn.close()
                flash('Data inserted successfully!')
                return render_template('reg_success.html', voter_id=voter_id)

    return render_template('form.html')



@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        voter_id=request.form.get('voter_id')

        conn=get_db_connection()
        cursor=conn.cursor()
        #check admin
        cursor.execute('SELECT * FROM admin WHERE voter_id=?',(voter_id,))
        admin=cursor.fetchone()
        if admin:
            session['user_id']=admin[0]
            session['username']=admin[1]
            session['voter_id']=admin[4]
            session['admin']=True
            flash('Welcome admin')
            conn.close()
            return redirect(url_for('admin_dashboard'))

        #check voter
        cursor.execute('SELECT * FROM voters WHERE voter_id=?',(voter_id,))
        voter=cursor.fetchone()
        if voter:
            session['user_id'] = voter[0]
            session['username'] = voter[1]
            session['role'] = voter[3]
            session['voter_id']=voter_id
            session['has_voted']=voter[5]
            conn.close()
            flash ('Login successful','success')

            if session['role'].lower()=='voter' and voter['has_voted'] == 1:
                flash('You have already voted.')
                return redirect(url_for('Welcome'))
            else:
                return redirect(url_for('voting_ballot'))
        return 'Please generate correct voter id'
        
    return render_template('login.html')


@app.route('/add_candidate', methods=['GET', 'POST'])
def add_candidate():
   
    if request.method == 'POST':
        name = request.form['name']
        party = request.form['party']
        description = request.form['description']
        image = request.form['image']  # Assume filename or URL

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO Candidates (name, party, description, image) VALUES (?, ?, ?, ?)',
            (name, party, description, image)
        )
        conn.commit()
        conn.close()

        flash('Candidate added successfully!', 'success')
        return redirect(url_for('add_candidate'))
    return render_template('add_candidate.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    # Render admin dashboard
    return render_template('admin_dashboard.html')



@app.route('/voting_ballot', methods=['GET', 'POST'])
def voting_ballot():
    
    user_id = session.get('user_id')
    if request.method == 'POST':
        selected_c_id = request.form.get('candidate')
        if not selected_c_id:
            flash('Please select a candidate', 'error')
            return render_template('voting_ballot.html')

        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT private_key, public_key, has_voted FROM voters WHERE id=?', (user_id,))
        voter = cursor.fetchone()
        if voter is None:
            flash('User not registered', 'error')
            conn.close()
            return render_template('voting_ballot.html')

        if voter['has_voted']:
            flash('You have already voted', 'error')
            conn.close()
            return render_template('voting_ballot.html')

        user_private_key = serialization.load_pem_private_key(
            voter['private_key'].encode(), password=None
        )
        user_public_key = serialization.load_pem_public_key(
            voter['public_key'].encode()
        )
        # Get admin public key (PEM)
        cursor.execute('SELECT public_key FROM admin WHERE id=1')
        admin_row = cursor.fetchone()
        if admin_row is None:
            flash('Admin public key not found', 'error')
            conn.close()
            return render_template('voting_ballot.html')

        admin_public_key = serialization.load_pem_public_key(
            admin_row['public_key'].encode()
        )
        conn.close()

        aes_key = derive_symmetric_key(user_private_key, admin_public_key)
        # Prepare vote data to encrypt
        vote_data = f"{user_id}:{selected_c_id}".encode()

        iv = os.urandom(12)
        encryptor = Cipher(algorithms.AES(aes_key), modes.GCM(iv)).encryptor()
        ciphertext = encryptor.update(vote_data) + encryptor.finalize()
        tag = encryptor.tag

        # Combine iv + tag + ciphertext
        encrypted_vote = iv + tag + ciphertext
        encrypted_vote_b64 = base64.b64encode(encrypted_vote).decode()

        # Sign the encrypted vote
        signature = sign_data(user_private_key, encrypted_vote)
        signature_b64 = base64.b64encode(signature).decode()

        if not verify_signature(user_public_key, signature, encrypted_vote):
            conn.close()
            flash('Signature verification failed. Vote not accepted.', 'error')
            return render_template('voting_ballot.html')

        # Store encrypted vote and update vote count & voter status
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('UPDATE candidates SET vote_count=vote_count+1 WHERE id=?', (selected_c_id,))
        cursor.execute('UPDATE voters SET has_voted=1 WHERE id=?', (user_id,))
        conn.commit()
        conn.close()
        # Add block with encrypted vote (no signature here for simplicity)
        bchain.add_block(voter_id=user_id, encrypted_vote=encrypted_vote_b64,signature=signature_b64)

        flash('Your vote has been recorded', 'success')
        return render_template('vote_success.html')

    # GET: show candidates
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM candidates')
    candidates = cursor.fetchall()
    conn.close()
    return render_template('voting_ballot.html', candidates=candidates)


@app.route('/vote_success')
def vote_success():
    return render_template('vote_success.html')

@app.route('/result')
def result():
    conn=get_db_connection()
    cursor=conn.cursor()
    cursor.execute('SELECT * FROM Candidates')
    result_data=cursor.fetchall()
    cursor.close()
    return render_template('result.html',r_data=result_data)

@app.route('/block_data')
def block_data():
    chain_data=bchain.generate_chain()
    return render_template('block_data.html',chain=chain_data)

import json
@app.route('/decrypt/<int:index>', methods=['GET'])
def decrypt(index):
    if not session.get('admin'):
        flash('Admin access required', 'error')
        return redirect(url_for('login'))

    try:
        with open('new_blockchain.json', 'r') as f:
            blockchain = json.load(f)
    except Exception as e:
        flash(f'Blockchain could not be loaded: {e}', 'error')
        return redirect(url_for('block_data'))

    if index < 0 or index >= len(blockchain):
        flash('Invalid block index', 'error')
        return redirect(url_for('block_data'))

    block = blockchain[index]
    encrypted_vote_b64 = block.get('encrypted_vote')
    voter_id = block.get('voter_id')

    if not encrypted_vote_b64 or not voter_id:
        flash('Encrypted vote or voter ID not found in block', 'error')
        return redirect(url_for('block_data'))

    # Get keys from DB
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('SELECT private_key FROM admin WHERE id=1')
    admin_row = cursor.fetchone()

    cursor.execute('SELECT public_key FROM voters WHERE id=?', (voter_id,))
    voter_row = cursor.fetchone()
    conn.close()

    if not admin_row or not voter_row:
        flash('Admin or voter key not found', 'error')
        return redirect(url_for('block_data'))

    try:
        # Load admin's private key (SECP384R1)
        admin_private_key = load_pem_private_key(admin_row['private_key'].encode(), password=None)
        # Load voter's public key
        voter_public_key = load_pem_public_key(voter_row['public_key'].encode())

        # Derive AES key
        aes_key = derive_symmetric_key(admin_private_key, voter_public_key)

        # Decode and split the encrypted vote
        encrypted_vote_bytes = base64.b64decode(encrypted_vote_b64)
        iv = encrypted_vote_bytes[:12]
        tag = encrypted_vote_bytes[12:28]
        ciphertext = encrypted_vote_bytes[28:]

        # Decrypt using AES-GCM
        decryptor = Cipher(algorithms.AES(aes_key), modes.GCM(iv, tag)).decryptor()
        decrypted_vote_bytes = decryptor.update(ciphertext) + decryptor.finalize()
        decrypted_vote = decrypted_vote_bytes.decode('utf-8')

        return render_template('decrypt.html', vote=decrypted_vote, block_index=index)

    except Exception as e:
        flash(f'Failed to decrypt vote: {repr(e)}', 'error')
        return redirect(url_for('block_data'))
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out','info')
    return render_template("Welcome.html")


@app.template_filter('datetimeformat')
def datetimeformat(value):
    return datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')

@app.route('/benchmark')
def show_benchmark():
    ecc_keygen_time = gen_time()  # Only ECC keygen time with serialization
    ecc_men_usage=gen_men_usage()
    # You can add RSA benchmark or others here too
    return render_template(
        'benchmark.html',
        ecc_keygen=ecc_keygen_time,
        ecc_men_usage=ecc_men_usage
    )
if __name__ == '__main__':
    app.run(debug=True)