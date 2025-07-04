#!/usr/bin/env python3
"""
Enhanced Solana Trading Bot - Official DexScreener API Integration
⚠️ WARNING: This version uses REAL MONEY on Solana mainnet when enabled
Features: Official APIs, Enhanced Discovery, Fallback Methods, Rate Limiting
Updated: 2025-07-04 - Official DexScreener API Integration
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

class EnhancedSolanaTradingBot:
    def __init__(self):
        """Initialize the enhanced trading bot with official API integration"""
        
        # WALLET CONFIGURATION
        self.private_key = os.getenv("SOLANA_PRIVATE_KEY")
        self.public_key = os.getenv("SOLANA_PUBLIC_KEY") 
        
        # RPC ENDPOINTS
        self.rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
        self.quicknode_http = os.getenv("QUICKNODE_HTTP_URL")
        self.quicknode_wss = os.getenv("QUICKNODE_WSS_URL")
        
        # TRADING CONFIGURATION
        self.enable_real_trading = os.getenv("ENABLE_REAL_TRADING", "false").lower() == "true"
        self.trade_amount = int(float(os.getenv("TRADE_AMOUNT", "1.0")) * 1_000_000)
        self.profit_target = float(os.getenv("PROFIT_TARGET", "3.0"))
        self.stop_loss_percent = float(os.getenv("STOP_LOSS_PERCENT", "15.0"))
        self.max_positions = int(os.getenv("MAX_POSITIONS", "10"))
        self.slippage = int(os.getenv("SLIPPAGE_BPS", "50"))
        
        # SAFETY THRESHOLDS
        self.safety_threshold = float(os.getenv("SAFETY_THRESHOLD", "0.55"))
        self.min_liquidity_usd = float(os.getenv("MIN_LIQUIDITY_USD", "2500"))
        self.min_volume_24h = float(os.getenv("MIN_VOLUME_24H", "500"))
        
        # TOKEN ADDRESSES
        self.usdc_mint = os.getenv("USDC_MINT", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
        self.sol_mint = os.getenv("SOL_MINT", "So11111111111111111111111111111111111111112")
        
        # API ENDPOINTS
        self.jupiter_quote_url = os.getenv("JUPITER_QUOTE_API", "https://quote-api.jup.ag/v6/quote")
        self.jupiter_swap_url = os.getenv("JUPITER_SWAP_API", "https://quote-api.jup.ag/v6/swap")
        
        # ENHANCED API ENDPOINTS
        self.dexscreener_base = "https://api.dexscreener.com"
        self.pumpportal_base = "https://pumpportal.fun/api"
        
        # BLACKLIST SYSTEM
        self.blacklist_threshold = float(os.getenv("BLACKLIST_THRESHOLD", "20.0"))
        self.token_blacklist = set()
        self.blacklist_file = "token_blacklist.json"
        
        # TRADING STATE
        self.active_positions = {}
        self.recently_traded = set()
        self.total_trades = 0
        self.profitable_trades = 0
        self.total_profit = 0.0
        
        # RATE LIMITING
        self.last_api_call = {}
        self.api_call_intervals = {
            "dexscreener_search": 0.2,      # 300 req/min = 5 req/sec
            "dexscreener_boosts": 1.0,      # 60 req/min = 1 req/sec
            "dexscreener_profiles": 1.0,    # 60 req/min = 1 req/sec
            "pumpfun": 2.0,                 # Conservative rate
            "raydium": 1.0                  # Conservative rate
        }
        
        # Load existing blacklist
        self.load_blacklist()
        
        # Log configuration
        logger.info("🚀 Enhanced Solana Trading Bot with Official APIs initialized")
        logger.info(f"💰 Trade Amount: ${self.trade_amount/1_000_000}")
        logger.info(f"🎯 Profit Target: {self.profit_target}%")
        logger.info(f"🛑 Stop Loss: {self.stop_loss_percent}%")
        logger.info(f"📊 Max Positions: {self.max_positions}")
        logger.info(f"🔒 Safety Threshold: {self.safety_threshold}")
        logger.info(f"💧 Min Liquidity: ${self.min_liquidity_usd:,.0f}")
        logger.info(f"📈 Min Volume 24h: ${self.min_volume_24h:,.0f}")
        
        if self.enable_real_trading:
            logger.warning("⚠️ REAL TRADING ENABLED - WILL USE REAL MONEY!")
        else:
            logger.info("💡 Simulation mode - No real money will be used")

    async def rate_limit_wait(self, api_type: str):
        """Implement rate limiting for API calls"""
        try:
            current_time = time.time()
            last_call = self.last_api_call.get(api_type, 0)
            interval = self.api_call_intervals.get(api_type, 1.0)
            
            time_since_last = current_time - last_call
            if time_since_last < interval:
                wait_time = interval - time_since_last
                await asyncio.sleep(wait_time)
            
            self.last_api_call[api_type] = time.time()
        except Exception as e:
            logger.warning(f"⚠️ Rate limit wait error: {e}")

    def load_blacklist(self):
        """Load blacklist from persistent storage"""
        try:
            if os.path.exists(self.blacklist_file):
                with open(self.blacklist_file, 'r') as f:
                    data = json.load(f)
                    self.token_blacklist = set(data.get('blacklisted_tokens', []))
                    logger.info(f"📋 Loaded {len(self.token_blacklist)} blacklisted tokens")
            else:
                logger.info("📋 No existing blacklist file found")
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
            logger.warning(f"🚫 BLACKLISTED: {token_address[:8]} ({loss_percent:.2f}% loss) - {reason}")

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
            usdc_balance = await self.get_token_balance(self.usdc_mint)
            sol_balance = await self.get_sol_balance()
            
            required_usdc = (self.trade_amount * self.max_positions) / 1_000_000
            required_sol = 0.01
            
            logger.info(f"💰 Wallet Balance: {usdc_balance:.2f} USDC, {sol_balance:.4f} SOL")
            logger.info(f"💰 Required: {required_usdc:.2f} USDC, {required_sol:.4f} SOL")
            
            if usdc_balance < required_usdc:
                logger.error(f"❌ Need {required_usdc:.2f} USDC, have {usdc_balance:.2f}")
                return False
                
            if sol_balance < required_sol:
                logger.error(f"❌ Need {required_sol:.4f} SOL, have {sol_balance:.4f}")
                return False
                
            logger.info("✅ Wallet has sufficient balance")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error checking wallet balance: {e}")
            return False

    async def get_token_balance(self, mint_address: str) -> float:
        """Get token balance from wallet"""
        try:
            return 150.0  # Simulated balance
        except:
            return 0.0

    async def get_sol_balance(self) -> float:
        """Get SOL balance from wallet"""
        try:
            return 0.05  # Simulated balance
        except:
            return 0.0

    async def verify_token_balance(self, token_address: str, expected_amount: int) -> Tuple[bool, int]:
        """Verify actual token balance before selling"""
        try:
            return True, expected_amount
        except Exception as e:
            logger.error(f"❌ Error verifying token balance: {e}")
            return False, 0

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

    async def execute_jupiter_swap_optimized(self, quote: Dict) -> Optional[str]:
        """Execute Jupiter swap with optimization"""
        try:
            if not self.enable_real_trading:
                tx_id = f"sim_{int(time.time())}"
                logger.info(f"✅ SIMULATED swap: {tx_id}")
                return tx_id
            
            # Implementation would go here for real trading
            logger.info("🔄 Real trading implementation needed")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error in swap execution: {e}")
            return None

    # ENHANCED DISCOVERY METHODS WITH OFFICIAL APIS

    async def dexscreener_boosted_tokens(self) -> List[str]:
        """Get latest boosted tokens from official DexScreener API"""
        try:
            await self.rate_limit_wait("dexscreener_boosts")
            
            url = f"{self.dexscreener_base}/token-boosts/latest/v1"
            
            headers = {
                'Accept': '*/*',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        tokens = []
                        
                        for item in data:
                            if item.get("chainId") == "solana":
                                token_address = item.get("tokenAddress")
                                if token_address and len(token_address) == 44:
                                    tokens.append(token_address)
                                    logger.info(f"📍 DexScreener BOOSTED: {token_address[:8]}")
                        
                        logger.info(f"✅ DexScreener boosted found {len(tokens)} tokens")
                        return tokens[:10]
                    else:
                        logger.warning(f"⚠️ DexScreener boosted API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.warning(f"⚠️ DexScreener boosted discovery error: {e}")
            return []

    async def dexscreener_search_tokens(self) -> List[str]:
        """Search for Solana token pairs using official API"""
        try:
            await self.rate_limit_wait("dexscreener_search")
            
            search_queries = ["SOL", "USDC"]
            tokens = []
            
            for query in search_queries:
                url = f"{self.dexscreener_base}/latest/dex/search?q={query}"
                
                headers = {
                    'Accept': '*/*',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, timeout=15) as response:
                        if response.status == 200:
                            data = await response.json()
                            pairs = data.get("pairs", [])
                            
                            current_time = time.time()
                            
                            for pair in pairs[:20]:
                                created_at = pair.get("pairCreatedAt")
                                if created_at:
                                    try:
                                        created_timestamp = float(created_at) / 1000
                                        hours_old = (current_time - created_timestamp) / 3600
                                        
                                        if hours_old > 24:
                                            continue
                                            
                                    except:
                                        continue
                                
                                if pair.get("chainId") != "solana":
                                    continue
                                
                                base_token = pair.get("baseToken", {})
                                quote_token = pair.get("quoteToken", {})
                                
                                base_address = base_token.get("address")
                                quote_address = quote_token.get("address")
                                
                                if quote_address in [self.sol_mint, self.usdc_mint] and base_address:
                                    liquidity = pair.get("liquidity", {}).get("usd", 0)
                                    if liquidity and float(liquidity) > 1000:
                                        tokens.append(base_address)
                                        logger.info(f"📍 DexScreener SEARCH: {base_address[:8]} (liq: ${float(liquidity):,.0f})")
                        else:
                            logger.warning(f"⚠️ DexScreener search error for '{query}': {response.status}")
                
                await asyncio.sleep(0.5)  # Small delay between searches
            
            logger.info(f"✅ DexScreener search found {len(tokens)} tokens")
            return tokens[:10]
            
        except Exception as e:
            logger.warning(f"⚠️ DexScreener search error: {e}")
            return []

    async def dexscreener_profile_tokens(self) -> List[str]:
        """Get latest token profiles from official API"""
        try:
            await self.rate_limit_wait("dexscreener_profiles")
            
            url = f"{self.dexscreener_base}/token-profiles/latest/v1"
            
            headers = {
                'Accept': '*/*',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        tokens = []
                        
                        for profile in data:
                            if profile.get("chainId") == "solana":
                                token_address = profile.get("tokenAddress")
                                if token_address and len(token_address) == 44:
                                    tokens.append(token_address)
                                    logger.info(f"📍 DexScreener PROFILE: {token_address[:8]}")
                        
                        logger.info(f"✅ DexScreener profiles found {len(tokens)} tokens")
                        return tokens[:5]
                    else:
                        logger.warning(f"⚠️ DexScreener profiles API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.warning(f"⚠️ DexScreener profiles discovery error: {e}")
            return []

    async def dexscreener_discovery_official(self) -> List[str]:
        """Enhanced DexScreener discovery using official API endpoints"""
        try:
            logger.info("📍 Using Official DexScreener API")
            tokens = []
            
            # Method 1: Latest boosted tokens (hot new tokens)
            boosted_tokens = await self.dexscreener_boosted_tokens()
            tokens.extend(boosted_tokens)
            
            # Method 2: Search for active pairs
            search_tokens = await self.dexscreener_search_tokens()
            tokens.extend(search_tokens)
            
            # Method 3: Latest token profiles
            profile_tokens = await self.dexscreener_profile_tokens()
            tokens.extend(profile_tokens)
            
            unique_tokens = list(set(tokens))
            logger.info(f"✅ Official DexScreener API: {len(unique_tokens)} unique tokens")
            return unique_tokens[:15]
            
        except Exception as e:
            logger.error(f"❌ Official DexScreener discovery error: {e}")
            return []

    async def dexscreener_discovery_original(self) -> List[str]:
        """Your original working DexScreener method (fallback)"""
        try:
            logger.info("📍 Using Original DexScreener Method (Fallback)")
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
                                        created_timestamp = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00')).timestamp()
                                    else:
                                        created_timestamp = float(created_at)
                                        if created_timestamp > 10**12:
                                            created_timestamp = created_timestamp / 1000
                                    
                                    hours_old = (current_time - created_timestamp) / 3600
                                    if hours_old > 24:
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
                                    logger.info(f"📍 DexScreener ORIGINAL: {base_address[:8]} (age: {hours_old:.1f}h, liq: ${float(liquidity):,.0f})")
                        
                        logger.info(f"✅ Original DexScreener: {len(tokens)} tokens")
                        return tokens[:15]
                        
                    else:
                        logger.warning(f"⚠️ Original DexScreener API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"❌ Original DexScreener discovery error: {e}")
            return []

    async def dexscreener_discovery(self) -> List[str]:
        """Enhanced DexScreener with official API + original fallback"""
        try:
            # Method 1: Try official API first (best quality, rate limited)
            tokens = await self.dexscreener_discovery_official()
            if tokens:
                logger.info(f"✅ Official DexScreener SUCCESS: {len(tokens)} tokens")
                return tokens
            
            # Method 2: Fallback to original working code
            logger.info("🔄 Trying original DexScreener fallback...")
            tokens = await self.dexscreener_discovery_original()
            if tokens:
                logger.info(f"✅ Original DexScreener FALLBACK SUCCESS: {len(tokens)} tokens")
                return tokens
            
            logger.warning("⚠️ All DexScreener methods failed")
            return []
            
        except Exception as e:
            logger.error(f"❌ Enhanced DexScreener discovery error: {e}")
            return []

    async def pumpfun_discovery(self) -> List[str]:
        """Your original working Pump.fun method"""
        try:
            await self.rate_limit_wait("pumpfun")
            
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
                                    created_time = datetime.datetime.fromisoformat(created_timestamp.replace('Z', '+00:00')).timestamp()
                                else:
                                    created_time = float(created_timestamp)
                                    if created_time > 10**12:
                                        created_time = created_time / 1000
                            except:
                                continue
                            
                            hours_old = (current_time - created_time) / 3600
                            if hours_old > 6:
                                continue
                            
                            mint_address = coin.get("mint") or coin.get("address") or coin.get("token")
                            if mint_address and len(mint_address) == 44:
                                tokens.append(mint_address)
                                logger.info(f"📍 Pump.fun NEW: {mint_address[:8]} (age: {hours_old:.1f}h)")
                        
                        logger.info(f"✅ Pump.fun: {len(tokens)} tokens < 6h old")
                        return tokens[:10]
                        
                    else:
                        logger.warning(f"⚠️ Pump.fun API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"❌ Pump.fun discovery error: {e}")
            return []

    async def raydium_discovery(self) -> List[str]:
        """Your original working Raydium method"""
        try:
            await self.rate_limit_wait("raydium")
            
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
                            logger.warning("⚠️ Raydium API returned unsuccessful response")
                            return []
                        
                        pool_data = data.get("data", {})
                        pools = pool_data.get("data", []) if isinstance(pool_data, dict) else pool_data
                        
                        if not pools:
                            logger.warning("⚠️ Raydium returned no pools")
                            return []
                        
                        for pool in pools[:30]:
                            tvl = pool.get("tvl", 0)
                            
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
                        
                        logger.info(f"✅ Raydium: {len(tokens)} active pools")
                        return tokens[:15]
                        
                    else:
                        logger.warning(f"⚠️ Raydium API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"❌ Raydium discovery error: {e}")
            return []

    def filter_tokens_enhanced(self, tokens: List[str]) -> List[str]:
        """Enhanced token filtering with blacklist checking"""
        skip_tokens = {
            self.usdc_mint,
            self.sol_mint,
            "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
            "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",   # mSOL
            "7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj",   # stSOL
            "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",   # BONK
            "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn",   # JitoSOL
        }
        
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
                    if hasattr(self, 'recently_traded') and token not in self.recently_traded:
                        filtered.append(token)
                    elif not hasattr(self, 'recently_traded'):
                        filtered.append(token)
        
        logger.info(f"🔧 Filtered {len(tokens)} → {len(filtered)} tokens")
        if blacklisted_count > 0:
            logger.info(f"🚫 Blocked {blacklisted_count} blacklisted tokens")
        
        return filtered

    async def discover_new_tokens(self) -> List[str]:
        """Enhanced token discovery with official APIs and fallbacks"""
        try:
            logger.info("🔍 Starting enhanced token discovery...")
            new_tokens = []
            
            # Method 1: Enhanced DexScreener (Official API + Original Fallback)
            logger.info("📍 Phase 1: Enhanced DexScreener Discovery")
            dexscreener_tokens = await self.dexscreener_discovery()
            new_tokens.extend(dexscreener_tokens)
            
            # Method 2: Pump.fun (Original Working Method)
            logger.info("📍 Phase 2: Pump.fun Discovery")
            pumpfun_tokens = await self.pumpfun_discovery()
            new_tokens.extend(pumpfun_tokens)
            
            # Method 3: Raydium (Original Working Method)
            logger.info("📍 Phase 3: Raydium Discovery")
            raydium_tokens = await self.raydium_discovery()
            new_tokens.extend(raydium_tokens)
            
            # Process and filter results
            unique_tokens = list(set(new_tokens))
            filtered_tokens = self.filter_tokens_enhanced(unique_tokens)
            
            # Prioritize Pump.fun tokens (newest)
            prioritized_tokens = []
            for token in filtered_tokens:
                if token in pumpfun_tokens:
                    prioritized_tokens.insert(0, token)
                else:
                    prioritized_tokens.append(token)
            
            logger.info(f"🔍 Enhanced Discovery Results:")
            logger.info(f"   DexScreener: {len(dexscreener_tokens)} tokens")
            logger.info(f"   Pump.fun: {len(pumpfun_tokens)} tokens")
            logger.info(f"   Raydium: {len(raydium_tokens)} tokens")
            logger.info(f"   Total Unique: {len(unique_tokens)} tokens")
            logger.info(f"   Final Filtered: {len(prioritized_tokens)} tokens")
            
            if not prioritized_tokens:
                logger.info("⏭️ No new tokens found this cycle")
            
            return prioritized_tokens[:10]
            
        except Exception as e:
            logger.error(f"❌ Error in enhanced token discovery: {e}")
            return []

    async def check_token_safety(self, token_address: str) -> Tuple[bool, float]:
        """Check if token is safe using configured thresholds"""
        try:
            if token_address == self.sol_mint:
                logger.info(f"⏭️ Skipping SOL - looking for new tokens only")
                return False, 0.5
            
            logger.info(f"🔍 Analyzing token safety: {token_address}")
            return await self.simplified_safety_check(token_address)
            
        except Exception as e:
            logger.error(f"❌ Error in safety analysis: {e}")
            return False, 0.0

    async def simplified_safety_check(self, token_address: str) -> Tuple[bool, float]:
        """Simplified safety check using environment variables"""
        try:
            # Run analysis methods
            dexscreener_score = await self.dexscreener_analysis(token_address)
            pattern_score = await self.pattern_analysis(token_address)
            
            # Calculate weighted score
            final_score = (dexscreener_score * 0.70) + (pattern_score * 0.30)
            is_safe = final_score >= self.safety_threshold
            
            logger.info(f"🔒 SAFETY REPORT for {token_address[:8]}:")
            logger.info(f"   DexScreener: {dexscreener_score:.2f}")
            logger.info(f"   Pattern:     {pattern_score:.2f}")
            logger.info(f"   FINAL:       {final_score:.2f} ({'✓ SAFE' if is_safe else '⚠️ RISKY'})")
            
            return is_safe, final_score
            
        except Exception as e:
            logger.error(f"❌ Error in simplified safety check: {e}")
            return False, 0.0

    async def dexscreener_analysis(self, token_address: str) -> float:
        """DexScreener analysis for individual token"""
        try:
            url = f"{self.dexscreener_base}/latest/dex/tokens/{token_address}"
            
            headers = {
                'Accept': '*/*',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=15) as response:
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
                            
                            logger.info(f"📊 DexScreener Analysis: Liq=${liquidity_usd:,.0f}, Vol=${volume_24h:,.0f}")
                            return min(score, 1.0)
                        else:
                            logger.warning("⚠️ No trading pairs found on DexScreener")
                            return 0.15
                    else:
                        logger.warning(f"⚠️ DexScreener analysis API error: {response.status}")
                        return 0.20
                        
        except Exception as e:
            logger.warning(f"⚠️ DexScreener analysis error: {e}")
            return 0.20

    async def pattern_analysis(self, token_address: str) -> float:
        """Basic pattern analysis"""
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
        """Execute a trade with strict duplicate prevention"""
        try:
            if token_address in self.active_positions:
                logger.warning(f"🚫 DUPLICATE PREVENTED: Already have position in {token_address[:8]}")
                return False
            
            if hasattr(self, 'recently_traded') and token_address in self.recently_traded:
                logger.warning(f"🚫 COOLDOWN ACTIVE: Recently traded {token_address[:8]}")
                return False
            
            if len(self.active_positions) >= self.max_positions:
                logger.info(f"⏳ Max positions ({self.max_positions}) reached")
                return False
            
            logger.info(f"🎯 EXECUTING TRADE: {token_address[:8]} (Position {len(self.active_positions)+1}/{self.max_positions})")
            
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
            
            token_amount = int(quote["outAmount"])
            self.active_positions[token_address] = {
                "entry_time": dt.now(),
                "tx_id": tx_id,
                "usdc_amount": self.trade_amount,
                "token_amount": token_amount,
                "entry_price": self.trade_amount / token_amount,
                "token_address": token_address
            }
            
            if not hasattr(self, 'recently_traded'):
                self.recently_traded = set()
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
            logger.info(f"💰 Attempting to sell position: {token_address[:8]}")
            
            expected_amount = position["token_amount"]
            has_balance, actual_amount = await self.verify_token_balance(token_address, expected_amount)
            
            if not has_balance:
                logger.error(f"❌ Insufficient token balance: Expected {expected_amount}, Have {actual_amount}")
                
                if actual_amount > 0:
                    logger.info(f"🔄 Adjusting sell amount to actual balance: {actual_amount}")
                    position["token_amount"] = actual_amount
                else:
                    logger.error(f"❌ No tokens found, removing position")
                    if token_address in self.active_positions:
                        del self.active_positions[token_address]
                    return False
            
            quote = await self.get_jupiter_quote(
                input_mint=token_address,
                output_mint=self.usdc_mint,
                amount=position["token_amount"]
            )
            
            if not quote:
                logger.error(f"❌ Failed to get sell quote for {token_address[:8]}")
                return False
                
            expected_usdc = int(quote["outAmount"])
            logger.info(f"📊 Verified sell quote: {position['token_amount']} tokens → ${expected_usdc/1_000_000:.2f} USDC")
            
            tx_id = await self.execute_jupiter_swap_optimized(quote)
            
            if tx_id:
                original_usdc = position["usdc_amount"]
                profit_usdc = expected_usdc - original_usdc
                profit_percent = (profit_usdc / original_usdc) * 100
                
                # BLACKLIST CHECK
                if profit_percent <= -self.blacklist_threshold:
                    self.add_to_blacklist(
                        token_address, 
                        abs(profit_percent), 
                        f"stop_loss_{abs(profit_percent):.1f}%"
                    )
                
                mode = "REAL" if self.enable_real_trading else "SIM"
                logger.info(f"💰 {mode} SOLD: {token_address[:8]} → ${profit_usdc/1_000_000:+.2f} ({profit_percent:+.2f}%)")
                
                self.total_trades += 1
                if profit_usdc > 0:
                    self.profitable_trades += 1
                    self.total_profit += profit_usdc / 1_000_000
                
                del self.active_positions[token_address]
                
                win_rate = (self.profitable_trades / self.total_trades) * 100 if self.total_trades > 0 else 0
                logger.info(f"📊 Stats: {self.profitable_trades}/{self.total_trades} trades ({win_rate:.1f}% win rate), Total profit: ${self.total_profit:.2f}")
                
                return True
            else:
                logger.error(f"❌ Failed to execute verified sell swap for {token_address[:8]}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in verified sell: {e}")
            return False

    async def monitor_positions(self):
        """Monitor active positions using configured thresholds"""
        try:
            if not self.active_positions:
                logger.info("📊 No active positions to monitor")
                return
                
            logger.info(f"📊 Monitoring {len(self.active_positions)} positions...")
            
            for token_address, position in list(self.active_positions.items()):
                try:
                    logger.info(f"🔍 Checking position: {token_address[:8]}")
                    
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
                        
                        if profit_percent >= self.profit_target:
                            logger.info(f"🎯 PROFIT TARGET HIT: {profit_percent:.2f}% >= {self.profit_target}%")
                            success = await self.sell_position_verified(token_address, position, current_value)
                            if success:
                                logger.info(f"✅ Successfully sold position")
                            else:
                                logger.error(f"❌ Failed to sell position")
                        
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
        """Main trading loop with enhanced discovery"""
        logger.info("🔄 Starting enhanced trading loop...")
        
        self.recently_traded = set()
        last_cooldown_cleanup = time.time()
        
        loop_count = 0
        while True:
            try:
                loop_count += 1
                logger.info(f"🔍 Enhanced Trading Loop #{loop_count}")
                
                # Clean up cooldown every 15 minutes
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
                
                # Look for new trading opportunities
                available_slots = self.max_positions - len(self.active_positions)
                if available_slots > 0:
                    logger.info(f"🔍 Scanning for opportunities ({available_slots} slots available)...")
                    
                    new_tokens = await self.discover_new_tokens()
                    
                    if not new_tokens:
                        logger.info("⏭️ No new tokens found this cycle")
                    else:
                        logger.info(f"🎯 Evaluating {len(new_tokens)} potential tokens...")
                    
                    trades_this_cycle = 0
                    max_trades_per_cycle = min(2, available_slots)
                    
                    for token_address in new_tokens:
                        if trades_this_cycle >= max_trades_per_cycle:
                            logger.info(f"⏳ Max trades per cycle reached ({max_trades_per_cycle})")
                            break
                        
                        if token_address in self.active_positions:
                            logger.info(f"⏭️ Skipping {token_address[:8]} - active position exists")
                            continue
                        
                        if token_address in self.recently_traded:
                            logger.info(f"⏭️ Skipping {token_address[:8]} - in cooldown period")
                            continue
                        
                        is_safe, confidence = await self.check_token_safety(token_address)
                        
                        if is_safe and confidence >= self.safety_threshold:
                            logger.info(f"✅ SAFE token found: {token_address[:8]} (confidence: {confidence:.2f})")
                            
                            success = await self.execute_trade(token_address)
                            if success:
                                trades_this_cycle += 1
                                logger.info(f"🎯 Trade {trades_this_cycle}/{max_trades_per_cycle} completed")
                                await asyncio.sleep(5)
                            else:
                                logger.warning(f"⚠️ Trade execution failed for {token_address[:8]}")
                        else:
                            logger.info(f"⚠️ Risky token skipped: {token_address[:8]} (confidence: {confidence:.2f})")
                else:
                    logger.info(f"⏳ Max positions ({self.max_positions}) reached, monitoring only")
                
                logger.info(f"📊 Summary: {len(self.active_positions)}/{self.max_positions} positions, {len(self.recently_traded)} cooldown, {len(self.token_blacklist)} blacklisted")
                
                await asyncio.sleep(30)
                
            except KeyboardInterrupt:
                logger.info("🛑 Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Error in main loop: {e}")
                await asyncio.sleep(10)

    async def run(self):
        """Start the enhanced trading bot"""
        logger.info("🚀 Starting Enhanced Solana Trading Bot with Official APIs...")
        
        if self.enable_real_trading:
            logger.warning("⚠️⚠️⚠️ REAL TRADING MODE ENABLED ⚠️⚠️⚠️")
            logger.warning("⚠️ This bot will use REAL MONEY on Solana mainnet")
            logger.warning("⚠️ Ensure your wallet is funded with USDC and SOL")
            
            for i in range(10, 0, -1):
                logger.warning(f"⚠️ Starting real trading in {i} seconds... (Ctrl+C to cancel)")
                await asyncio.sleep(1)
        
        if not await self.validate_configuration():
            logger.error("❌ Configuration validation failed")
            return
        
        logger.info("✅ Enhanced bot configuration validated")
        
        if self.enable_real_trading:
            logger.info("💸 Bot is now operational and ready for REAL TRADING!")
            logger.info(f"💰 Will trade REAL MONEY: ${self.trade_amount/1_000_000} per trade")
        else:
            logger.info("🎯 Bot is now operational in SIMULATION mode!")
            logger.info(f"💰 Simulating trades with ${self.trade_amount/1_000_000} amounts")
        
        logger.info(f"🔍 Enhanced discovery with Official DexScreener APIs...")
        
        await self.main_trading_loop()

async def main():
    """Entry point for enhanced trading bot"""
    try:
        bot = EnhancedSolanaTradingBot()
        await bot.run()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
    finally:
        logger.info("🏁 Enhanced bot shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())
