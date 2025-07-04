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
    
    # Security Analysis APIs (Alternatives to QuillAI)
    RUGCHECK_API = os.getenv('RUGCHECK_API', 'https://api.rugcheck.xyz/v1/tokens/sol')
    DEXSCREENER_API = os.getenv('DEXSCREENER_API', 'https://api.dexscreener.com/latest/dex/tokens')
    BIRDEYE_API = os.getenv('BIRDEYE_API', 'https://public-api.birdeye.so/defi/token_security')
    GOPLUS_API = os.getenv('GOPLUS_API', 'https://api.gopluslabs.io')
    
    # Optional API Keys (for higher limits)
    BIRDEYE_API_KEY = os.getenv('BIRDEYE_API_KEY', '')
    RUGCHECK_API_KEY = os.getenv('RUGCHECK_API_KEY', '')
    
    # Safety Thresholds
    SAFETY_THRESHOLD = float(os.getenv('SAFETY_THRESHOLD', '0.65'))
    MIN_LIQUIDITY_USD = float(os.getenv('MIN_LIQUIDITY_USD', '5000'))
    MIN_VOLUME_24H = float(os.getenv('MIN_VOLUME_24H', '1000'))
