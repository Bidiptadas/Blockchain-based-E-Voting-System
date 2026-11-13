import time
import hashlib
import json
import os

class Block:
    def __init__(self,index,timestamp,voter_id,encrypted_vote,signature,previous_hash):
        self.index=index
        self.timestamp=timestamp
        self.voter_id=voter_id
        self.encrypted_vote=encrypted_vote
        self.signature=signature
        self.previous_hash=previous_hash
        self.hash=self.calculate_hash()

    def calculate_hash(self):
        block_str=json.dumps ({
            'index':self.index,
            'timestamp': self.timestamp,
            'voter_id' : self.voter_id,
            'encrypted_vote': self.encrypted_vote,
            'signature' : self.signature,
            'previous_hash' : self.previous_hash
            }, sort_keys=True).encode()
        return hashlib.sha256(block_str).hexdigest()
    
    def to_dict(self):
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'voter_id': self.voter_id,
            'encrypted_vote': self.encrypted_vote,
            'signature': self.signature,
            'previous_hash': self.previous_hash,
            'hash': self.hash
        }

    def from_dict(block_dict):
        block = Block(
            block_dict['index'],
            block_dict['timestamp'],
            block_dict['voter_id'],
            block_dict['encrypted_vote'],
            block_dict['signature'],
            block_dict['previous_hash']
        )
        # hash is calculated in __init__, but to keep it consistent, overwrite it
        block.hash = block_dict['hash']
        return block
    
class blockchain:
    def __init__(self, filename='new_blockchain.json'):
        self.filename = filename
        self.chain = []
        self.load_chain()

    def genesis_block(self):
        gen_block = Block(0, time.time(), "0", "GENESIS", "GENESIS", "0")
        self.chain.append(gen_block)
        self.save_chain()

    def load_chain(self):
        if os.path.exists(self.filename):
            if os.stat(self.filename).st_size == 0:
                print("Empty blockchain.json — generating genesis block.")
                self.genesis_block()
            else:
                with open(self.filename, 'r') as f:
                    data = json.load(f)
                    self.chain = [Block.from_dict(block) for block in data]
        else:
            self.genesis_block()
            self.save_chain()

    def save_chain(self):
        with open(self.filename, 'w') as f:
            json.dump([block.to_dict() for block in self.chain], f, indent=4)

   
    def add_block(self, voter_id, encrypted_vote, signature):
        last_block = self.chain[-1]
        new_block = Block(
            index=len(self.chain),
            timestamp=time.time(),
            voter_id=voter_id,
            encrypted_vote=encrypted_vote,
            signature=signature,
            previous_hash=last_block.hash
        )
        self.chain.append(new_block)
        self.save_chain()

    def generate_chain(self):
        return [block.to_dict() for block in self.chain]