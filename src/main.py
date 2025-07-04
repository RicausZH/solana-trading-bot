#!/usr/bin/env python3
"""
Solana Trading Bot - COMPLETE FIXED VERSION
Features: New Token Detection, Blacklist System, Duplicate Prevention, Optimized Execution
Updated: 2025-07-04 - All API endpoints fixed, blacklist system added
"""

import os
import asyncio
import aiohttp
import json
import base64
import logging
import time
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime as dt, datetime, timedelta
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
        """Initialize the trading bot with all features"""
        # Environment variables
        self.private_key = os.getenv("SOLANA_PRIVATE_KEY")
        self.public_key = os.getenv("SOLANA_PUBLIC_KEY") 
        self.rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
        self.quicknode_http = os.getenv("QUICKNODE_HTTP_URL")
        self.quicknode_wss = os.getenv("QUICKNODE_WSS_URL")
        
        # Trading control
        self.enable_real_trading = os.getenv("ENABLE_REAL_TRADING", "false").lower() == "true"
        
        # Trading configuration
        self.trade_amount = int(float(os.getenv("TRADE_AMOUNT", "1.0")) * 1_000_000)
        self.profit_target = float(os.getenv("PROFIT_TARGET", "3.0"))
        self.stop_loss_percent = float(os.getenv("STOP_LOSS_PERCENT", "15.0"))
        self.max_positions = int(os.getenv("MAX_POSITIONS", "10"))
        self.slippage = int(os.getenv("SLIPPAGE_BPS", "50"))
        
        # Token addresses
        self.usdc_mint = os.getenv("USDC_MINT", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
        self.sol_mint = os.getenv("SOL_MINT", "So11111111111111111111111111111111111111112")
        
        # Safety thresholds
        self.safety_threshold = float(os.getenv("SAFETY_THRESHOLD", "0.55"))
        self.min_liquidity_usd = float(os.getenv("MIN_LIQUIDITY_USD", "5000"))
        self.min_volume_24h = float(os.getenv("MIN_VOLUME_24H", "1000"))
        
        # API endpoints
        self.jupiter_quote_url = "https://quote-api.jup.ag/v6/quote"
        self.jupiter_swap_url = "https://quote-api.jup.ag/v6/swap"
        
        # Blacklist system
        self.blacklist_threshold = float(os.getenv("BLACKLIST_THRESHOLD", "20.0"))
        self.token_blacklist = set()
        self.blacklist_file = "token_blacklist.json"
        self.load_blacklist()
        
        # Trading state
        self.active_positions = {}
        self.recently_traded = set()
        self.total_trades = 0
        self.profitable_trades = 0
        self.total_profit = 0.0
        
        logger.info("🤖 Solana Trading Bot initialized with all features")
        logger.info(f"💰 Trade Amount: ${self.trade_amount/1_000_000}")
        logger.info(f"🎯 Profit Target: {self.profit_target}%")
        logger.info(f"🛑 Stop Loss: {self.stop_loss_percent}%")
        logger.info(f"📊 Max Positions: {self.max_positions}")
        logger.info(f"🚫 Blacklist threshold: {self.blacklist_threshold}%")
        logger.info(f"🚫 Blacklisted tokens: {len(self.token_blacklist)}")
        
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

    def add_to_blacklist(self, token_address: str, loss_percent: float):
        """Add token to blacklist"""
        if token_address not in self.token_blacklist:
            self.token_blacklist.add(token_address)
            self.save_blacklist()
            logger.warning(f"🚫 BLACKLISTED: {token_address[:8]} ({loss_percent:.2f}% loss)")
            logger.warning(f"🚫 Total blacklisted: {len(self.token_blacklist)}")

    async def pumpfun_discovery(self) -> List[str]:
        """Discover newly launched tokens from Pump.fun - FIXED VERSION"""
        try:
            url = "https://frontend-api.pump.fun/coins"
            params = {
                "offset": 0,
                "limit": 50,
                "sort": "created_timestamp",
                "order": "DESC"
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        tokens = []
                        current_time = time.time()
                        
                        coins = data if isinstance(data, list) else data.get('coins', [])
                        
                        for coin in coins[:30]:
                            created_timestamp = (
                                coin.get("created_timestamp") or 
                                coin.get("createdAt") or 
                                coin.get("timestamp")
                            )
                            
                            if not created_timestamp:
                                continue
                            
                            try:
                                if isinstance(created_timestamp, str):
                                    created_time = datetime.fromisoformat(created_timestamp.replace('Z', '+00:00')).timestamp()
                                else:
                                    created_time = float(created_timestamp)
                                    if created_time > 10**12:
                                        created_time = created_time / 1000
                            except:
                                continue
                            
                            hours_old = (current_time - created_time) / 3600
                            if hours_old > 6:  # Only tokens < 6 hours old
                                continue
                            
                            mint_address = coin.get("mint") or coin.get("address") or coin.get("token")
                            if mint_address and len(mint_address) == 44:
                                tokens.append(mint_address)
                                logger.info(f"📍 Pump.fun NEW: {mint_address[:8]} (age: {hours_old:.1f}h)")
                        
                        logger.info(f"📍 Pump.fun found {len(tokens)} tokens < 6h old")
                        return tokens[:10]
                        
                    else:
                        logger.warning(f"Pump.fun API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Pump.fun discovery error: {e}")
            return []

    async def dexscreener_discovery(self) -> List[str]:
        """Discover newly launched tokens using DexScreener - FIXED VERSION"""
        try:
            url = "https://api.dexscreener.com/latest/dex/pairs/solana"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        tokens = []
                        current_time = time.time()
                        
                        pairs = data.get("pairs", [])
                        if not pairs:
                            logger.warning("⚠️ DexScreener returned no pairs")
                            return []
                        
                        for pair in pairs[:100]:
                            created_at = (
                                pair.get("pairCreatedAt") or 
                                pair.get("createdAt") or
                                pair.get("firstSeenAt")
                            )
                            
                            if created_at:
                                try:
                                    if isinstance(created_at, str):
                                        created_timestamp = datetime.fromisoformat(created_at.replace('Z', '+00:00')).timestamp()
                                    else:
                                        created_timestamp = float(created_at)
                                        if created_timestamp > 10**12:
                                            created_timestamp = created_timestamp / 1000
                                    
                                    hours_old = (current_time - created_timestamp) / 3600
                                    if hours_old > 24:  # Only pairs < 24 hours old
                                        continue
                                        
                                except:
                                    continue
                            else:
                                continue
                            
                            base_token = pair.get("baseToken", {})
                            quote_token = pair.get("quoteToken", {})
                            
                            base_address = base_token.get("address")
                            quote_address = quote_token.get("address")
                            
                            if quote_address in [self.sol_mint, self.usdc_mint] and base_address:
                                liquidity = pair.get("liquidity", {}).get("usd", 0)
                                if liquidity and float(liquidity) > 1000:
                                    tokens.append(base_address)
                                    logger.info(f"📍 DexScreener NEW: {base_address[:8]} (age: {hours_old:.1f}h)")
                        
                        logger.info(f"📍 DexScreener found {len(tokens)} new pairs")
                        return tokens[:15]
                        
                    else:
                        logger.warning(f"DexScreener API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"DexScreener error: {e}")
            return []

    async def raydium_discovery(self) -> List[str]:
        """Discover newly created pools using Raydium - FIXED VERSION"""
        try:
            url = "https://api-v3.raydium.io/pools/info/list"
            params = {
                "poolType": "all",
                "poolSortField": "default",
                "sortType": "desc",
                "pageSize": 50,
                "page": 1
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        tokens = []
                        
                        if not data.get("success"):
                            logger.warning("⚠️ Raydium API unsuccessful")
                            return []
                        
                        pool_data = data.get("data", {})
                        pools = pool_data.get("data", []) if isinstance(pool_data, dict) else pool_data
                        
                        if not pools:
                            logger.warning("⚠️ Raydium returned no pools")
                            return []
                        
                        for pool in pools[:30]:
                            tvl = pool.get("tvl", 0)
                            
                            # Focus on newer pools with reasonable TVL
                            if not (1000 < float(tvl or 0) < 1000000):
                                continue
                            
                            mint_a = pool.get("mintA", {}).get("address")
                            mint_b = pool.get("mintB", {}).get("address")
                            
                            new_token = None
                            if mint_a in [self.sol_mint, self.usdc_mint]:
                                if mint_b and mint_b not in [self.sol_mint, self.usdc_mint]:
                                    new_token = mint_b
                            elif mint_b in [self.sol_mint, self.usdc_mint]:
                                if mint_a and mint_a not in [self.sol_mint, self.usdc_mint]:
                                    new_token = mint_a
                            
                            if new_token:
                                tokens.append(new_token)
                                logger.info(f"📍 Raydium pool: {new_token[:8]} (TVL: ${float(tvl or 0):,.0f})")
                        
                        logger.info(f"📍 Raydium found {len(tokens)} active pools")
                        return tokens[:15]
                        
                    else:
                        logger.warning(f"Raydium API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Raydium error: {e}")
            return []

    async def discover_new_tokens(self) -> List[str]:
        """Discover ONLY newly launched tokens from all sources"""
        try:
            new_tokens = []
            
            # Get tokens from all sources
            pumpfun_tokens = await self.pumpfun_discovery()
            new_tokens.extend(pumpfun_tokens)
            
            dexscreener_tokens = await self.dexscreener_discovery()
            new_tokens.extend(dexscreener_tokens)
            
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
        """Enhanced token filtering with blacklist and duplicate checking"""
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
        """Check if token is safe using simplified analysis"""
        try:
            if token_address == self.sol_mint:
                return False, 0.5
            
            logger.info(f"🔍 Analyzing token safety: {token_address}")
            
            # Run simplified safety analysis
            dexscreener_score = await self.dexscreener_analysis(token_address)
            pattern_score = await self.pattern_analysis(token_address)
            
            final_score = (dexscreener_score * 0.70) + (pattern_score * 0.30)
            is_safe = final_score >= self.safety_threshold
            
            logger.info(f"🔒 SAFETY REPORT for {token_address[:8]}:")
            logger.info(f"   DexScreener: {dexscreener_score:.2f}")
            logger.info(f"   Pattern:     {pattern_score:.2f}")
            logger.info(f"   FINAL:       {final_score:.2f} ({'✓ SAFE' if is_safe else '⚠️ RISKY'})")
            
            return is_safe, final_score
            
        except Exception as e:
            logger.error(f"❌ Error in safety analysis: {e}")
            return False, 0.0

    async def dexscreener_analysis(self, token_address: str) -> float:
        """DexScreener analysis for token safety"""
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            
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
            logger.warning(f"DexScreener analysis error: {e}")
            return 0.20

    async def pattern_analysis(self, token_address: str) -> float:
        """Basic pattern analysis for token addresses"""
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
            logger.warning(f"Pattern analysis error: {e}")
            return 0.50

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
                        logger.error(f"❌ Jupiter quote failed: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error getting Jupiter quote: {e}")
            return None

    async def send_transaction_ultra_minimal(self, transaction_data: str) -> Optional[str]:
        """Ultra-minimal transaction sending with size optimization"""
        try:
            logger.warning("⚠️ SENDING REAL TRANSACTION WITH REAL MONEY")
            
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
            
            # Send via RPC
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
        """Execute swap with progressive optimization"""
        try:
            if not self.enable_real_trading:
                tx_id = f"sim_{int(time.time())}"
                logger.info(f"✅ SIMULATED swap: {tx_id}")
                return tx_id
            
            # Try minimal parameters first
            swap_data = {
                "quoteResponse": quote,
                "userPublicKey": self.public_key,
                "wrapAndUnwrapSol": True,
                "useSharedAccounts": False,
                "asLegacyTransaction": True,
                "onlyDirectRoutes": True,
                "computeUnitPriceMicroLamports": 1000
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
                            transaction_bytes = base64.b64decode(transaction_data)
                            if len(transaction_bytes) > 1232:
                                logger.warning(f"⚠️ Transaction too large: {len(transaction_bytes)} bytes")
                                return None
                            
                            tx_id = await self.send_transaction_ultra_minimal(transaction_data)
                            if tx_id:
                                logger.info(f"✅ REAL SWAP EXECUTED: {tx_id}")
                                logger.info(f"🔗 View: https://explorer.solana.com/tx/{tx_id}")
                                return tx_id
                        
                        logger.error("❌ No transaction data")
                        return None
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Jupiter swap failed: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error executing swap: {e}")
            return None

    async def verify_token_balance(self, token_address: str, expected_amount: int) -> Tuple[bool, int]:
        """Verify actual token balance before selling"""
        try:
            from solders.pubkey import Pubkey
            from spl.token.constants import ASSOCIATED_TOKEN_PROGRAM_ID, TOKEN_PROGRAM_ID
            
            wallet_pubkey = Pubkey.from_string(self.public_key)
            token_pubkey = Pubkey.from_string(token_address)
            
            ata_address = Pubkey.find_program_address(
                [
                    bytes(wallet_pubkey),
                    bytes(TOKEN_PROGRAM_ID),
                    bytes(token_pubkey)
                ],
                ASSOCIATED_TOKEN_PROGRAM_ID
            )[0]
            
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
                    logger.info(f"💰 Balance check: Expected {expected_amount}, Actual {actual_amount}")
                    return actual_amount >= expected_amount, actual_amount
                else:
                    logger.warning(f"⚠️ Token account not found for {token_address[:8]}")
                    return False, 0
            else:
                logger.error(f"❌ Failed to check balance: {response.status_code}")
                return False, 0
                
        except Exception as e:
            logger.error(f"❌ Error verifying balance: {e}")
            return False, 0

    async def execute_trade(self, token_address: str) -> bool:
        """Execute trade with strict duplicate prevention"""
        try:
            # Critical checks
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
            
            # Get quote and execute
            quote = await self.get_jupiter_quote(
                input_mint=self.usdc_mint,
                output_mint=token_address,
                amount=self.trade_amount
            )
            
            if not quote:
                return False
            
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
            
            # Add to recently traded
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
                logger.error(f"❌ Insufficient balance: Expected {expected_amount}, Have {actual_amount}")
                
                if actual_amount > 0:
                    logger.info(f"🔄 Adjusting to actual balance: {actual_amount}")
                    position["token_amount"] = actual_amount
                else:
                    logger.error(f"❌ No tokens found, removing position")
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
                logger.error(f"❌ Failed to get sell quote")
                return False
                
            expected_usdc = int(quote["outAmount"])
            logger.info(f"📊 Sell quote: {position['token_amount']} tokens → ${expected_usdc/1_000_000:.2f} USDC")
            
            # Execute sell
            tx_id = await self.execute_jupiter_swap_optimized(quote)
            
            if tx_id:
                # Calculate profit
                original_usdc = position["usdc_amount"]
                profit_usdc = expected_usdc - original_usdc
                profit_percent = (profit_usdc / original_usdc) * 100
                
                # Blacklist check
                if profit_percent <= -self.blacklist_threshold:
                    self.add_to_blacklist(token_address, abs(profit_percent))
                
                mode = "REAL" if self.enable_real_trading else "SIM"
                logger.info(f"💰 {mode} SOLD: {token_address[:8]} → ${profit_usdc/1_000_000:+.2f} ({profit_percent:+.2f}%)")
                
                # Update statistics
                self.total_trades += 1
                if profit_usdc > 0:
                    self.profitable_trades += 1
                    self.total_profit += profit_usdc / 1_000_000
                
                # Remove position
                del self.active_positions[token_address]
                
                # Log stats
                win_rate = (self.profitable_trades / self.total_trades) * 100 if self.total_trades > 0 else 0
                logger.info(f"📊 Stats: {self.profitable_trades}/{self.total_trades} trades ({win_rate:.1f}% win rate), Total profit: ${self.total_profit:.2f}")
                
                return True
            else:
                logger.error(f"❌ Failed to execute sell")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error selling position: {e}")
            return False

    async def monitor_positions(self):
        """Monitor active positions for profit targets and stop losses"""
        try:
            if not self.active_positions:
                logger.info("📊 No active positions to monitor")
                return
                
            logger.info(f"📊 Monitoring {len(self.active_positions)} positions...")
            
            for token_address, position in list(self.active_positions.items()):
                try:
                    logger.info(f"🔍 Checking position: {token_address[:8]}")
                    
                    # Get current price
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
                        
                        # Check profit target
                        if profit_percent >= self.profit_target:
                            logger.info(f"🎯 PROFIT TARGET HIT: {profit_percent:.2f}% >= {self.profit_target}%")
                            success = await self.sell_position_verified(token_address, position, current_value)
                            if success:
                                logger.info(f"✅ Successfully sold position")
                            else:
                                logger.error(f"❌ Failed to sell position")
                        
                        # Check stop loss
                        elif profit_percent <= -self.stop_loss_percent:
                            logger.warning(f"🛑 STOP LOSS HIT: {profit_percent:.2f}% <= -{self.stop_loss_percent}%")
                            success = await self.sell_position_verified(token_address, position, current_value)
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

    async def main_trading_loop(self):
        """Main trading loop with enhanced diversification"""
        logger.info("🔄 Starting main trading loop with all features...")
        
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
                
                # Monitor existing positions
                if self.active_positions:
                    await self.monitor_positions()
                else:
                    logger.info("📊 No active positions to monitor")
                
                # Look for new opportunities
                available_slots = self.max_positions - len(self.active_positions)
                if available_slots > 0:
                    logger.info(f"🔍 Scanning for opportunities ({available_slots} slots available)")
                    
                    new_tokens = await self.discover_new_tokens()
                    
                    if not new_tokens:
                        logger.info("⏭️ No new tokens found")
                    else:
                        logger.info(f"🎯 Evaluating {len(new_tokens)} potential tokens")
                    
                    trades_this_cycle = 0
                    max_trades_per_cycle = min(2, available_slots)
                    
                    for token_address in new_tokens:
                        if trades_this_cycle >= max_trades_per_cycle:
                            logger.info(f"⏳ Max trades per cycle reached ({max_trades_per_cycle})")
                            break
                        
                        # Triple check for duplicates
                        if token_address in self.active_positions:
                            logger.info(f"⏭️ Skipping {token_address[:8]} - active position")
                            continue
                        
                        if token_address in self.recently_traded:
                            logger.info(f"⏭️ Skipping {token_address[:8]} - in cooldown")
                            continue
                        
                        # Safety check
                        is_safe, confidence = await self.check_token_safety(token_address)
                        
                        if is_safe and confidence >= self.safety_threshold:
                            logger.info(f"✅ NEW safe token: {token_address[:8]} (confidence: {confidence:.2f})")
                            
                            success = await self.execute_trade(token_address)
                            if success:
                                trades_this_cycle += 1
                                logger.info(f"🎯 Trade {trades_this_cycle}/{max_trades_per_cycle} completed")
                                await asyncio.sleep(5)
                            else:
                                logger.warning(f"⚠️ Trade failed for {token_address[:8]}")
                        else:
                            logger.info(f"⚠️ Risky token skipped: {token_address[:8]} (confidence: {confidence:.2f})")
                else:
                    logger.info(f"⏳ Max positions ({self.max_positions}) reached")
                
                # Status summary
                logger.info(f"📊 Summary: {len(self.active_positions)}/{self.max_positions} positions, {len(self.recently_traded)} cooldown, {len(self.token_blacklist)} blacklisted")
                
                # Wait before next iteration
                await asyncio.sleep(30)
                
            except KeyboardInterrupt:
                logger.info("🛑 Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Error in main loop: {e}")
                await asyncio.sleep(10)

    async def run(self):
        """Start the trading bot"""
        logger.info("🚀 Starting Solana Trading Bot with all features...")
        
        if self.enable_real_trading:
            logger.warning("⚠️⚠️⚠️ REAL TRADING MODE ENABLED ⚠️⚠️⚠️")
            logger.warning("⚠️ This bot will use REAL MONEY")
            
            for i in range(10, 0, -1):
                logger.warning(f"⚠️ Starting real trading in {i} seconds... (Ctrl+C to cancel)")
                await asyncio.sleep(1)
        
        logger.info("✅ Bot configuration validated")
        
        if self.enable_real_trading:
            logger.info("💸 Bot ready for REAL TRADING!")
        else:
            logger.info("🎯 Bot ready in SIMULATION mode!")
        
        logger.info(f"🔍 Looking for NEWLY LAUNCHED token opportunities...")
        
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
        
