import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Solana Configuration
    SOLANA_PRIVATE_KEY = os.getenv('SOLANA_PRIVATE_KEY')
    SOLANA_PUBLIC_KEY = os.getenv('SOLANA_PUBLIC_KEY')
    SOLANA_RPC_URL = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
    
    # QuickNode Configuration
    QUICKNODE_HTTP_URL = os.getenv('QUICKNODE_HTTP_URL')
    QUICKNODE_WSS_URL = os.getenv('QUICKNODE_WSS_URL')
    
    # Trading Configuration
    TRADE_AMOUNT = os.getenv('TRADE_AMOUNT', '35')
    PROFIT_TARGET = os.getenv('PROFIT_TARGET', '2.5')
    MAX_POSITIONS = os.getenv('MAX_POSITIONS', '4')
    SLIPPAGE_BPS = os.getenv('SLIPPAGE_BPS', '50')
    
    # Token Addresses
    USDC_MINT = os.getenv('USDC_MINT', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v')
    SOL_MINT = os.getenv('SOL_MINT', 'So11111111111111111111111111111111111111112')
    
    # Jupiter API URLs
    JUPITER_QUOTE_API = os.getenv('JUPITER_QUOTE_API', 'https://quote-api.jup.ag/v6/quote')
    JUPITER_SWAP_API = os.getenv('JUPITER_SWAP_API', 'https://quote-api.jup.ag/v6/swap')
    
    # Free Fraud Detection APIs
    QUILLCHECK_API = os.getenv('QUILLCHECK_API', 'https://api.quillai.network/')
    GOPLUS_API = os.getenv('GOPLUS_API', 'https://api.gopluslabs.io/')
