from Hashes import HashManager
class Block_entity:
    def __init__(self, index, timestamp, data, previous_hash):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.hash = HashManager().generate_hash(f"{index}{timestamp}{data}{previous_hash}")
    
    def __str__(self):
        return f"Index: {self.index}, Timestamp: {self.timestamp}, Data: {self.data}, Previous Hash: {self.previous_hash}, Hash: {self.hash}"

    def __repr__(self):
        return self.__str__()

    def __dict__(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "hash": self.hash
        }

    def __eq__(self, other):
        return self.index == other.index