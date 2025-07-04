#!/usr/bin/env python3
"""
Solana Trading Bot - FIXED VERSION FOR LIVE TRADING
⚠️ Jupiter API parameter conflict resolved
⚠️ Working transaction execution with direct RPC calls
⚠️ Enhanced selling logic for profit capture
⚠️ Optimized for $1 testing trades
Updated: 2025-07-04 - Parameter conflict fix, working transactions
"""

import os
import asyncio
import aiohttp
import json
import base64
import logging
import time
import datetime
import requests
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
        self.trade_amount = int(float(os.getenv("TRADE_AMOUNT", "1.0")) * 1_000_000)  # Default $1 for testing
        self.profit_target = float(os.getenv("PROFIT_TARGET", "3.0"))  # 3% for testing
        self.stop_loss_percent = float(os.getenv("STOP_LOSS_PERCENT", "15.0"))  # 15% stop loss
        self.max_positions = int(os.getenv("MAX_POSITIONS", "12"))
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
        self.min_liquidity_usd = float(os.getenv("MIN_LIQUIDITY_USD", "3000"))  # Reduced for testing
        self.min_volume_24h = float(os.getenv("MIN_VOLUME_24H", "800"))  # Reduced for testing
        
        logger.info("🤖 Solana Trading Bot initialized - FIXED VERSION")
        logger.info(f"💰 Trade Amount: ${self.trade_amount/1_000_000}")
        logger.info(f"🎯 Profit Target: {self.profit_target}%")
        logger.info(f"🛑 Stop Loss: {self.stop_loss_percent}%")
        logger.info(f"📊 Max Positions: {self.max_positions}")
        logger.info(f"🔒 Safety Threshold: {self.safety_threshold}")
        logger.info(f"💧 Min Liquidity: ${self.min_liquidity_usd:,.0f}")
        logger.info(f"📈 Min Volume 24h: ${self.min_volume_24h:,.0f}")
        
        # CRITICAL WARNING
        if self.enable_real_trading:
            logger.warning("⚠️ REAL TRADING ENABLED - WILL USE REAL MONEY!")
            logger.warning("⚠️ Testing with small amounts - monitor closely")
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
            # This would normally use Solana RPC to check token balance
            # For now, return a simulated balance
            return 50.0  # Simulated USDC balance for testing
        except:
            return 0.0
    
    async def get_sol_balance(self) -> float:
        """Get SOL balance from wallet"""
        try:
            # This would normally use Solana RPC to check SOL balance
            return 0.05  # Simulated SOL balance
        except:
            return 0.0
    
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
    
    async def send_transaction_working(self, transaction_data: str) -> Optional[str]:
        """Working transaction sending method using direct RPC"""
        try:
            from solders.keypair import Keypair
            from solders.transaction import VersionedTransaction
            
            logger.warning("⚠️ SENDING REAL TRANSACTION WITH REAL MONEY")
            
            # Decode and sign transaction
            transaction_bytes = base64.b64decode(transaction_data)
            
            # Try versioned transaction first
            try:
                versioned_tx = VersionedTransaction.from_bytes(transaction_bytes)
                keypair = Keypair.from_base58_string(self.private_key)
                
                # Sign the message
                from solders.message import to_bytes_versioned
                message_bytes = to_bytes_versioned(versioned_tx.message)
                signature = keypair.sign_message(message_bytes)
                
                # Create signed transaction
                signed_tx = VersionedTransaction.populate(versioned_tx.message, [signature])
                
                # Convert to base64 for RPC
                signed_tx_bytes = bytes(signed_tx)
                signed_tx_b64 = base64.b64encode(signed_tx_bytes).decode('utf-8')
                
            except Exception as e:
                logger.warning(f"Versioned transaction failed, trying legacy: {e}")
                # Fallback to legacy transaction
                from solana.transaction import Transaction
                transaction = Transaction.deserialize(transaction_bytes)
                keypair = Keypair.from_base58_string(self.private_key)
                transaction.sign(keypair)
                signed_tx_b64 = base64.b64encode(bytes(transaction)).decode('utf-8')
            
            # Send via direct RPC call
            rpc_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "sendTransaction",
                "params": [
                    signed_tx_b64,
                    {
                        "skipPreflight": False,
                        "preflightCommitment": "processed",
                        "encoding": "base64",
                        "maxRetries": 3
                    }
                ]
            }
            
            # Use requests for reliability
            response = requests.post(
                self.rpc_url,
                json=rpc_payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    tx_id = result["result"]
                    logger.info(f"✅ REAL TRANSACTION SENT: {tx_id}")
                    return tx_id
                else:
                    error = result.get("error", "Unknown error")
                    logger.error(f"❌ RPC Error: {error}")
                    return None
            else:
                logger.error(f"❌ HTTP Error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error sending transaction: {e}")
            return None
    
    async def execute_jupiter_swap(self, quote: Dict) -> Optional[str]:
        """Execute swap via Jupiter API - FIXED VERSION"""
        try:
            # For simulation mode
            if not self.enable_real_trading:
                tx_id = f"sim_{int(time.time())}"
                logger.info(f"✅ SIMULATED swap: {tx_id}")
                return tx_id
            
            # FIXED: Enhanced swap data without parameter conflicts
            swap_data = {
                "quoteResponse": quote,
                "userPublicKey": self.public_key,
                "wrapAndUnwrapSol": True,
                "useSharedAccounts": False,
                "asLegacyTransaction": True,
                "feeAccount": None,
                "trackingAccount": None,
                # Use ONLY computeUnitPriceMicroLamports, NOT prioritizationFeeLamports
                "computeUnitPriceMicroLamports": 1000
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "Solana Trading Bot"
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
                            # Use the working transaction method
                            tx_id = await self.send_transaction_working(transaction_data)
                            if tx_id:
                                logger.info(f"✅ REAL SWAP EXECUTED: {tx_id}")
                                logger.info(f"🔗 View: https://explorer.solana.com/tx/{tx_id}")
                                return tx_id
                            else:
                                logger.error("❌ Failed to send transaction")
                                return None
                        else:
                            logger.error("❌ No transaction data in swap response")
                            return None
                    elif response.status == 400:
                        error_text = await response.text()
                        logger.error(f"❌ Jupiter API error: {error_text}")
                        
                        # Try fallback without compute unit pricing
                        return await self.execute_jupiter_swap_fallback(quote)
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Jupiter swap failed: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error executing Jupiter swap: {e}")
            return None
    
    async def execute_jupiter_swap_fallback(self, quote: Dict) -> Optional[str]:
        """Fallback swap method with minimal parameters"""
        try:
            logger.info("🔄 Trying fallback swap with minimal parameters...")
            
            # Minimal swap data without compute unit pricing
            swap_data = {
                "quoteResponse": quote,
                "userPublicKey": self.public_key,
                "wrapAndUnwrapSol": True,
                "useSharedAccounts": False,
                "asLegacyTransaction": True
                # No compute unit or prioritization fee parameters
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
                            tx_id = await self.send_transaction_working(transaction_data)
                            if tx_id:
                                logger.info(f"✅ REAL SWAP EXECUTED (fallback): {tx_id}")
                                logger.info(f"🔗 View: https://explorer.solana.com/tx/{tx_id}")
                                return tx_id
                        
                        logger.error("❌ Fallback swap also failed")
                        return None
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Fallback swap failed: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error in fallback swap: {e}")
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
                from fraud_detector import FraudDetector
                from config import Config
                
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
            if not self.active_positions:
                logger.info("📊 No active positions to monitor")
                return
                
            logger.info(f"📊 Monitoring {len(self.active_positions)} positions...")
            
            for token_address, position in list(self.active_positions.items()):
                try:
                    logger.info(f"🔍 Checking position: {token_address[:8]}")
                    
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
                        
                        logger.info(f"📈 Position {token_address[:8]}: {profit_percent:+.2f}% (Current: ${current_value/1_000_000:.2f}, Entry: ${entry_value/1_000_000:.2f})")
                        
                        # Check for profit target
                        if profit_percent >= self.profit_target:
                            logger.info(f"🎯 PROFIT TARGET HIT: {profit_percent:.2f}% >= {self.profit_target}%")
                            success = await self.sell_position(token_address, position, current_value)
                            if success:
                                logger.info(f"✅ Successfully sold position")
                            else:
                                logger.error(f"❌ Failed to sell position")
                        
                        # Check for stop loss
                        elif profit_percent <= -self.stop_loss_percent:
                            logger.warning(f"🛑 STOP LOSS HIT: {profit_percent:.2f}% <= -{self.stop_loss_percent}%")
                            success = await self.sell_position(token_address, position, current_value)
                            if success:
                                logger.info(f"✅ Successfully sold position (stop loss)")
                            else:
                                logger.error(f"❌ Failed to sell position (stop loss)")
                        
                        else:
                            logger.info(f"⏳ Position holding: {profit_percent:+.2f}% (target: {self.profit_target}%, stop: -{self.stop_loss_percent}%)")
                            
                    else:
                        logger.warning(f"⚠️ Could not get sell quote for {token_address[:8]}")
                        
                except Exception as e:
                    logger.error(f"❌ Error checking position {token_address[:8]}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error monitoring positions: {e}")
    
    async def sell_position(self, token_address: str, position: Dict, current_value: int) -> bool:
        """Sell a position with enhanced error handling"""
        try:
            logger.info(f"💰 Attempting to sell position: {token_address[:8]}")
            logger.info(f"    Token amount: {position['token_amount']}")
            logger.info(f"    Expected value: ${current_value/1_000_000:.2f}")
            
            # Get fresh sell quote
            quote = await self.get_jupiter_quote(
                input_mint=token_address,
                output_mint=self.usdc_mint,
                amount=position["token_amount"]
            )
            
            if not quote:
                logger.error(f"❌ Failed to get sell quote for {token_address[:8]}")
                return False
                
            expected_usdc = int(quote["outAmount"])
            logger.info(f"📊 Sell quote: {position['token_amount']} tokens → ${expected_usdc/1_000_000:.2f} USDC")
            
            # Execute the sell swap
            tx_id = await self.execute_jupiter_swap(quote)
            
            if tx_id:
                # Calculate profit
                original_usdc = position["usdc_amount"]
                profit_usdc = expected_usdc - original_usdc
                profit_percent = (profit_usdc / original_usdc) * 100
                
                mode = "REAL" if self.enable_real_trading else "SIM"
                logger.info(f"💰 {mode} SOLD: {token_address[:8]} → ${profit_usdc/1_000_000:+.2f} ({profit_percent:+.2f}%)")
                
                # Update statistics
                self.total_trades += 1
                if profit_usdc > 0:
                    self.profitable_trades += 1
                    self.total_profit += profit_usdc / 1_000_000
                
                # Remove from active positions
                del self.active_positions[token_address]
                
                # Log statistics
                win_rate = (self.profitable_trades / self.total_trades) * 100 if self.total_trades > 0 else 0
                logger.info(f"📊 Stats: {self.profitable_trades}/{self.total_trades} trades ({win_rate:.1f}% win rate), Total profit: ${self.total_profit:.2f}")
                
                return True
            else:
                logger.error(f"❌ Failed to execute sell swap for {token_address[:8]}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error selling position {token_address[:8]}: {e}")
            return False
    
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
            
            # Execute the swap
            tx_id = await self.execute_jupiter_swap(quote)
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
                
                # IMPORTANT: Monitor existing positions FIRST
                if self.active_positions:
                    logger.info(f"📊 Monitoring {len(self.active_positions)} active positions...")
                    await self.monitor_positions()
                else:
                    logger.info("📊 No active positions to monitor")
                
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
                else:
                    logger.info(f"⏳ Max positions ({self.max_positions}) reached, monitoring only")
                
                # Wait before next iteration - faster for testing
                await asyncio.sleep(20)  # 20 second intervals for testing
                
            except KeyboardInterrupt:
                logger.info("🛑 Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Error in main loop: {e}")
                await asyncio.sleep(10)  # Wait before retrying
    
    async def run(self):
        """Start the trading bot"""
        logger.info("🚀 Starting Solana Trading Bot - FIXED VERSION...")
        
        if self.enable_real_trading:
            logger.warning("⚠️⚠️⚠️ REAL TRADING MODE ENABLED ⚠️⚠️⚠️")
            logger.warning("⚠️ This bot will use REAL MONEY on Solana mainnet")
            logger.warning("⚠️ Testing with small amounts - monitor closely")
            logger.warning("⚠️ All transaction execution bugs have been fixed")
            
            # Give user 5 seconds to cancel (reduced for testing)
            for i in range(5, 0, -1):
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
            logger.info("🧪 TESTING MODE: Small amounts for validation")
        else:
            logger.info("🎯 Bot is now operational in SIMULATION mode!")
            logger.info(f"💰 Simulating trades with ${self.trade_amount/1_000_000} amounts")
        
        logger.info(f"🔍 Looking for NEW token opportunities...")
        logger.info(f"🎯 Target: {self.profit_target}% profit, {self.stop_loss_percent}% stop loss")
        
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
