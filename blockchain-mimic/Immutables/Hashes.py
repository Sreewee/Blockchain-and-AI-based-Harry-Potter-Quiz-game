import hashlib

class HashManager:
    def __init__(self, algorithm='sha512'):
        self.algorithm = algorithm

    def generate_hash(self, data):
        hash_function = hashlib.new(self.algorithm)
        hash_function.update(data.encode('utf-8'))
        return hash_function.hexdigest()

    def verify_hash(self, data, hash_value):
        return self.generate_hash(data) == hash_value

