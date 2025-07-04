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
    TRADE_AMOUNT = float(os.getenv('TRADE_AMOUNT', '35'))
    PROFIT_TARGET = float(os.getenv('PROFIT_TARGET', '2.5'))
    MAX_POSITIONS = int(os.getenv('MAX_POSITIONS', '4'))
    SLIPPAGE_BPS = int(os.getenv('SLIPPAGE_BPS', '50'))
    
    # Token Addresses
    USDC_MINT = os.getenv('USDC_MINT', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v')
    SOL_MINT = os.getenv('SOL_MINT', 'So11111111111111111111111111111111111111112')
    
    # Jupiter API URLs
    JUPITER_QUOTE_API = os.getenv('JUPITER_QUOTE_API', 'https://quote-api.jup.ag/v6/quote')
    JUPITER_SWAP_API = os.getenv('JUPITER_SWAP_API', 'https://quote-api.jup.ag/v6/swap')
    
    # Working Security APIs (Broken APIs Removed)
    DEXTOOLS_API_KEY = os.getenv('DEXTOOLS_API_KEY', '')
    DEXTOOLS_API_BASE = os.getenv('DEXTOOLS_API_BASE', 'https://public-api.dextools.io/standard/v2')
    DEXSCREENER_API = os.getenv('DEXSCREENER_API', 'https://api.dexscreener.com/latest/dex/tokens')
    
    # Safety Thresholds (Optimized)
    SAFETY_THRESHOLD = float(os.getenv('SAFETY_THRESHOLD', '0.60'))
    MIN_LIQUIDITY_USD = float(os.getenv('MIN_LIQUIDITY_USD', '1500'))
    MIN_VOLUME_24H = float(os.getenv('MIN_VOLUME_24H', '300'))
    
    # API Weights (Optimized for working APIs)
    DEXTOOLS_WEIGHT = 0.45      # Premium API gets highest weight
    DEXSCREENER_WEIGHT = 0.30   # Excellent market data
    RPC_WEIGHT = 0.20           # On-chain analysis
    PATTERN_WEIGHT = 0.05       # Basic validation
