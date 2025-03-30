from Hashes import HashManager
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Index

Base = declarative_base()

class Block(Base):
    """Represents a block in the blockchain."""
    __tablename__ = 'blocks'

    id = Column(Integer, primary_key=True)
    hash = Column(String(64), unique=True, nullable=False)
    previous_hash = Column(String(64), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    nonce = Column(Integer, default=0)
    validator = Column(String(42))
    signature = Column(String(132))

    # Relationships
    coin_transactions = relationship("CoinTransaction", backref="block")
    nfts = relationship("NFT", backref="block")
    contracts = relationship("Contract", backref="block")
    
    Index('ix_blocks_hash', Block.hash)

class CoinTransaction(Base):
    """Fungible token (coin) transfers."""
    __tablename__ = 'coin_transactions'

    id = Column(Integer, primary_key=True)
    tx_hash = Column(String(66), unique=True, nullable=False)
    sender = Column(String(42), nullable=False)
    receiver = Column(String(42), nullable=False)
    amount = Column(Float, nullable=False)
    fee = Column(Float, default=0.0)
    signature = Column(String(132), nullable=False)
    block_id = Column(Integer, ForeignKey('blocks.id'))

class CoinBalance(Base):
    """Tracks fungible token balances for addresses."""
    __tablename__ = 'coin_balances'

    address = Column(String(42), primary_key=True)
    balance = Column(Float, default=0.0)

class NFT(Base):
    """Non-fungible token (NFT) representation."""
    __tablename__ = 'nfts'

    id = Column(Integer, primary_key=True)
    token_id = Column(String(64), unique=True, nullable=False)
    creator = Column(String(42), nullable=False)
    owner = Column(String(42), nullable=False)
    asset_uri = Column(String(256), nullable=False)
    metadata = Column(JSON)
    block_id = Column(Integer, ForeignKey('blocks.id'))

    transfers = relationship("NFTTransfer", backref="nft")

class NFTTransfer(Base):
    """Tracks NFT ownership transfers."""
    __tablename__ = 'nft_transfers'

    id = Column(Integer, primary_key=True)
    from_address = Column(String(42))
    to_address = Column(String(42), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    nft_id = Column(Integer, ForeignKey('nfts.id'))
    block_id = Column(Integer, ForeignKey('blocks.id'))

class Contract(Base):
    """Smart contract deployment and state."""
    __tablename__ = 'contracts'

    id = Column(Integer, primary_key=True)
    contract_id = Column(String(64), unique=True, nullable=False)
    creator = Column(String(42), nullable=False)
    code = Column(JSON, nullable=False)
    status = Column(String(20), default='active')
    block_id = Column(Integer, ForeignKey('blocks.id'))

    events = relationship("ContractEvent", backref="contract")

class ContractEvent(Base):
    """Records contract-triggered actions."""
    __tablename__ = 'contract_events'

    id = Column(Integer, primary_key=True)
    trigger_tx_hash = Column(String(66))
    action_type = Column(String(20), nullable=False)
    action_data = Column(JSON, nullable=False)
    contract_id = Column(Integer, ForeignKey('contracts.id'))
    block_id = Column(Integer, ForeignKey('blocks.id'))

