# Updated: 2025-07-04 - Fixed Jupiter v6 compatibility
import asyncio
import logging
import base64
import json
from typing import Dict, Optional, Tuple, List
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import TxOpts
from solana.rpc.commitment import Processed, Confirmed
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from solders import message
import aiohttp
from config import Config

logger = logging.getLogger(__name__)

class JupiterTrader:
    def __init__(self, config: Config):
        self.config = config
        self.solana_client = AsyncClient(config.SOLANA_RPC_URL)
        self.active_positions = {}
        
        # Create keypair if we have private key
        if config.SOLANA_PRIVATE_KEY:
            self.keypair = Keypair.from_base58_string(config.SOLANA_PRIVATE_KEY)
        else:
            self.keypair = None
            
        # Jupiter API endpoints
        self.jupiter_quote_url = config.JUPITER_QUOTE_API
        self.jupiter_swap_url = config.JUPITER_SWAP_API
        
    async def execute_trade(self, token_address: str, amount_usdc: float) -> Tuple[bool, Dict]:
        """
        Execute a buy trade using Jupiter
        Returns: (success, trade_info)
        """
        try:
            # Convert USDC amount to smallest units (6 decimals)
            amount_units = int(amount_usdc * 1_000_000)
            
            logger.info(f"Executing buy trade: ${amount_usdc} USDC -> {token_address}")
            
            # Step 1: Get Jupiter quote
            quote_result = await self._get_jupiter_quote(
                input_mint=self.config.USDC_MINT,
                output_mint=token_address,
                amount=amount_units
            )
            
            if not quote_result['success']:
                return False, {'error': 'Failed to get quote', 'details': quote_result}
            
            quote = quote_result['quote']
            expected_output = int(quote['outAmount'])
            
            # Step 2: Execute swap
            swap_result = await self._execute_jupiter_swap(quote)
            
            if swap_result['success']:
                trade_info = {
                    'type': 'buy',
                    'token_address': token_address,
                    'input_amount': amount_usdc,
                    'input_mint': self.config.USDC_MINT,
                    'output_amount': expected_output,
                    'output_mint': token_address,
                    'transaction_id': swap_result['transaction_id'],
                    'timestamp': asyncio.get_event_loop().time(),
                    'expected_profit_price': expected_output * (1 + self.config.PROFIT_TARGET / 100)
                }
                
                # Store position for monitoring
                self.active_positions[token_address] = trade_info
                
                logger.info(f"Buy trade successful: {swap_result['transaction_id']}")
                return True, trade_info
            else:
                return False, {'error': 'Swap execution failed', 'details': swap_result}
                
        except Exception as e:
            logger.error(f"Error executing trade for {token_address}: {e}")
            return False, {'error': str(e)}
    
    async def check_profit_targets(self) -> List[Dict]:
        """Check all active positions for profit targets"""
        profitable_positions = []
        
        for token_address, position in list(self.active_positions.items()):
            try:
                # Get current price quote
                quote_result = await self._get_jupiter_quote(
                    input_mint=position['output_mint'],
                    output_mint=position['input_mint'],
                    amount=position['output_amount']
                )
                
                if quote_result['success']:
                    current_value = int(quote_result['quote']['outAmount'])
                    target_value = position['expected_profit_price']
                    
                    if current_value >= target_value:
                        profitable_positions.append({
                            'position': position,
                            'current_value': current_value,
                            'target_value': target_value,
                            'profit_percentage': ((current_value - position['input_amount'] * 1_000_000) / (position['input_amount'] * 1_000_000)) * 100
                        })
                        
            except Exception as e:
                logger.error(f"Error checking profit for {token_address}: {e}")
        
        return profitable_positions
    
    async def execute_sell(self, position: Dict) -> Tuple[bool, Dict]:
        """Execute a sell trade for a profitable position"""
        try:
            token_address = position['output_mint']
            amount_tokens = position['output_amount']
            
            logger.info(f"Executing sell trade: {amount_tokens} {token_address} -> USDC")
            
            # Step 1: Get Jupiter quote for selling
            quote_result = await self._get_jupiter_quote(
                input_mint=token_address,
                output_mint=self.config.USDC_MINT,
                amount=amount_tokens
            )
            
            if not quote_result['success']:
                return False, {'error': 'Failed to get sell quote', 'details': quote_result}
            
            quote = quote_result['quote']
            expected_usdc = int(quote['outAmount'])
            
            # Step 2: Execute swap
            swap_result = await self._execute_jupiter_swap(quote)
            
            if swap_result['success']:
                # Calculate profit
                original_usdc = position['input_amount'] * 1_000_000
                profit_usdc = expected_usdc - original_usdc
                profit_percentage = (profit_usdc / original_usdc) * 100
                
                sell_info = {
                    'type': 'sell',
                    'token_address': token_address,
                    'input_amount': amount_tokens,
                    'output_amount': expected_usdc / 1_000_000,  # Convert back to USDC
                    'transaction_id': swap_result['transaction_id'],
                    'timestamp': asyncio.get_event_loop().time(),
                    'profit_usdc': profit_usdc / 1_000_000,
                    'profit_percentage': profit_percentage,
                    'original_position': position
                }
                
                # Remove from active positions
                if token_address in self.active_positions:
                    del self.active_positions[token_address]
                
                logger.info(f"Sell trade successful: {swap_result['transaction_id']} - Profit: ${profit_usdc/1_000_000:.2f} ({profit_percentage:.2f}%)")
                return True, sell_info
            else:
                return False, {'error': 'Sell swap execution failed', 'details': swap_result}
                
        except Exception as e:
            logger.error(f"Error executing sell: {e}")
            return False, {'error': str(e)}
    
    async def _get_jupiter_quote(self, input_mint: str, output_mint: str, amount: int) -> Dict:
        """Get quote from Jupiter API"""
        try:
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": amount,
                "slippageBps": self.config.SLIPPAGE_BPS,
                "onlyDirectRoutes": "false",
                "asLegacyTransaction": "false"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.jupiter_quote_url, params=params) as response:
                    if response.status == 200:
                        quote = await response.json()
                        return {'success': True, 'quote': quote}
                    else:
                        error_text = await response.text()
                        logger.error(f"Jupiter quote error: {response.status} - {error_text}")
                        return {'success': False, 'error': f'HTTP {response.status}'}
                        
        except Exception as e:
            logger.error(f"Error getting Jupiter quote: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _execute_jupiter_swap(self, quote: Dict) -> Dict:
        """Execute swap transaction using Jupiter (FIXED)"""
        try:
            if not self.keypair:
                return {'success': False, 'error': 'No keypair available'}
            
            # Get compute unit price
            compute_unit_price = await self._get_compute_unit_price()
            
            # Prepare swap data
            swap_data = {
                "quoteResponse": quote,
                "userPublicKey": str(self.keypair.pubkey()),
                "wrapAndUnwrapSol": True,
                "useSharedAccounts": True,
                "feeAccount": None,
                "computeUnitPriceMicroLamports": min(compute_unit_price, 50000),
                "asLegacyTransaction": False
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.jupiter_swap_url,
                    json=swap_data,
                    headers=headers,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        swap_response = await response.json()
                        transaction_data = swap_response.get("swapTransaction")
                        
                        if transaction_data:
                            # Send transaction
                            tx_result = await self._send_transaction(transaction_data)
                            if tx_result['success']:
                                return {'success': True, 'transaction_id': tx_result['transaction_id']}
                            else:
                                return {'success': False, 'error': tx_result['error']}
                        else:
                            return {'success': False, 'error': 'No transaction data received'}
                    else:
                        error_text = await response.text()
                        logger.error(f"Jupiter swap error: {response.status} - {error_text}")
                        return {'success': False, 'error': f'HTTP {response.status}'}
                        
        except Exception as e:
            logger.error(f"Error executing Jupiter swap: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _send_transaction(self, transaction_data: str) -> Dict:
        """Send transaction to Solana blockchain (FIXED)"""
        try:
            # Decode transaction
            transaction_bytes = base64.b64decode(transaction_data)
            
            # Use VersionedTransaction
            versioned_tx = VersionedTransaction.from_bytes(transaction_bytes)
            
            # Sign transaction
            signed_tx = versioned_tx.sign([self.keypair])
            
            # Send to blockchain
            opts = TxOpts(
                skip_preflight=False,
                preflight_commitment=Processed,
                max_retries=3
            )
            
            result = await self.solana_client.send_transaction(signed_tx, opts)
            
            if result.value:
                # Wait for confirmation
                confirmation = await self._confirm_transaction(str(result.value))
                if confirmation:
                    return {'success': True, 'transaction_id': str(result.value)}
                else:
                    return {'success': False, 'error': 'Transaction confirmation failed'}
            else:
                return {'success': False, 'error': 'No transaction signature returned'}
                
        except Exception as e:
            logger.error(f"Error sending transaction: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _confirm_transaction(self, transaction_id: str, timeout: int = 60) -> bool:
        """Confirm transaction on Solana"""
        try:
            start_time = asyncio.get_event_loop().time()
            
            while asyncio.get_event_loop().time() - start_time < timeout:
                try:
                    result = await self.solana_client.get_signature_statuses([transaction_id])
                    if result.value and result.value[0]:
                        status = result.value[0]
                        if status.confirmation_status in [Confirmed, 'finalized']:
                            if status.err:
                                logger.error(f"Transaction {transaction_id} failed: {status.err}")
                                return False
                            return True
                except:
                    pass
                
                await asyncio.sleep(2)
            
            logger.warning(f"Transaction {transaction_id} confirmation timeout")
            return False
            
        except Exception as e:
            logger.error(f"Error confirming transaction {transaction_id}: {e}")
            return False
    
    async def _get_compute_unit_price(self) -> int:
        """Get current compute unit price"""
        try:
            rpc_data = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getRecentPrioritizationFees",
                "params": [["11111111111111111111111111111111"]]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.config.SOLANA_RPC_URL, json=rpc_data) as response:
                    if response.status == 200:
                        data = await response.json()
                        fees = data.get("result", [])
                        
                        if fees:
                            sorted_fees = sorted([f["prioritizationFee"] for f in fees])
                            median_fee = sorted_fees[len(sorted_fees)//2]
                            return max(median_fee, 1)
                        
            return 1
            
        except Exception as e:
            logger.warning(f"Could not get compute unit price: {e}")
            return 1
    
    async def get_wallet_balance(self, mint_address: str = None) -> float:
        """Get wallet balance for a specific token or SOL"""
        try:
            if mint_address is None or mint_address == self.config.SOL_MINT:
                # Get SOL balance
                balance = await self.solana_client.get_balance(self.keypair.pubkey())
                return balance.value / 1_000_000_000  # Convert lamports to SOL
            else:
                # Get token balance
                from solana.rpc.types import TokenAccountOpts
                token_accounts = await self.solana_client.get_token_accounts_by_owner(
                    self.keypair.pubkey(),
                    TokenAccountOpts(mint=Pubkey.from_string(mint_address))
                )
                
                if token_accounts.value:
                    account = token_accounts.value[0]
                    balance_info = await self.solana_client.get_token_account_balance(account.pubkey)
                    return float(balance_info.value.ui_amount or 0)
                return 0.0
                
        except Exception as e:
            logger.error(f"Error getting wallet balance: {e}")
            return 0.0
