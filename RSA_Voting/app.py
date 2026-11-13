from flask import Flask, request, render_template,flash,session,redirect,url_for
import sqlite3
import secrets
from Blockchain import blockchain
import rsa
from sqlite3 import IntegrityError
import json
from datetime import datetime
import time

bchain=blockchain()
app = Flask(__name__)
app.secret_key="a91fd9e4b60b40bfa7763d39d124b87b" # some fatures in flask needs the secret_key

DATABASE = 'RSAdb.db' 

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
                        voter_id TEXT UNIQUE NOT NULL,
                        has_voted INTEGER DEFAULT 0)''')
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

#verify the signed encrypted vote
def verify_vote(encrypted_vote,signature,v_public_key):
    try:
        rsa.verify(encrypted_vote,signature,v_public_key)
        return True
    except rsa.VerificationError:
        return False

def add_padding(s):
    return s + '=' * (-len(s) % 4)
import tracemalloc
def gen_memory_usage():
    tracemalloc.start()
    public_key,private_key=rsa.newkeys(2048)
    pub_key_pem=public_key.save_pkcs1().decode('utf-8')
    pri_key_pem=private_key.save_pkcs1().decode('utf-8')
    current,peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak/1024

def gen_time():

    start=time.time()
    public_key,private_key=rsa.newkeys(2048)
    pub_key_pem=public_key.save_pkcs1().decode('utf-8')
    pri_key_pem=private_key.save_pkcs1().decode('utf-8')

    end=time.time()
    key_gen=end-start
    return key_gen


@app.route("/")
def Welcome():
    return render_template('Welcome.html')

@app.route('/form', methods=['GET','POST'])
def form():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        role=request.form.get('role','voter') # by default role will be voter
        
        #generating keys
        public_key,private_key=rsa.newkeys(2048)
        pub_key_pem=public_key.save_pkcs1().decode('utf-8')
        pri_key_pem=private_key.save_pkcs1().decode('utf-8')

        #checkng all the input fields
        if not name or not email or not role:
            flash("PLease enter all the fields",'error')
            return redirect(url_for('form'))

        #db connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        #check if admin or not
        if role.lower()=='admin':
            voter_id=secrets.token_hex(4)
            try:
                cursor.execute('INSERT INTO admin(name,email,role,voter_id,public_key,private_key) VALUES(?,?,?,?,?,?)',(name,email,role,voter_id,pub_key_pem,pri_key_pem))
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
            voter_id=secrets.token_hex(4)
            cursor.execute(
                'INSERT INTO voters (name, email,role,voter_id,has_voted,public_key,private_key) VALUES (?,?,?,?,?,?,?)', (name, email,role,voter_id,0,pub_key_pem,pri_key_pem))
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
    return render_template('admin_dashboard.html')

@app.route('/voting_ballot',methods=['GET', 'POST'])
def voting_ballot():
    user_id = session.get('user_id') 
    if request.method=='POST':
        selected_c_id=request.form.get('candidate')

        if selected_c_id :
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT public_key FROM admin WHERE id=1')
            admin_rec=cursor.fetchone()        
            if admin_rec is None:
                flash('Admin does not exist')
                return render_template('form.html')
            #admin public key
            a_pub_key=rsa.PublicKey.load_pkcs1(admin_rec[0].encode('utf-8'))
            
            cursor.execute('SELECT private_key,public_key FROM voters WHERE id=?',(user_id,))
            voter_rec=cursor.fetchone()
            if voter_rec is None:
                flash('user does not exist')
                return render_template('form.html')
            #voter's public and private key
            pub_key=rsa.PublicKey.load_pkcs1(voter_rec[1].encode())
            pri_key=rsa.PrivateKey.load_pkcs1(voter_rec[0].encode())

            #encrypt the vote using admin public key
            vote_data=selected_c_id.encode()
            encryptes_vote=rsa.encrypt(vote_data,a_pub_key)
            #sign the encrypted vote usning voter's private key
            signature=rsa.sign(vote_data,pri_key,'SHA-256')

            #verify the vote using voter's public key
            if verify_vote(vote_data,signature,pub_key):
                cursor.execute('UPDATE Candidates SET vote_count=vote_count+1 WHERE id=?',(selected_c_id,))
                cursor.execute('UPDATE voters SET has_voted=1 WHERE id=?',(user_id,))
                conn.commit()
                conn.close()
                #store encrypted vote and signature in blockchain
                bchain.add_block(voter_id=user_id,encrypt_vote=encryptes_vote.hex(),signature=signature.hex())

                flash('Your vote has been recorded','success')
                return render_template('vote_success.html')
        else:
            flash('Please select a candidate','error')
        
    #Show ballot
    conn=get_db_connection()
    cursor=conn.cursor()
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

@app.route('/decrypt_vote/<int:index>',methods=['GET','POST'])
def decrypt_vote(index):
    flash(f"Accessing decrypt_vote route with block_index: {index}")
    if request.method=='GET':
        voter_id=session.get('voter_id')
        if voter_id and session.get('admin'):
            try:
                #open json file and load the block content
                with open('blockchain.json','r') as f:
                    blockchain=json.load(f)
            except Exception as e:
                flash('Blockchain could not be loaded',e)
                return redirect(url_for('block_data'))
            #check if the block exist
            if index < 0 or index >= len(blockchain):
                flash('Block is invalid')
                return redirect(url_for('block_data'))
            #get the encrypted vote from the block
            encrypted_vote=blockchain[index].get('encrypt_vote')
            print("Raw Encrypted Vote:", repr(encrypted_vote))
            print("EV",encrypted_vote)
            if not encrypted_vote:
                flash('Encrypted vote not found')
                return redirect(url_for('block_data'))
            #convert back to bytes
            encrypted_vote=blockchain[index].get('encrypt_vote')
            encry_s=encrypted_vote.strip()
            encrypted_vote_b=bytes.fromhex(encry_s)
            #Load admin's private key
            conn=get_db_connection()
            cursor=conn.cursor()
            cursor.execute('SELECT private_key FROM admin WHERE id=1')
            rec=cursor.fetchone()
            conn.close()

            if not rec:
                flash('Admin does not exist')
                return redirect(url_for('block_data'))
            
            pri_key_pem = rec[0]
            private_key = rsa.PrivateKey.load_pkcs1(pri_key_pem.encode('utf-8'))
            #decrypt the vote
            try:
                decrypt_vote=rsa.decrypt(encrypted_vote_b,private_key).decode('utf-8')
            except Exception as e:
                flash('Decryption failed: ' + str(e))
                return redirect(url_for('block_data'))
            return render_template('decrypt_vote.html',vote=decrypt_vote)
        flash('access denied only admins')
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
    rsa_keygen_time = gen_time()  # Only ECC keygen time with serialization
    rsa_gen_mem=gen_memory_usage()
    return render_template(
        'benchmark.html',
        rsa_keygen=rsa_keygen_time,
        rsa_gen_mem=rsa_gen_mem
    )
if __name__ == '__main__':
    app.run(debug=True)