from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature


# Load PEM-formatted keys
def load_private_key(pem):
    return serialization.load_pem_private_key(pem.encode(), password=None)

def load_public_key(pem):
    return serialization.load_pem_public_key(pem.encode())

# Derive AES key via ECDH
def derive_symmetric_key(private_key, peer_public_key):
    shared_key = private_key.exchange(ec.ECDH(), peer_public_key)
    derived_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b'handshake',
    ).derive(shared_key)
    return derived_key

# Encrypt using AES-GCM

def encrypt_vote(private_key, public_key):
    shared_key = private_key.exchange(ec.ECDH(), public_key)
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b'handshake data',
    ).derive(shared_key)

# Sign encrypted vote
def sign_data(private_key, message):
    return private_key.sign(message, ec.ECDSA(hashes.SHA256()))

# Verify signature
def verify_signature(public_key, signature,message):
    try:
        public_key.verify(signature, message, ec.ECDSA(hashes.SHA256()))
        return True
    except Exception:
        return False
