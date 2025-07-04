#!/usr/bin/env python3
"""
Solana Trading Bot - REAL TRADING VERSION (FIXED)
⚠️ WARNING: This version uses REAL MONEY on Solana mainnet
Uses direct Jupiter API calls + Real blockchain transactions
Includes: Real Token Discovery, Advanced Fraud Detection, REAL Trading, Profit Taking
Updated: 2025-07-04 - Fixed Jupiter v6 compatibility and transaction serialization
"""

import os
import asyncio
import aiohttp
import json
import base64
import logging
import time
import datetime
from typing import Dict, List, Optional, Tuple
from datetime import datetime as dt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging for Railway
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class SolanaTradingBot:
    def __init__(self):
        """Initialize the trading bot with configuration"""
        # Environment variables
        self.private_key = os.getenv("SOLANA_PRIVATE_KEY")
        self.public_key = os.getenv("SOLANA_PUBLIC_KEY") 
        self.rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
        self.quicknode_http = os.getenv("QUICKNODE_HTTP_URL")
        self.quicknode_wss = os.getenv("QUICKNODE_WSS_URL")
        
        # REAL TRADING CONTROL
        self.enable_real_trading = os.getenv("ENABLE_REAL_TRADING", "false").lower() == "true"
        
        # Trading configuration
        self.trade_amount = int(float(os.getenv("TRADE_AMOUNT", "35.0")) * 1_000_000)
        self.profit_target = float(os.getenv("PROFIT_TARGET", "2.5"))
        self.max_positions = int(os.getenv("MAX_POSITIONS", "4"))
        self.slippage = int(os.getenv("SLIPPAGE_BPS", "50"))
        
        # Token addresses
        self.usdc_mint = os.getenv("USDC_MINT", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
        self.sol_mint = os.getenv("SOL_MINT", "So11111111111111111111111111111111111111112")
        
        # Trading state
        self.active_positions = {}
        self.total_trades = 0
        self.profitable_trades = 0
        self.total_profit = 0.0
        
        # API endpoints
        self.jupiter_quote_url = "https://quote-api.jup.ag/v6/quote"
        self.jupiter_swap_url = "https://quote-api.jup.ag/v6/swap"
        
        # Security Analysis APIs (Free and Working)
        self.dexscreener_url = os.getenv("DEXSCREENER_API", "https://api.dexscreener.com/latest/dex/tokens")
        
        # Safety thresholds
        self.safety_threshold = float(os.getenv("SAFETY_THRESHOLD", "0.55"))
        self.min_liquidity_usd = float(os.getenv("MIN_LIQUIDITY_USD", "1500"))
        self.min_volume_24h = float(os.getenv("MIN_VOLUME_24H", "300"))
        
        logger.info("🤖 Solana Trading Bot initialized with Free APIs")
        logger.info(f"💰 Trade Amount: ${self.trade_amount/1_000_000}")
        logger.info(f"🎯 Profit Target: {self.profit_target}%")
        logger.info(f"📊 Max Positions: {self.max_positions}")
        logger.info(f"🔒 Safety Threshold: {self.safety_threshold}")
        logger.info(f"💧 Min Liquidity: ${self.min_liquidity_usd:,.0f}")
        logger.info(f"📈 Min Volume 24h: ${self.min_volume_24h:,.0f}")
        
        # CRITICAL WARNING
        if self.enable_real_trading:
            logger.warning("⚠️ REAL TRADING ENABLED - WILL USE REAL MONEY!")
            logger.warning("⚠️ Ensure wallet is funded with USDC and SOL")
        else:
            logger.info("💡 Simulation mode - No real money will be used")
    
    async def validate_configuration(self) -> bool:
        """Validate bot configuration"""
        if not self.private_key:
            logger.error("❌ SOLANA_PRIVATE_KEY not set")
            return False
        if not self.public_key:
            logger.error("❌ SOLANA_PUBLIC_KEY not set") 
            return False
            
        if self.enable_real_trading:
            logger.warning("⚠️ REAL TRADING MODE - Checking wallet balance...")
            balance_ok = await self.check_wallet_balance()
            if not balance_ok:
                logger.error("❌ Insufficient wallet balance for real trading")
                return False
            
        logger.info("✅ Configuration validated")
        return True
    
    async def check_wallet_balance(self) -> bool:
        """Check if wallet has sufficient balance for trading"""
        try:
            # Check USDC balance
            usdc_balance = await self.get_token_balance(self.usdc_mint)
            sol_balance = await self.get_sol_balance()
            
            required_usdc = (self.trade_amount * self.max_positions) / 1_000_000
            required_sol = 0.01  # Minimum SOL for fees
            
            logger.info(f"💰 Wallet Balance: {usdc_balance:.2f} USDC, {sol_balance:.4f} SOL")
            logger.info(f"💰 Required: {required_usdc:.2f} USDC, {required_sol:.4f} SOL")
            
            if usdc_balance < required_usdc:
                logger.error(f"❌ Need {required_usdc:.2f} USDC, have {usdc_balance:.2f}")
                return False
                
            if sol_balance < required_sol:
                logger.error(f"❌ Need {required_sol:.4f} SOL, have {sol_balance:.4f}")
                return False
                
            logger.info("✅ Wallet has sufficient balance for trading")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error checking wallet balance: {e}")
            return False
    
    async def get_token_balance(self, mint_address: str) -> float:
        """Get token balance from wallet"""
        try:
            # Use Solana RPC to check token balance
            from solana.rpc.async_api import AsyncClient
            from solders.pubkey import Pubkey
            from solana.rpc.types import TokenAccountOpts
            
            client = AsyncClient(self.rpc_url)
            
            if mint_address == self.usdc_mint:
                # Get USDC token accounts
                token_accounts = await client.get_token_accounts_by_owner(
                    Pubkey.from_string(self.public_key),
                    TokenAccountOpts(mint=Pubkey.from_string(mint_address))
                )
                
                if token_accounts.value:
                    account = token_accounts.value[0]
                    balance_info = await client.get_token_account_balance(account.pubkey)
                    return float(balance_info.value.ui_amount or 0)
                return 0.0
            else:
                return 150.0  # Simulated balance for other tokens
                
        except Exception as e:
            logger.error(f"Error getting token balance: {e}")
            return 0.0
    
    async def get_sol_balance(self) -> float:
        """Get SOL balance from wallet"""
        try:
            from solana.rpc.async_api import AsyncClient
            from solders.pubkey import Pubkey
            
            client = AsyncClient(self.rpc_url)
            balance = await client.get_balance(Pubkey.from_string(self.public_key))
            return balance.value / 1_000_000_000  # Convert lamports to SOL
            
        except Exception as e:
            logger.error(f"Error getting SOL balance: {e}")
            return 0.0
    
    async def get_compute_unit_price(self) -> int:
        """Get current compute unit price for transactions"""
        try:
            # Get recent compute unit prices from RPC
            async with aiohttp.ClientSession() as session:
                rpc_data = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getRecentPrioritizationFees",
                    "params": [["11111111111111111111111111111111"]]
                }
                
                async with session.post(self.rpc_url, json=rpc_data) as response:
                    if response.status == 200:
                        data = await response.json()
                        fees = data.get("result", [])
                        
                        if fees:
                            # Use median fee
                            sorted_fees = sorted([f["prioritizationFee"] for f in fees])
                            median_fee = sorted_fees[len(sorted_fees)//2]
                            return max(median_fee, 1)  # At least 1 micro-lamport
                        
            return 1  # Default fallback
            
        except Exception as e:
            logger.warning(f"Could not get compute unit price: {e}")
            return 1
    
    async def get_jupiter_quote(self, input_mint: str, output_mint: str, amount: int) -> Optional[Dict]:
        """Get quote from Jupiter API"""
        try:
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": amount,
                "slippageBps": self.slippage,
                "onlyDirectRoutes": "false",
                "asLegacyTransaction": "false"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.jupiter_quote_url, params=params) as response:
                    if response.status == 200:
                        quote = await response.json()
                        input_amount = int(quote["inAmount"]) / 1_000_000
                        output_amount = int(quote["outAmount"]) / 1_000_000
                        
                        logger.info(f"📊 Jupiter Quote: {input_amount:.2f} → {output_amount:.6f}")
                        return quote
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Jupiter quote failed: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error getting Jupiter quote: {e}")
            return None
    
    async def execute_jupiter_swap(self, quote: Dict) -> Optional[str]:
        """Execute swap via Jupiter API - REAL OR SIMULATION (FIXED)"""
        try:
            # Get current compute unit price
            compute_unit_price = await self.get_compute_unit_price()
            
            swap_data = {
                "quoteResponse": quote,
                "userPublicKey": self.public_key,
                "wrapAndUnwrapSol": True,
                "useSharedAccounts": True,  # Add this for v6
                "feeAccount": None,
                "computeUnitPriceMicroLamports": min(compute_unit_price, 50000),  # Cap at 50k
                "asLegacyTransaction": False  # Use versioned transactions
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
                            if self.enable_real_trading:
                                # REAL TRADING - USES ACTUAL MONEY
                                tx_id = await self.send_real_transaction(transaction_data)
                                if tx_id:
                                    logger.info(f"✅ REAL SWAP EXECUTED: {tx_id}")
                                    logger.info(f"🔗 View: https://explorer.solana.com/tx/{tx_id}")
                                    return tx_id
                                else:
                                    logger.error("❌ Failed to send real transaction")
                                    return None
                            else:
                                # SIMULATION MODE
                                tx_id = f"sim_{int(time.time())}"
                                logger.info(f"✅ SIMULATED swap: {tx_id}")
                                logger.info("💡 To enable real trading: Set ENABLE_REAL_TRADING=true")
                                return tx_id
                        else:
                            logger.error("❌ No transaction data in swap response")
                            return None
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Jupiter swap failed: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error executing Jupiter swap: {e}")
            return None
    
    async def execute_jupiter_swap_with_retry(self, quote: Dict, max_retries: int = 3) -> Optional[str]:
        """Execute swap with retry logic"""
        for attempt in range(max_retries):
            try:
                result = await self.execute_jupiter_swap(quote)
                if result:
                    return result
                
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Swap failed, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    
            except Exception as e:
                logger.error(f"Swap attempt {attempt + 1} failed: {e}")
                
        return None
    
    async def send_real_transaction(self, transaction_data: str) -> Optional[str]:
        """Send real transaction to Solana blockchain (FIXED)"""
        try:
            # REAL BLOCKCHAIN TRANSACTION
            logger.warning("⚠️ SENDING REAL TRANSACTION WITH REAL MONEY")
        
            # Updated transaction handling for Jupiter v6
            from solana.rpc.async_api import AsyncClient
            from solders.keypair import Keypair
            from solders.transaction import VersionedTransaction
            from solana.rpc.types import TxOpts
            from solana.rpc.commitment import Processed
            import base64
        
            # Decode transaction
            transaction_bytes = base64.b64decode(transaction_data)
            
            # Use VersionedTransaction instead of Transaction
            versioned_tx = VersionedTransaction.from_bytes(transaction_bytes)
            
            # Sign with keypair
            keypair = Keypair.from_base58_string(self.private_key)
            signed_tx = versioned_tx.sign([keypair])
            
            # Send to blockchain
            client = AsyncClient(self.rpc_url)
            
            # Use send_transaction with proper options
            opts = TxOpts(
                skip_preflight=False,
                preflight_commitment=Processed,
                max_retries=3
            )
            
            result = await client.send_transaction(signed_tx, opts)
            
            if result.value:
                logger.info(f"✅ REAL TRANSACTION SENT: {result.value}")
                return str(result.value)
            else:
                logger.error("❌ Transaction failed - no signature returned")
                return None
            
        except Exception as e:
            logger.error(f"❌ Error sending real transaction: {e}")
            return None
    
    async def check_token_safety(self, token_address: str) -> Tuple[bool, float]:
        """Check if token is safe using reliable free APIs"""
        try:
            # Skip SOL for now - focus on new tokens
            if token_address == self.sol_mint:
                logger.info(f"⏭️ Skipping SOL - looking for new tokens only")
                return False, 0.5
            
            logger.info(f"🔍 Analyzing token safety: {token_address}")
            
            # Import and use fraud detector
            try:
                from src.fraud_detector import FraudDetector
                from src.config import Config
                
                config = Config()
                async with FraudDetector(config) as detector:
                    is_safe, analysis_report = await detector.analyze_token_safety(token_address)
                    confidence = analysis_report.get('safety_score', 0.0)
                    
                    return is_safe, confidence
            except ImportError:
                # Fallback if fraud_detector import fails
                logger.warning("⚠️ Fraud detector import failed, using simplified analysis")
                return await self.simplified_safety_check(token_address)
            
        except Exception as e:
            logger.error(f"❌ Error in safety analysis: {e}")
            return False, 0.0
    
    async def simplified_safety_check(self, token_address: str) -> Tuple[bool, float]:
        """Simplified safety check using only DexScreener"""
        try:
            # Run DexScreener analysis
            dexscreener_score = await self.dexscreener_analysis(token_address)
            pattern_score = await self.pattern_analysis(token_address)
            
            # Calculate weighted score
            final_score = (dexscreener_score * 0.70) + (pattern_score * 0.30)
            is_safe = final_score >= self.safety_threshold
            
            logger.info(f"🔒 SIMPLIFIED SAFETY REPORT for {token_address[:8]}:")
            logger.info(f"   DexScreener: {dexscreener_score:.2f}")
            logger.info(f"   Pattern:     {pattern_score:.2f}")
            logger.info(f"   FINAL:       {final_score:.2f} ({'✓ SAFE' if is_safe else '⚠️ RISKY'})")
            
            return is_safe, final_score
            
        except Exception as e:
            logger.error(f"❌ Error in simplified safety check: {e}")
            return False, 0.0
    
    async def dexscreener_analysis(self, token_address: str) -> float:
        """DexScreener API analysis"""
        try:
            url = f"{self.dexscreener_url}/{token_address}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        pairs = data.get('pairs', [])
                        
                        if pairs:
                            # Get best pair
                            pair = max(pairs, key=lambda p: float(p.get('liquidity', {}).get('usd', 0)))
                            
                            liquidity_usd = float(pair.get('liquidity', {}).get('usd', 0))
                            volume_24h = float(pair.get('volume', {}).get('h24', 0))
                            
                            score = 0.20
                            
                            if liquidity_usd >= self.min_liquidity_usd * 3:
                                score += 0.35
                            elif liquidity_usd >= self.min_liquidity_usd:
                                score += 0.25
                            
                            if volume_24h >= self.min_volume_24h * 5:
                                score += 0.35
                            elif volume_24h >= self.min_volume_24h:
                                score += 0.25
                            
                            logger.info(f"📊 DexScreener: Liq=${liquidity_usd:,.0f}, Vol=${volume_24h:,.0f}")
                            return min(score, 1.0)
                        else:
                            logger.warning("⚠️ No trading pairs found on DexScreener")
                            return 0.15
                    else:
                        logger.warning(f"⚠️ DexScreener API error: {response.status}")
                        return 0.20
                        
        except Exception as e:
            logger.warning(f"⚠️ DexScreener analysis error: {e}")
            return 0.20
    
    async def pattern_analysis(self, token_address: str) -> float:
        """Basic pattern analysis"""
        try:
            score = 0.40  # Base score
            
            # Check address length
            if len(token_address) == 44:
                score += 0.20
            
            # Check character variety
            unique_chars = len(set(token_address))
            if unique_chars >= 20:
                score += 0.30
            elif unique_chars >= 15:
                score += 0.20
            
            # Check for suspicious patterns
            suspicious_patterns = ['1111', '0000', 'pump', 'scam']
            if not any(pattern in token_address.lower() for pattern in suspicious_patterns):
                score += 0.10
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.warning(f"⚠️ Pattern analysis error: {e}")
            return 0.50
    
    async def discover_new_tokens(self) -> List[str]:
        """Discover new tokens from various FREE sources"""
        try:
            new_tokens = []
            
            # Method 1: DexScreener trending/new tokens (FREE)
            dexscreener_tokens = await self.dexscreener_discovery()
            new_tokens.extend(dexscreener_tokens)
            
            # Method 2: Raydium public API (FREE)
            raydium_tokens = await self.raydium_discovery()
            new_tokens.extend(raydium_tokens)
            
            # Remove duplicates and filter out stablecoins/known tokens
            unique_tokens = list(set(new_tokens))
            filtered_tokens = self.filter_tokens(unique_tokens)
            
            logger.info(f"🔍 Discovered {len(filtered_tokens)} potential NEW tokens")
            return filtered_tokens[:10]  # Limit to top 10 newest
            
        except Exception as e:
            logger.error(f"❌ Error discovering tokens: {e}")
            return []
    
    async def dexscreener_discovery(self) -> List[str]:
        """Discover new tokens using DexScreener API (FREE)"""
        try:
            # DexScreener latest tokens on Solana
            url = "https://api.dexscreener.com/latest/dex/search/?q=solana"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        tokens = []
                        
                        for pair in data.get("pairs", [])[:20]:  # Top 20 newest
                            # Get base token (the new token, not SOL/USDC)
                            base_token = pair.get("baseToken", {})
                            quote_token = pair.get("quoteToken", {})
                            
                            base_address = base_token.get("address")
                            quote_address = quote_token.get("address")
                            
                            # Only take tokens paired with SOL or USDC
                            if quote_address in [self.sol_mint, self.usdc_mint] and base_address:
                                tokens.append(base_address)
                                logger.info(f"📍 Found token: {base_address[:8]}")
                        
                        return tokens[:15]  # Return top 15
                    else:
                        logger.warning(f"DexScreener discovery API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"DexScreener discovery error: {e}")
            return []
    
    async def raydium_discovery(self) -> List[str]:
        """Discover new tokens using Raydium public API (FREE)"""
        try:
            # Raydium V3 pools API
            url = "https://api-v3.raydium.io/pools/info/list"
            params = {
                "poolType": "all",
                "poolSortField": "default",
                "sortType": "desc",
                "pageSize": 30,
                "page": 1
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        tokens = []
                        
                        if data.get("success") and data.get("data"):
                            pools = data["data"]["data"]
                            
                            for pool in pools[:15]:  # Latest 15 pools
                                # Get mint A and mint B
                                mint_a = pool.get("mintA", {}).get("address")
                                mint_b = pool.get("mintB", {}).get("address")
                                
                                # Skip if one of the mints is SOL or USDC (we want the other token)
                                if mint_a == self.sol_mint or mint_a == self.usdc_mint:
                                    if mint_b and mint_b not in [self.sol_mint, self.usdc_mint]:
                                        tokens.append(mint_b)
                                        logger.info(f"📍 Raydium new token: {mint_b[:8]}")
                                elif mint_b == self.sol_mint or mint_b == self.usdc_mint:
                                    if mint_a and mint_a not in [self.sol_mint, self.usdc_mint]:
                                        tokens.append(mint_a)
                                        logger.info(f"📍 Raydium new token: {mint_a[:8]}")
                        
                        logger.info(f"📍 Raydium found {len(tokens)} new pool tokens")
                        return tokens
                    else:
                        logger.warning(f"Raydium API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Raydium discovery error: {e}")
            return []
    
    def filter_tokens(self, tokens: List[str]) -> List[str]:
        """Filter out known stablecoins and system tokens"""
        # Known tokens to skip (stablecoins, wrapped tokens, etc.)
        skip_tokens = {
            self.usdc_mint,  # USDC
            self.sol_mint,   # SOL
            "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
            "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",   # mSOL
            "7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj",   # stSOL
            "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",   # BONK
            "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn",   # JitoSOL
        }
        
        filtered = []
        for token in tokens:
            if token and token not in skip_tokens and len(token) == 44:  # Valid Solana address length
                filtered.append(token)
        
        logger.info(f"🔧 Filtered {len(tokens)} → {len(filtered)} tokens (removed known/stable tokens)")
        return filtered
    
    async def monitor_positions(self):
        """Monitor active positions for profit targets"""
        try:
            for token_address, position in list(self.active_positions.items()):
                # Check current price
                quote = await self.get_jupiter_quote(
                    input_mint=token_address,
                    output_mint=self.usdc_mint,
                    amount=position["token_amount"]
                )
                
                if quote:
                    current_value = int(quote["outAmount"])
                    entry_value = position["usdc_amount"]
                    profit_percent = ((current_value - entry_value) / entry_value) * 100
                    
                    logger.info(f"📈 Position {token_address[:8]}: {profit_percent:+.2f}%")
                    
                    # Check if profit target hit
                    if profit_percent >= self.profit_target:
                        await self.sell_position(token_address, position, current_value)
                    
                    # Check for stop loss (optional)
                    elif profit_percent <= -8:  # 8% stop loss
                        logger.warning(f"⚠️ Stop loss triggered for {token_address[:8]}")
                        await self.sell_position(token_address, position, current_value)
                        
        except Exception as e:
            logger.error(f"❌ Error monitoring positions: {e}")
    
    async def sell_position(self, token_address: str, position: Dict, current_value: int):
        """Sell a position"""
        try:
            quote = await self.get_jupiter_quote(
                input_mint=token_address,
                output_mint=self.usdc_mint,
                amount=position["token_amount"]
            )
            
            if quote:
                tx_id = await self.execute_jupiter_swap_with_retry(quote)
                if tx_id:
                    profit = current_value - position["usdc_amount"]
                    profit_percent = (profit / position["usdc_amount"]) * 100
                    
                    mode = "REAL" if self.enable_real_trading else "SIM"
                    logger.info(f"💰 {mode} SOLD: {token_address[:8]} → +${profit/1_000_000:.2f} ({profit_percent:+.2f}%)")
                    
                    # Update statistics
                    self.total_trades += 1
                    if profit > 0:
                        self.profitable_trades += 1
                        self.total_profit += profit / 1_000_000
                    
                    # Remove from active positions
                    del self.active_positions[token_address]
                    
                    # Log statistics
                    win_rate = (self.profitable_trades / self.total_trades) * 100 if self.total_trades > 0 else 0
                    logger.info(f"📊 Stats: {self.profitable_trades}/{self.total_trades} trades ({win_rate:.1f}% win rate), Total profit: ${self.total_profit:.2f}")
                    
        except Exception as e:
            logger.error(f"❌ Error selling position: {e}")
    
    async def execute_trade(self, token_address: str) -> bool:
        """Execute a trade for a token"""
        try:
            # Check if we have room for more positions
            if len(self.active_positions) >= self.max_positions:
                logger.info(f"⏳ Max positions ({self.max_positions}) reached, skipping trade")
                return False
            
            # Get quote for buying token with USDC
            quote = await self.get_jupiter_quote(
                input_mint=self.usdc_mint,
                output_mint=token_address,
                amount=self.trade_amount
            )
            
            if not quote:
                return False
            
            # Execute the swap with retry
            tx_id = await self.execute_jupiter_swap_with_retry(quote)
            if not tx_id:
                return False
            
            # Record the position
            token_amount = int(quote["outAmount"])
            self.active_positions[token_address] = {
                "entry_time": dt.now(),
                "tx_id": tx_id,
                "usdc_amount": self.trade_amount,
                "token_amount": token_amount,
                "entry_price": self.trade_amount / token_amount
            }
            
            mode = "REAL" if self.enable_real_trading else "SIM"
            logger.info(f"🚀 {mode} BOUGHT: ${self.trade_amount/1_000_000} → {token_amount/1_000_000:.6f} {token_address[:8]}")
            logger.info(f"📊 Active positions: {len(self.active_positions)}/{self.max_positions}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error executing trade: {e}")
            return False
    
    async def main_trading_loop(self):
        """Main trading loop"""
        logger.info("🔄 Starting main trading loop...")
        
        loop_count = 0
        while True:
            try:
                loop_count += 1
                logger.info(f"🔍 Trading loop #{loop_count}")
                
                # Monitor existing positions
                if self.active_positions:
                    await self.monitor_positions()
                
                # Look for new trading opportunities
                if len(self.active_positions) < self.max_positions:
                    logger.info("🔍 Scanning for new trading opportunities...")
                    
                    # Discover new tokens
                    new_tokens = await self.discover_new_tokens()
                    
                    for token_address in new_tokens:
                        # Skip if we already have this position
                        if token_address in self.active_positions:
                            continue
                        
                        # Check if token is safe
                        is_safe, confidence = await self.check_token_safety(token_address)
                        
                        if is_safe and confidence >= self.safety_threshold:
                            logger.info(f"✅ Safe token found: {token_address[:8]} (confidence: {confidence:.2f})")
                            
                            # Execute trade
                            success = await self.execute_trade(token_address)
                            if success:
                                break  # One trade per loop
                        else:
                            logger.info(f"⚠️ Risky token skipped: {token_address[:8]} (confidence: {confidence:.2f})")
                
                # Wait before next iteration
                await asyncio.sleep(60)  # 60 second intervals
                
            except KeyboardInterrupt:
                logger.info("🛑 Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Error in main loop: {e}")
                await asyncio.sleep(10)  # Wait before retrying
    
    async def run(self):
        """Start the trading bot"""
        logger.info("🚀 Starting Solana Trading Bot...")
        
        if self.enable_real_trading:
            logger.warning("⚠️⚠️⚠️ REAL TRADING MODE ENABLED ⚠️⚠️⚠️")
            logger.warning("⚠️ This bot will use REAL MONEY on Solana mainnet")
            logger.warning("⚠️ Ensure your wallet is funded with USDC and SOL")
            logger.warning("⚠️ Trades are IRREVERSIBLE on blockchain")
            
            # Give user 10 seconds to cancel if they didn't mean to enable real trading
            for i in range(10, 0, -1):
                logger.warning(f"⚠️ Starting real trading in {i} seconds... (Ctrl+C to cancel)")
                await asyncio.sleep(1)
        
        # Validate configuration
        if not await self.validate_configuration():
            logger.error("❌ Configuration validation failed")
            return
        
        logger.info("✅ Bot configuration validated")
        
        if self.enable_real_trading:
            logger.info("💸 Bot is now operational and ready for REAL TRADING!")
            logger.info(f"💰 Will trade REAL MONEY: ${self.trade_amount/1_000_000} per trade")
        else:
            logger.info("🎯 Bot is now operational in SIMULATION mode!")
            logger.info(f"💰 Simulating trades with ${self.trade_amount/1_000_000} amounts")
        
        logger.info(f"🔍 Looking for NEW token opportunities...")
        
        # Start main trading loop
        await self.main_trading_loop()

async def main():
    """Entry point"""
    try:
        bot = SolanaTradingBot()
        await bot.run()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
    finally:
        logger.info("🏁 Bot shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())
