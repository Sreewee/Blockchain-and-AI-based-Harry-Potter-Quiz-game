class Rules:
    def is_block_valid(self, new_block, previous_block):
    # Check hash linkage
    if previous_block.hash != new_block.previous_hash:
        return False
    # Validate PoS/PoW
    if not self.is_proof_valid(new_block):
        return False
    return True

    def is_chain_valid(self, chain):
        for i in range(1, len(chain)):
            if not self.is_block_valid(chain[i], chain[i-1]):
                return False
        return True


    def resolve_conflict(self, peers):
        max_length = len(self.chain)
        new_chain = None
        for peer in peers:
            peer_chain = peer.get_chain()  # Fetch via HTTP/P2P
            if len(peer_chain) > max_length and self.is_chain_valid(peer_chain):
                new_chain = peer_chain
        if new_chain:
            self.chain = new_chain  # Replace local chain