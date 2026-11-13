# Comparative Analysis of RSA and ECC in a Blockchain-Based E-Voting System

A small Flask web app that lets people register, cast an encrypted and signed vote, and have that vote stored in a hash-linked chain of blocks. I built it twice, once with **RSA-2048** and once with **ECC (SECP384R1)**, so I could compare how the two behave in the same voting workflow.

This started as my final-year B.Sc. Computer Science project at St. Edmund's College, Shillong (2025). I'm now treating it as a starting point for deeper research, including making it post-quantum secure (see [What's next](#whats-next)).

> **Heads up:** this is an educational prototype, not a production voting system. Please read the [Known limitations](#known-limitations) section before reusing any of it.

---

## Why I built this

Paper voting has real problems: ballots can be tampered with before counting, running elections is expensive, and people have to trust the people counting. Blockchain looks like a natural fit because records are append-only and easy to verify. But a blockchain is only as trustworthy as the cryptography underneath it.

So the question I wanted to answer was: **if you build the same e-voting flow with RSA and with ECC, what actually differs in practice?**

## What it does

**Voters can**
- Register and receive a unique login ID (generated with Python's `secrets.token_hex()`)
- Log in and pick a candidate on the ballot
- Vote only once

**The admin can**
- Add candidates
- View results
- Browse the blockchain data
- Decrypt individual votes with the admin private key

**Under the hood**
- Every vote is encrypted so only the admin can read it
- Every encrypted vote is signed by the voter and verified before it is stored
- Each block holds the previous block's SHA-256 hash, so changing an old block breaks the chain
- A benchmark page compares key generation time and memory use

## How the cryptography works

### ECC version
| Step | What's used |
|---|---|
| Curve | SECP384R1 |
| Key agreement | ECDH between the voter's private key and the admin's public key |
| Key derivation | HKDF (SHA-256) to turn the shared secret into an AES key |
| Vote encryption | AES-GCM |
| Signatures | ECDSA with SHA-256 |
| Decryption | Admin re-derives the same AES key from their private key and the voter's public key |

### RSA version
| Step | What's used |
|---|---|
| Key size | 2048-bit (`rsa.newkeys(2048)`) |
| Vote encryption | `rsa.encrypt()` with the admin's public key |
| Signatures | `rsa.sign()` with SHA-256, using the voter's private key |
| Decryption | `rsa.decrypt()` with the admin's private key |

### The blockchain
This is a **demonstration chain**, not a real distributed network. Blocks are Python dictionaries saved to a JSON file. Each block stores:

`index`, `timestamp`, `voter_id`, `encrypted vote`, `voter signature`, `previous hash`, `current hash`

## Results

Key generation benchmark from my runs:

| | Time | Memory |
|---|---|---|
| **ECC (SECP384R1)** | ~0.0009 s | ~0.03 KB |
| **RSA (2048-bit)** | ~5.6 s | ~24.64 KB |

ECC was dramatically cheaper to generate keys for. One caveat I want to be upfront about: these numbers cover key generation only, and RSA-2048 and P-384 are not at the same security level (P-384 is roughly comparable to RSA-7680). A fairer comparison, including encrypt, decrypt, sign and verify costs, is on my to-do list.

## Tech stack

- **Backend:** Python 3.12+, Flask
- **Database:** SQLite (three tables: voters, admin, candidates)
- **Crypto:** `cryptography` (ECC), `rsa` (RSA), `hashlib` (SHA-256)
- **Frontend:** HTML, CSS
- **Charts:** matplotlib

## Project structure

```
.
├── ecc-version/
│   ├── app.py
│   ├── blockchain.py
│   ├── ecc_utils.py
│   ├── templates/
│   └── static/
├── rsa-version/
│   ├── app.py
│   ├── blockchain.py
│   ├── templates/
│   └── static/
└── README.md
```

*(Adjust the folder names to match how you've organised the repo.)*

## Getting started

You'll need Python 3.12 or newer.

```bash
# 1. Clone the repo
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>

# 2. (Optional) create a virtual environment
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate

# 3. Install dependencies
pip install flask cryptography rsa matplotlib

# 4. Run whichever version you want to try
cd ecc-version        # or rsa-version
python app.py
```

Then open `http://127.0.0.1:5000` in your browser.

The admin table only allows one record, so register the admin account first, then register voters and start voting. The benchmark page is available at `/benchmark`.

## Known limitations

I'd rather list these myself than have you find them:

- **Private keys are stored in the database** unencrypted. That's fine for a demo and unacceptable for a real election.
- **A single admin key decrypts every vote.** There's no threshold or multi-party decryption.
- **Votes are linked to voter IDs** in the chain, so ballot secrecy is not fully preserved.
- **The Flask `secret_key` is hardcoded.** Move it to an environment variable before deploying anywhere.
- **The "blockchain" is a JSON file.** There's no consensus mechanism or peer-to-peer network.
- **No end-to-end verifiability.** Voters can't independently confirm their vote was counted.
- **Not quantum-safe.** Both RSA and ECC can be broken by Shor's algorithm on a large enough quantum computer. For votes stored permanently on a ledger, "harvest now, decrypt later" is a real concern.

## What's next

My plan for taking this further:

1. **Fuller benchmarks:** encrypt, decrypt, sign, verify and key/signature sizes, at matched security levels
2. **Post-quantum migration:** replace ECDH/RSA with **ML-KEM** (FIPS 203) and ECDSA/RSA signatures with **ML-DSA** (FIPS 204), using [liboqs](https://github.com/open-quantum-safe/liboqs-python)
3. **Hybrid mode:** classical + post-quantum together, so security holds if either one fails
4. **Threshold decryption** so no single admin can read every vote
5. **Ballot anonymity** and **homomorphic tallying** so votes can be counted without decrypting them individually
6. **A real permissioned blockchain** (e.g. Hyperledger Fabric) to measure how larger post-quantum signatures affect block size and throughput
7. Smaller things: biometric login, a live admin dashboard, better accessibility

If you're working on something similar, I'd love to hear about it.

## Acknowledgements

Thank you to my guide, Prof. Dr. Sangyal L. Tamang, and the Department of Computer Science at St. Edmund's College for their support and encouragement, and to my family for putting up with the late nights.

## Author

**Bidipta Das**

