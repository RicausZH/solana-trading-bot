import os
import base58
from dotenv import load_dotenv
from solders.keypair import Keypair
from typing import Optional

load_dotenv()

class Config:
    def __init__(self):
        # Validate required environment variables
        self.validate_env_vars()
        
        # Solana Configuration
        self.SOLANA_PRIVATE_KEY = self._get_private_key()
        self.SOLANA_PUBLIC_KEY = self.SOLANA_PRIVATE_KEY.pubkey()
        self.SOLANA_RPC_URL = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
        
        # QuickNode Configuration
        self.QUICKNODE_HTTP_URL = os.getenv('QUICKNODE_HTTP_URL')
        self.QUICKNODE_WSS_URL = os.getenv('QUICKNODE_WSS_URL')
        
        # Jupiter Configuration
        self.JUPITER_API_URL = os.getenv('JUPITER_API_URL', 'https://quote-api.jup.ag/v6')
        
        # Trading Configuration
        self.TRADE_AMOUNT = float(os.getenv('TRADE_AMOUNT', '35.0'))
        self.PROFIT_TARGET = float(os.getenv('PROFIT_TARGET', '2.5'))
        self.MAX_POSITIONS = int(os.getenv('MAX_POSITIONS', '4'))
        self.SLIPPAGE_BPS = int(os.getenv('SLIPPAGE_BPS', '50'))
        
        # Fraud Detection APIs (Free)
        self.QUILLCHECK_API_URL = 'https://api.quillai.network'
        self.GOPLUS_API_URL = 'https://api.gopluslabs.io/api/v1'
        
        # Token Addresses
        self.USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        self.SOL_MINT = "So11111111111111111111111111111111111111112"
        
        # Raydium Program ID
        self.RAYDIUM_PROGRAM_ID = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
        
    def validate_env_vars(self):
        required_vars = [
            'SOLANA_PRIVATE_KEY',
            'QUICKNODE_HTTP_URL',
            'QUICKNODE_WSS_URL'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    def _get_private_key(self) -> Keypair:
        private_key_str = os.getenv('SOLANA_PRIVATE_KEY')
        try:
            # Try base58 decode first
            private_key_bytes = base58.b58decode(private_key_str)
            return Keypair.from_bytes(private_key_bytes)
        except:
            try:
                # Try JSON array format
                import json
                private_key_array = json.loads(private_key_str)
                return Keypair.from_bytes(private_key_array)
            except:
                raise ValueError("Invalid private key format. Use base58 string or JSON array.")
