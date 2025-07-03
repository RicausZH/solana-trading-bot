import asyncio
import os
import base58
import base64
import json
from dotenv import load_dotenv

from solders import message
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction

from solana.rpc.types import TxOpts
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Processed

from jupiter_python_sdk.jupiter import Jupiter

from config import Config
from token_scanner import TokenScanner
from contract_analyzer import ContractAnalyzer
from monitor import PositionMonitor

load_dotenv()

class SolanaTradingBot:
    def __init__(self):
        self.config = Config()
        self.validate_config()
        
        # Initialize Solana client
        self.solana_client = AsyncClient(self.config.SOLANA_RPC_URL)
        
        # Initialize wallet
        self.private_key = Keypair.from_bytes(base58.b58decode(self.config.SOLANA_PRIVATE_KEY))
        
        # Initialize Jupiter
        self.jupiter = Jupiter(
            async_client=self.solana_client,
            keypair=self.private_key,
            quote_api_url="https://quote-api.jup.ag/v6/quote?",
            swap_api_url="https://quote-api.jup.ag/v6/swap"
        )
        
        # Initialize components
        self.token_scanner = TokenScanner(self.config)
        self.contract_analyzer = ContractAnalyzer(self.config)
        self.position_monitor = PositionMonitor(self.config, self.jupiter)
        
        # Trading state
        self.active_positions = {}
        self.available_capital = float(self.config.TRADE_AMOUNT) * float(self.config.MAX_POSITIONS)
        
        print(f"🚀 Solana Trading Bot initialized")
        print(f"💰 Wallet: {self.private_key.pubkey()}")
        print(f"💵 Available capital: ${self.available_capital}")

    def validate_config(self):
        """Validate all required configuration is present"""
        required_vars = [
            'SOLANA_PRIVATE_KEY', 'SOLANA_PUBLIC_KEY', 'SOLANA_RPC_URL',
            'TRADE_AMOUNT', 'PROFIT_TARGET', 'MAX_POSITIONS'
        ]
        
        for var in required_vars:
            if not hasattr(self.config, var) or not getattr(self.config, var):
                raise ValueError(f"Missing required environment variable: {var}")

    async def execute_trade(self, token_address: str, amount_usdc: float):
        """Execute a real Jupiter swap"""
        try:
            print(f"🔄 Executing trade: ${amount_usdc} USDC → {token_address}")
            
            # Convert amount to lamports (USDC has 6 decimals)
            amount_lamports = int(amount_usdc * 1_000_000)
            
            # Execute swap via Jupiter
            transaction_data = await self.jupiter.swap(
                input_mint=self.config.USDC_MINT,  # USDC
                output_mint=token_address,
                amount=amount_lamports,
                slippage_bps=int(self.config.SLIPPAGE_BPS)
            )
            
            # Sign and send transaction
            raw_transaction = VersionedTransaction.from_bytes(base64.b64decode(transaction_data))
            signature = self.private_key.sign_message(message.to_bytes_versioned(raw_transaction.message))
            signed_txn = VersionedTransaction.populate(raw_transaction.message, [signature])
            
            opts = TxOpts(skip_preflight=False, preflight_commitment=Processed)
            result = await self.solana_client.send_raw_transaction(txn=bytes(signed_txn), opts=opts)
            transaction_id = json.loads(result.to_json())['result']
            
            print(f"✅ Trade executed: https://explorer.solana.com/tx/{transaction_id}")
            
            return {
                'success': True,
                'transaction_id': transaction_id,
                'token_address': token_address,
                'amount_usdc': amount_usdc
            }
            
        except Exception as e:
            print(f"❌ Trade execution failed: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def sell_position(self, token_address: str, token_amount: float):
        """Sell a position back to USDC"""
        try:
            print(f"💸 Selling position: {token_amount} {token_address} → USDC")
            
            # Get token decimals and convert amount
            # Most tokens use 9 decimals, but should be fetched dynamically
            amount_lamports = int(token_amount * 1_000_000_000)
            
            # Execute sell via Jupiter
            transaction_data = await self.jupiter.swap(
                input_mint=token_address,
                output_mint=self.config.USDC_MINT,  # USDC
                amount=amount_lamports,
                slippage_bps=int(self.config.SLIPPAGE_BPS)
            )
            
            # Sign and send transaction
            raw_transaction = VersionedTransaction.from_bytes(base64.b64decode(transaction_data))
            signature = self.private_key.sign_message(message.to_bytes_versioned(raw_transaction.message))
            signed_txn = VersionedTransaction.populate(raw_transaction.message, [signature])
            
            opts = TxOpts(skip_preflight=False, preflight_commitment=Processed)
            result = await self.solana_client.send_raw_transaction(txn=bytes(signed_txn), opts=opts)
            transaction_id = json.loads(result.to_json())['result']
            
            print(f"✅ Position sold: https://explorer.solana.com/tx/{transaction_id}")
            
            return {
                'success': True,
                'transaction_id': transaction_id,
                'token_address': token_address
            }
            
        except Exception as e:
            print(f"❌ Sell execution failed: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def main_trading_loop(self):
        """Main trading loop - 24/7 operation"""
        print("🔄 Starting main trading loop...")
        
        while True:
            try:
                # 1. Scan for new tokens
                new_tokens = await self.token_scanner.discover_new_tokens()
                
                for token_data in new_tokens:
                    token_address = token_data['address']
                    
                    # 2. Analyze for fraud (15 seconds max)
                    is_safe = await self.contract_analyzer.analyze_token(token_address)
                    
                    if not is_safe:
                        print(f"⚠️  Token {token_address} failed fraud analysis - skipping")
                        continue
                    
                    # 3. Check if we have available capital
                    if len(self.active_positions) >= int(self.config.MAX_POSITIONS):
                        print(f"📊 Maximum positions reached ({self.config.MAX_POSITIONS})")
                        continue
                    
                    # 4. Execute trade
                    trade_result = await self.execute_trade(token_address, float(self.config.TRADE_AMOUNT))
                    
                    if trade_result['success']:
                        # Add to active positions
                        self.active_positions[token_address] = {
                            'entry_price': float(self.config.TRADE_AMOUNT),
                            'target_price': float(self.config.TRADE_AMOUNT) * (1 + float(self.config.PROFIT_TARGET) / 100),
                            'transaction_id': trade_result['transaction_id']
                        }
                        
                        print(f"📈 Position opened: {token_address} | Target: +{self.config.PROFIT_TARGET}%")
                
                # 5. Monitor existing positions
                await self.position_monitor.check_positions(self.active_positions, self.sell_position)
                
                # 6. Wait before next scan
                await asyncio.sleep(10)  # 10 second intervals
                
            except Exception as e:
                print(f"❌ Error in main loop: {str(e)}")
                await asyncio.sleep(30)  # Wait longer on errors

    async def start(self):
        """Start the trading bot"""
        try:
            await self.main_trading_loop()
        except KeyboardInterrupt:
            print("🛑 Bot stopped by user")
        except Exception as e:
            print(f"💥 Fatal error: {str(e)}")
        finally:
            await self.solana_client.close()

if __name__ == "__main__":
    bot = SolanaTradingBot()
    asyncio.run(bot.start())
