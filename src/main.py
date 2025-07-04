#!/usr/bin/env python3
"""
Solana Trading Bot - NEW TOKEN FOCUS with Blacklist System
⚠️ WARNING: This version uses REAL MONEY on Solana mainnet
Enhanced Features: New token detection, blacklist system, duplicate prevention
Updated: 2025-07-04 - Complete rewrite with new token focus
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
from datetime import datetime as dt, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class SolanaTradingBot:
    def __init__(self):
        """Initialize the trading bot with enhanced new token detection"""
        # Environment variables
        self.private_key = os.getenv("SOLANA_PRIVATE_KEY")
        self.public_key = os.getenv("SOLANA_PUBLIC_KEY") 
        self.rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
        self.quicknode_http = os.getenv("QUICKNODE_HTTP_URL")
        
        # REAL TRADING CONTROL
        self.enable_real_trading = os.getenv("ENABLE_REAL_TRADING", "false").lower() == "true"
        
        # Trading configuration
        self.trade_amount = int(float(os.getenv("TRADE_AMOUNT", "1.0")) * 1_000_000)
        self.profit_target = float(os.getenv("PROFIT_TARGET", "3.0"))
        self.stop_loss_percent = float(os.getenv("STOP_LOSS_PERCENT", "15.0"))
        self.max_positions = int(os.getenv("MAX_POSITIONS", "10"))
        self.slippage = int(os.getenv("SLIPPAGE_BPS", "100"))
        
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
        
        # Security Analysis APIs
        self.dexscreener_url = "https://api.dexscreener.com/latest/dex/tokens"
        
        # Safety thresholds
        self.safety_threshold = float(os.getenv("SAFETY_THRESHOLD", "0.55"))
        self.min_liquidity_usd = float(os.getenv("MIN_LIQUIDITY_USD", "3000"))
        self.min_volume_24h = float(os.getenv("MIN_VOLUME_24H", "800"))
        
        # Token blacklist system
        self.token_blacklist = set()
        self.blacklist_threshold = float(os.getenv("BLACKLIST_THRESHOLD", "20.0"))
        self.blacklist_file = "token_blacklist.json"
        self.recently_traded = set()
        
        # Load existing blacklist
        self.load_blacklist()
        
        logger.info("🤖 Solana Trading Bot initialized - NEW TOKEN FOCUS")
        logger.info(f"💰 Trade Amount: ${self.trade_amount/1_000_000}")
        logger.info(f"🎯 Profit Target: {self.profit_target}%")
        logger.info(f"🛑 Stop Loss: {self.stop_loss_percent}%")
        logger.info(f"📊 Max Positions: {self.max_positions}")
        logger.info(f"🚫 Blacklist threshold: {self.blacklist_threshold}%")
        logger.info(f"🚫 Blacklisted tokens: {len(self.token_blacklist)}")
        
        # CRITICAL WARNING
        if self.enable_real_trading:
            logger.warning("⚠️ REAL TRADING ENABLED - WILL USE REAL MONEY!")
        else:
            logger.info("💡 Simulation mode - No real money will be used")
    
    def load_blacklist(self):
        """Load blacklist from persistent storage"""
        try:
            if os.path.exists(self.blacklist_file):
                with open(self.blacklist_file, 'r') as f:
                    data = json.load(f)
                    self.token_blacklist = set(data.get('blacklisted_tokens', []))
                    logger.info(f"📋 Loaded {len(self.token_blacklist)} blacklisted tokens")
            else:
                logger.info("📋 No existing blacklist file, starting fresh")
        except Exception as e:
            logger.error(f"❌ Error loading blacklist: {e}")
            self.token_blacklist = set()

    def save_blacklist(self):
        """Save blacklist to persistent storage"""
        try:
            blacklist_data = {
                'blacklisted_tokens': list(self.token_blacklist),
                'last_updated': dt.now().isoformat(),
                'threshold': self.blacklist_threshold
            }
            with open(self.blacklist_file, 'w') as f:
                json.dump(blacklist_data, f, indent=2)
            logger.info(f"💾 Saved {len(self.token_blacklist)} tokens to blacklist")
        except Exception as e:
            logger.error(f"❌ Error saving blacklist: {e}")

    def add_to_blacklist(self, token_address: str, loss_percent: float, reason: str = "high_loss"):
        """Add token to blacklist with logging"""
        if token_address not in self.token_blacklist:
            self.token_blacklist.add(token_address)
            self.save_blacklist()
            logger.warning(f"🚫 BLACKLISTED: {token_address[:8]} ({loss_percent:.2f}% loss)")
            logger.warning(f"🚫 Total blacklisted: {len(self.token_blacklist)}")
        else:
            logger.info(f"🚫 {token_address[:8]} already blacklisted")
    
    async def validate_configuration(self) -> bool:
        """Validate bot configuration"""
        if not self.private_key:
            logger.error("❌ SOLANA_PRIVATE_KEY not set")
            return False
        if not self.public_key:
            logger.error("❌ SOLANA_PUBLIC_KEY not set") 
            return False
        
        logger.info("✅ Configuration validated")
        return True
    
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
                        logger.error(f"❌ Jupiter quote failed: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error getting Jupiter quote: {e}")
            return None

    async def get_jupiter_quote_minimal(self, input_mint: str, output_mint: str, amount: int) -> Optional[Dict]:
        """Get quote with ultra-minimal routing for new tokens"""
        try:
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": amount,
                "slippageBps": 100,
                "onlyDirectRoutes": "true",
                "maxAccounts": "15",
                "asLegacyTransaction": "true"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.jupiter_quote_url, params=params) as response:
                    if response.status == 200:
                        quote = await response.json()
                        logger.info(f"📊 Minimal Quote: {int(quote['inAmount'])/1_000_000:.2f} → {int(quote['outAmount'])/1_000_000:.6f}")
                        return quote
                    else:
                        logger.error(f"❌ Minimal quote failed: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error getting minimal quote: {e}")
            return None

    async def send_transaction_ultra_minimal(self, transaction_data: str) -> Optional[str]:
        """Ultra-minimal transaction sending for new tokens"""
        try:
            logger.warning("⚠️ SENDING REAL TRANSACTION WITH REAL MONEY")
            
            # Decode and check size
            transaction_bytes = base64.b64decode(transaction_data)
            logger.info(f"📏 Transaction size: {len(transaction_bytes)} bytes")
            
            if len(transaction_bytes) > 1232:
                logger.error(f"❌ Transaction too large: {len(transaction_bytes)} bytes")
                return None
            
            # Use legacy transaction for smaller size
            try:
                from solana.transaction import Transaction
                from solders.keypair import Keypair
                
                transaction = Transaction.deserialize(transaction_bytes)
                keypair = Keypair.from_base58_string(self.private_key)
                transaction.sign(keypair)
                signed_tx_b64 = base64.b64encode(bytes(transaction)).decode('utf-8')
            except Exception as e:
                logger.error(f"❌ Transaction signing failed: {e}")
                return None
            
            # Ultra-minimal RPC call
            rpc_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "sendTransaction",
                "params": [
                    signed_tx_b64,
                    {
                        "skipPreflight": True,
                        "encoding": "base64",
                        "maxRetries": 0
                    }
                ]
            }
            
            response = requests.post(
                self.rpc_url,
                json=rpc_payload,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    tx_id = result["result"]
                    logger.info(f"✅ TRANSACTION SENT: {tx_id}")
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

    async def execute_jupiter_swap_optimized(self, quote: Dict) -> Optional[str]:
        """Execute swap with progressive optimization for new tokens"""
        try:
            # For simulation mode
            if not self.enable_real_trading:
                tx_id = f"sim_{int(time.time())}"
                logger.info(f"✅ SIMULATED swap: {tx_id}")
                return tx_id
            
            # Try minimal routing first
            logger.info("🔄 Attempting minimal route swap...")
            result = await self.execute_jupiter_swap_minimal(quote)
            if result:
                return result
            
            # Try fresh minimal quote
            logger.info("🔄 Attempting fresh minimal quote...")
            fresh_quote = await self.get_jupiter_quote_minimal(
                input_mint=quote.get("inputMint"),
                output_mint=quote.get("outputMint"),
                amount=int(quote.get("inAmount"))
            )
            
            if fresh_quote:
                result = await self.execute_jupiter_swap_minimal(fresh_quote)
                if result:
                    return result
            
            logger.error("❌ All optimization attempts failed")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error in optimized swap: {e}")
            return None

    async def execute_jupiter_swap_minimal(self, quote: Dict) -> Optional[str]:
        """Ultra-minimal swap execution for new tokens"""
        try:
            # Ultra-minimal swap data
            swap_data = {
                "quoteResponse": quote,
                "userPublicKey": self.public_key,
                "wrapAndUnwrapSol": True,
                "useSharedAccounts": False,
                "asLegacyTransaction": True,
                "onlyDirectRoutes": True,
                "maxAccounts": 20
            }
            
            headers = {"Content-Type": "application/json"}
            
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
                            # Check size before sending
                            transaction_bytes = base64.b64decode(transaction_data)
                            if len(transaction_bytes) > 1232:
                                logger.error(f"❌ Transaction too large: {len(transaction_bytes)} bytes")
                                return None
                            
                            tx_id = await self.send_transaction_ultra_minimal(transaction_data)
                            if tx_id:
                                logger.info(f"✅ SWAP EXECUTED: {tx_id}")
                                return tx_id
                        
                        logger.error("❌ No transaction data")
                        return None
                    else:
                        logger.error(f"❌ Swap failed: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error in minimal swap: {e}")
            return None

    async def verify_token_balance(self, token_address: str, expected_amount: int) -> Tuple[bool, int]:
        """Verify actual token balance before selling"""
        try:
            from solders.pubkey import Pubkey
            from spl.token.constants import ASSOCIATED_TOKEN_PROGRAM_ID, TOKEN_PROGRAM_ID
            
            # Calculate ATA address
            wallet_pubkey = Pubkey.from_string(self.public_key)
            token_pubkey = Pubkey.from_string(token_address)
            
            # Find Associated Token Account
            ata_address = Pubkey.find_program_address(
                [
                    bytes(wallet_pubkey),
                    bytes(TOKEN_PROGRAM_ID),
                    bytes(token_pubkey)
                ],
                ASSOCIATED_TOKEN_PROGRAM_ID
            )[0]
            
            # Get account balance via RPC
            rpc_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenAccountBalance",
                "params": [str(ata_address)]
            }
            
            response = requests.post(
                self.rpc_url,
                json=rpc_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if "result" in result and result["result"]["value"]:
                    actual_amount = int(result["result"]["value"]["amount"])
                    logger.info(f"💰 Balance: Expected {expected_amount}, Actual {actual_amount}")
                    return actual_amount >= expected_amount, actual_amount
                else:
                    logger.warning(f"⚠️ Token account not found")
                    return False, 0
            else:
                logger.error(f"❌ Balance check failed: {response.status_code}")
                return False, 0
                
        except Exception as e:
            logger.error(f"❌ Error verifying balance: {e}")
            return False, 0

    async def pumpfun_discovery(self) -> List[str]:
        """Discover newly launched tokens from Pump.fun"""
        try:
            url = "https://frontend-api.pump.fun/coins/latest"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        tokens = []
                        current_time = time.time()
                        
                        for coin in data[:30]:
                            created_timestamp = coin.get("created_timestamp")
                            if not created_timestamp:
                                continue
                            
                            try:
                                created_time = float(created_timestamp)
                            except:
                                continue
                            
                            # Only tokens created in last 6 hours
                            hours_old = (current_time - created_time) / 3600
                            if hours_old > 6:
                                continue
                            
                            mint_address = coin.get("mint")
                            if mint_address and len(mint_address) == 44:
                                tokens.append(mint_address)
                                logger.info(f"📍 Pump.fun NEW: {mint_address[:8]} ({hours_old:.1f}h old)")
                        
                        logger.info(f"📍 Pump.fun found {len(tokens)} tokens < 6h old")
                        return tokens[:10]
                    else:
                        logger.warning(f"Pump.fun API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Pump.fun discovery error: {e}")
            return []

    async def dexscreener_discovery(self) -> List[str]:
        """Discover newly created pairs using DexScreener"""
        try:
            url = "https://api.dexscreener.com/latest/dex/pairs/solana"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        tokens = []
                        current_time = time.time()
                        
                        for pair in data.get("pairs", [])[:50]:
                            created_at = pair.get("pairCreatedAt")
                            if not created_at:
                                continue
                            
                            try:
                                if isinstance(created_at, str):
                                    created_timestamp = dt.fromisoformat(created_at.replace('Z', '+00:00')).timestamp()
                                else:
                                    created_timestamp = created_at / 1000
                            except:
                                continue
                            
                            # Only pairs created in last 24 hours
                            hours_old = (current_time - created_timestamp) / 3600
                            if hours_old > 24:
                                continue
                            
                            base_token = pair.get("baseToken", {})
                            quote_token = pair.get("quoteToken", {})
                            
                            base_address = base_token.get("address")
                            quote_address = quote_token.get("address")
                            
                            if quote_address in [self.sol_mint, self.usdc_mint] and base_address:
                                tokens.append(base_address)
                                logger.info(f"📍 DexScreener NEW: {base_address[:8]} ({hours_old:.1f}h old)")
                        
                        logger.info(f"📍 DexScreener found {len(tokens)} pairs < 24h old")
                        return tokens[:15]
                    else:
                        logger.warning(f"DexScreener error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"DexScreener discovery error: {e}")
            return []

    async def raydium_discovery(self) -> List[str]:
        """Discover newly created pools using Raydium API"""
        try:
            url = "https://api-v3.raydium.io/pools/info/list"
            params = {
                "poolType": "all",
                "poolSortField": "created_time",
                "sortType": "desc",
                "pageSize": 50,
                "page": 1
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        tokens = []
                        current_time = time.time()
                        
                        if data.get("success") and data.get("data"):
                            pools = data["data"]["data"]
                            
                            for pool in pools:
                                created_time = pool.get("created_time")
                                if not created_time:
                                    continue
                                
                                # Only pools created in last 12 hours
                                hours_old = (current_time - created_time) / 3600
                                if hours_old > 12:
                                    continue
                                
                                mint_a = pool.get("mintA", {}).get("address")
                                mint_b = pool.get("mintB", {}).get("address")
                                
                                new_token = None
                                if mint_a == self.sol_mint or mint_a == self.usdc_mint:
                                    if mint_b and mint_b not in [self.sol_mint, self.usdc_mint]:
                                        new_token = mint_b
                                elif mint_b == self.sol_mint or mint_b == self.usdc_mint:
                                    if mint_a and mint_a not in [self.sol_mint, self.usdc_mint]:
                                        new_token = mint_a
                                
                                if new_token:
                                    tokens.append(new_token)
                                    logger.info(f"📍 Raydium NEW: {new_token[:8]} ({hours_old:.1f}h old)")
                            
                            logger.info(f"📍 Raydium found {len(tokens)} pools < 12h old")
                            return tokens[:15]
                        else:
                            return []
                    else:
                        logger.warning(f"Raydium API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Raydium discovery error: {e}")
            return []

    async def discover_new_tokens(self) -> List[str]:
        """Discover ONLY newly launched tokens from multiple sources"""
        try:
            new_tokens = []
            
            # Method 1: Pump.fun (newest tokens) - PRIMARY
            pumpfun_tokens = await self.pumpfun_discovery()
            new_tokens.extend(pumpfun_tokens)
            
            # Method 2: DexScreener new pairs (last 24h)
            dexscreener_tokens = await self.dexscreener_discovery()
            new_tokens.extend(dexscreener_tokens)
            
            # Method 3: Raydium new pools (last 12h)
            raydium_tokens = await self.raydium_discovery()
            new_tokens.extend(raydium_tokens)
            
            # Remove duplicates and filter
            unique_tokens = list(set(new_tokens))
            filtered_tokens = self.filter_tokens_enhanced(unique_tokens)
            
            # Prioritize Pump.fun tokens (newest)
            prioritized_tokens = []
            for token in filtered_tokens:
                if token in pumpfun_tokens:
                    prioritized_tokens.insert(0, token)
                else:
                    prioritized_tokens.append(token)
            
            logger.info(f"🔍 Discovered {len(prioritized_tokens)} NEWLY LAUNCHED tokens")
            logger.info(f"   Pump.fun: {len(pumpfun_tokens)} tokens")
            logger.info(f"   DexScreener: {len(dexscreener_tokens)} tokens")
            logger.info(f"   Raydium: {len(raydium_tokens)} tokens")
            
            return prioritized_tokens[:10]
            
        except Exception as e:
            logger.error(f"❌ Error discovering NEW tokens: {e}")
            return []

    def filter_tokens_enhanced(self, tokens: List[str]) -> List[str]:
        """Enhanced filtering with blacklist and duplicate prevention"""
        skip_tokens = {
            self.usdc_mint, self.sol_mint,
            "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
            "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",   # mSOL
            "7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj",   # stSOL
            "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",   # BONK
        }
        
        # Add active positions and blacklisted tokens
        skip_tokens.update(self.active_positions.keys())
        skip_tokens.update(self.token_blacklist)
        
        filtered = []
        blacklisted_count = 0
        
        for token in tokens:
            if token and len(token) == 44:
                if token in self.token_blacklist:
                    blacklisted_count += 1
                    continue
                elif token not in skip_tokens:
                    if token not in self.recently_traded:
                        filtered.append(token)
        
        logger.info(f"🔧 Filtered {len(tokens)} → {len(filtered)} tokens")
        logger.info(f"🚫 Blocked {blacklisted_count} blacklisted tokens")
        logger.info(f"🚫 Total blacklist: {len(self.token_blacklist)}")
        
        return filtered

    async def check_token_safety(self, token_address: str) -> Tuple[bool, float]:
        """Simple safety check for new tokens"""
        try:
            if token_address == self.sol_mint:
                return False, 0.5
            
            logger.info(f"🔍 Analyzing NEW token: {token_address}")
            
            # Simple analysis for new tokens
            dexscreener_score = await self.dexscreener_analysis(token_address)
            pattern_score = await self.pattern_analysis(token_address)
            
            final_score = (dexscreener_score * 0.70) + (pattern_score * 0.30)
            is_safe = final_score >= self.safety_threshold
            
            logger.info(f"🔒 NEW TOKEN SAFETY for {token_address[:8]}:")
            logger.info(f"   DexScreener: {dexscreener_score:.2f}")
            logger.info(f"   Pattern:     {pattern_score:.2f}")
            logger.info(f"   FINAL:       {final_score:.2f} ({'✓ SAFE' if is_safe else '⚠️ RISKY'})")
            
            return is_safe, final_score
            
        except Exception as e:
            logger.error(f"❌ Error analyzing token safety: {e}")
            return False, 0.0

    async def dexscreener_analysis(self, token_address: str) -> float:
        """DexScreener analysis for new tokens"""
        try:
            url = f"{self.dexscreener_url}/{token_address}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        pairs = data.get('pairs', [])
                        
                        if pairs:
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
                            return 0.15
                    else:
                        return 0.20
                        
        except Exception as e:
            logger.warning(f"⚠️ DexScreener analysis error: {e}")
            return 0.20

    async def pattern_analysis(self, token_address: str) -> float:
        """Basic pattern analysis for new tokens"""
        try:
            score = 0.40
            
            if len(token_address) == 44:
                score += 0.20
            
            unique_chars = len(set(token_address))
            if unique_chars >= 20:
                score += 0.30
            elif unique_chars >= 15:
                score += 0.20
            
            suspicious_patterns = ['1111', '0000', 'pump', 'scam']
            if not any(pattern in token_address.lower() for pattern in suspicious_patterns):
                score += 0.10
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.warning(f"⚠️ Pattern analysis error: {e}")
            return 0.50

    async def execute_trade(self, token_address: str) -> bool:
        """Execute trade with strict duplicate prevention"""
        try:
            # CRITICAL CHECKS
            if token_address in self.active_positions:
                logger.warning(f"🚫 DUPLICATE PREVENTED: {token_address[:8]}")
                return False
            
            if token_address in self.recently_traded:
                logger.warning(f"🚫 COOLDOWN ACTIVE: {token_address[:8]}")
                return False
            
            if len(self.active_positions) >= self.max_positions:
                logger.info(f"⏳ Max positions reached")
                return False
            
            logger.info(f"🎯 EXECUTING NEW TRADE: {token_address[:8]} (Position {len(self.active_positions)+1}/{self.max_positions})")
            
            # Get quote
            quote = await self.get_jupiter_quote(
                input_mint=self.usdc_mint,
                output_mint=token_address,
                amount=self.trade_amount
            )
            
            if not quote:
                return False
            
            # Execute swap
            tx_id = await self.execute_jupiter_swap_optimized(quote)
            if not tx_id:
                return False
            
            # Record position
            token_amount = int(quote["outAmount"])
            self.active_positions[token_address] = {
                "entry_time": dt.now(),
                "tx_id": tx_id,
                "usdc_amount": self.trade_amount,
                "token_amount": token_amount,
                "entry_price": self.trade_amount / token_amount,
                "token_address": token_address
            }
            
            # Add to cooldown
            self.recently_traded.add(token_address)
            
            mode = "REAL" if self.enable_real_trading else "SIM"
            logger.info(f"🚀 {mode} BOUGHT: ${self.trade_amount/1_000_000} → {token_amount/1_000_000:.6f} {token_address[:8]}")
            logger.info(f"📊 Active positions: {len(self.active_positions)}/{self.max_positions}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error executing trade: {e}")
            return False

    async def sell_position_verified(self, token_address: str, position: Dict, current_value: int) -> bool:
        """Sell position with balance verification and blacklist checking"""
        try:
            logger.info(f"💰 Attempting to sell: {token_address[:8]}")
            
            # Verify balance
            expected_amount = position["token_amount"]
            has_balance, actual_amount = await self.verify_token_balance(token_address, expected_amount)
            
            if not has_balance:
                if actual_amount > 0:
                    position["token_amount"] = actual_amount
                else:
                    if token_address in self.active_positions:
                        del self.active_positions[token_address]
                    return False
            
            # Get sell quote
            quote = await self.get_jupiter_quote(
                input_mint=token_address,
                output_mint=self.usdc_mint,
                amount=position["token_amount"]
            )
            
            if not quote:
                return False
                
            expected_usdc = int(quote["outAmount"])
            
            # Execute sell
            tx_id = await self.execute_jupiter_swap_optimized(quote)
            
            if tx_id:
                # Calculate profit
                original_usdc = position["usdc_amount"]
                profit_usdc = expected_usdc - original_usdc
                profit_percent = (profit_usdc / original_usdc) * 100
                
                # BLACKLIST CHECK
                if profit_percent <= -self.blacklist_threshold:
                    self.add_to_blacklist(token_address, abs(profit_percent), f"loss_{abs(profit_percent):.1f}%")
                
                mode = "REAL" if self.enable_real_trading else "SIM"
                logger.info(f"💰 {mode} SOLD: {token_address[:8]} → ${profit_usdc/1_000_000:+.2f} ({profit_percent:+.2f}%)")
                
                # Update stats
                self.total_trades += 1
                if profit_usdc > 0:
                    self.profitable_trades += 1
                    self.total_profit += profit_usdc / 1_000_000
                
                # Remove position
                del self.active_positions[token_address]
                
                # Log stats
                win_rate = (self.profitable_trades / self.total_trades) * 100 if self.total_trades > 0 else 0
                logger.info(f"📊 Stats: {self.profitable_trades}/{self.total_trades} trades ({win_rate:.1f}% win rate), Profit: ${self.total_profit:.2f}")
                
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in verified sell: {e}")
            return False

    async def monitor_positions(self):
        """Monitor positions for profit targets and stop losses"""
        try:
            if not self.active_positions:
                return
                
            logger.info(f"📊 Monitoring {len(self.active_positions)} positions...")
            
            for token_address, position in list(self.active_positions.items()):
                try:
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
                        
                        # Check profit target
                        if profit_percent >= self.profit_target:
                            logger.info(f"🎯 PROFIT TARGET HIT: {profit_percent:.2f}%")
                            await self.sell_position_verified(token_address, position, current_value)
                        
                        # Check stop loss
                        elif profit_percent <= -self.stop_loss_percent:
                            logger.warning(f"🛑 STOP LOSS HIT: {profit_percent:.2f}%")
                            await self.sell_position_verified(token_address, position, current_value)
                        
                        else:
                            logger.info(f"⏳ Holding: {profit_percent:+.2f}%")
                            
                except Exception as e:
                    logger.error(f"❌ Error checking {token_address[:8]}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error monitoring positions: {e}")

    async def main_trading_loop(self):
        """Main trading loop with new token focus"""
        logger.info("🔄 Starting NEW TOKEN trading loop...")
        
        last_cooldown_cleanup = time.time()
        loop_count = 0
        
        while True:
            try:
                loop_count += 1
                logger.info(f"🔍 Trading loop #{loop_count}")
                
                # Clean cooldown every 15 minutes
                if time.time() - last_cooldown_cleanup > 900:
                    cooldown_size = len(self.recently_traded)
                    self.recently_traded.clear()
                    last_cooldown_cleanup = time.time()
                    logger.info(f"🧹 Cleared {cooldown_size} tokens from cooldown")
                
                # Monitor positions
                if self.active_positions:
                    await self.monitor_positions()
                
                # Look for new opportunities
                available_slots = self.max_positions - len(self.active_positions)
                if available_slots > 0:
                    logger.info(f"🔍 Scanning for NEW tokens ({available_slots} slots available)...")
                    
                    new_tokens = await self.discover_new_tokens()
                    
                    if not new_tokens:
                        logger.info("⏭️ No new tokens found")
                    else:
                        logger.info(f"🎯 Evaluating {len(new_tokens)} NEW tokens...")
                    
                    trades_this_cycle = 0
                    max_trades_per_cycle = min(2, available_slots)
                    
                    for token_address in new_tokens:
                        if trades_this_cycle >= max_trades_per_cycle:
                            break
                        
                        # Triple-check duplicates
                        if token_address in self.active_positions:
                            logger.info(f"⏭️ Skipping {token_address[:8]} - active position")
                            continue
                        
                        if token_address in self.recently_traded:
                            logger.info(f"⏭️ Skipping {token_address[:8]} - cooldown")
                            continue
                        
                        # Safety check
                        is_safe, confidence = await self.check_token_safety(token_address)
                        
                        if is_safe and confidence >= self.safety_threshold:
                            logger.info(f"✅ NEW safe token: {token_address[:8]} ({confidence:.2f})")
                            
                            success = await self.execute_trade(token_address)
                            if success:
                                trades_this_cycle += 1
                                await asyncio.sleep(5)
                        else:
                            logger.info(f"⚠️ Risky token: {token_address[:8]} ({confidence:.2f})")
                else:
                    logger.info(f"⏳ Max positions reached, monitoring only")
                
                # Status summary
                logger.info(f"📊 Summary: {len(self.active_positions)}/{self.max_positions} positions, {len(self.recently_traded)} cooldown, {len(self.token_blacklist)} blacklisted")
                
                # Wait
                await asyncio.sleep(30)
                
            except KeyboardInterrupt:
                logger.info("🛑 Bot stopped")
                break
            except Exception as e:
                logger.error(f"❌ Error in main loop: {e}")
                await asyncio.sleep(10)

    async def run(self):
        """Start the NEW TOKEN trading bot"""
        logger.info("🚀 Starting NEW TOKEN Solana Trading Bot...")
        
        if self.enable_real_trading:
            logger.warning("⚠️⚠️⚠️ REAL TRADING MODE ENABLED ⚠️⚠️⚠️")
            for i in range(10, 0, -1):
                logger.warning(f"⚠️ Starting real trading in {i} seconds...")
                await asyncio.sleep(1)
        
        # Validate config
        if not await self.validate_configuration():
            return
        
        logger.info("✅ Bot ready for NEW TOKEN trading!")
        
        if self.enable_real_trading:
            logger.info("💸 REAL TRADING active!")
        else:
            logger.info("🎯 SIMULATION mode active!")
        
        logger.info(f"🔍 Focus: NEWLY LAUNCHED tokens only")
        
        # Start trading
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
    
