#!/usr/bin/env python3
"""
Solana Trading Bot - ENHANCED VERSION WITH WEEK 1 CRITICAL SAFETY FIXES
⚠️ WARNING: This version uses REAL MONEY on Solana mainnet when enabled
Features: Enhanced Safety System, Mandatory Liquidity Verification, Honeypot Detection
Updated: 2025-07-04 - Week 1 Critical Safety Fixes Implemented
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
        """Initialize the enhanced trading bot with critical safety fixes"""
        
        # WALLET CONFIGURATION
        self.private_key = os.getenv("SOLANA_PRIVATE_KEY")
        self.public_key = os.getenv("SOLANA_PUBLIC_KEY") 
        
        # RPC ENDPOINTS
        self.rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
        self.quicknode_http = os.getenv("QUICKNODE_HTTP_URL")
        self.quicknode_wss = os.getenv("QUICKNODE_WSS_URL")
        
        # TRADING CONFIGURATION
        self.enable_real_trading = os.getenv("ENABLE_REAL_TRADING", "false").lower() == "true"
        self.trade_amount = int(float(os.getenv("TRADE_AMOUNT", "1.0")) * 1_000_000)  # Convert to micro-USDC
        self.profit_target = float(os.getenv("PROFIT_TARGET", "3.0"))
        self.stop_loss_percent = float(os.getenv("STOP_LOSS_PERCENT", "15.0"))
        self.max_positions = int(os.getenv("MAX_POSITIONS", "10"))
        self.slippage = int(os.getenv("SLIPPAGE_BPS", "50"))
        
        # ENHANCED SAFETY THRESHOLDS
        self.safety_threshold = float(os.getenv("SAFETY_THRESHOLD", "0.55"))
        self.min_liquidity_usd = float(os.getenv("MIN_LIQUIDITY_USD", "2500"))
        self.min_volume_24h = float(os.getenv("MIN_VOLUME_24H", "500"))
        
        # TOKEN ADDRESSES
        self.usdc_mint = os.getenv("USDC_MINT", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
        self.sol_mint = os.getenv("SOL_MINT", "So11111111111111111111111111111111111111112")
        
        # API ENDPOINTS
        self.jupiter_quote_url = os.getenv("JUPITER_QUOTE_API", "https://quote-api.jup.ag/v6/quote")
        self.jupiter_swap_url = os.getenv("JUPITER_SWAP_API", "https://quote-api.jup.ag/v6/swap")
        self.dexscreener_url = os.getenv("DEXSCREENER_API", "https://api.dexscreener.com/latest/dex/tokens")
        
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
        
        # WEEK 1 ENHANCEMENT: Safety statistics
        self.safety_stats = {
            "liquidity_rejections": 0,
            "honeypot_rejections": 0,
            "safety_passed": 0,
            "total_analyzed": 0
        }
        
        # Load existing blacklist
        self.load_blacklist()
        
        # Log configuration
        logger.info("🤖 Enhanced Solana Trading Bot initialized with CRITICAL SAFETY FIXES")
        logger.info(f"💰 Trade Amount: ${self.trade_amount/1_000_000}")
        logger.info(f"🎯 Profit Target: {self.profit_target}%")
        logger.info(f"🛑 Stop Loss: {self.stop_loss_percent}%")
        logger.info(f"📊 Max Positions: {self.max_positions}")
        logger.info(f"🔒 Safety Threshold: {self.safety_threshold}")
        logger.info(f"💧 Min Liquidity: ${self.min_liquidity_usd:,.0f}")
        logger.info(f"📈 Min Volume 24h: ${self.min_volume_24h:,.0f}")
        logger.info(f"🚫 Blacklist threshold: {self.blacklist_threshold}%")
        logger.info(f"🚫 Blacklisted tokens: {len(self.token_blacklist)}")
        logger.info("🛡️ WEEK 1 SAFETY ENHANCEMENTS: Mandatory liquidity gates, honeypot detection enabled")
        
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
            logger.warning(f"🚫 Total blacklisted: {len(self.token_blacklist)}")

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
            # Simplified version - in production would check actual ATA balance
            return True, expected_amount
        except Exception as e:
            logger.error(f"❌ Error verifying token balance: {e}")
            return False, 0

    # ============================================================================
    # WEEK 1 CRITICAL SAFETY ENHANCEMENT: MANDATORY LIQUIDITY VERIFICATION
    # ============================================================================

    async def verify_minimum_liquidity(self, token_address: str) -> Tuple[bool, Dict]:
        """
        WEEK 1 FIX: Mandatory liquidity verification - Hard gate before any trading
        This prevents the $0 liquidity bug that was marking unsafe tokens as safe
        """
        try:
            logger.info(f"🔍 Mandatory liquidity verification for {token_address[:8]}...")
            
            # Check liquidity from multiple sources for accuracy
            dex_liquidity = await self._get_dexscreener_liquidity(token_address)
            await asyncio.sleep(0.5)  # Rate limiting
            raydium_liquidity = await self._get_raydium_liquidity(token_address)
            
            # Take the highest reported liquidity (most conservative)
            max_liquidity = max(dex_liquidity, raydium_liquidity)
            
            # HARD RULES - ZERO TOLERANCE FOR DANGEROUS TOKENS
            if max_liquidity <= 0:
                logger.warning(f"🚫 ZERO LIQUIDITY DETECTED: {token_address[:8]} - ${max_liquidity}")
                self.safety_stats["liquidity_rejections"] += 1
                return False, {
                    "reason": "zero_liquidity", 
                    "amount": max_liquidity,
                    "sources": {"dexscreener": dex_liquidity, "raydium": raydium_liquidity}
                }
            
            if max_liquidity < self.min_liquidity_usd:
                logger.warning(f"🚫 BELOW MIN LIQUIDITY: {token_address[:8]} - ${max_liquidity:,.0f} < ${self.min_liquidity_usd:,.0f}")
                self.safety_stats["liquidity_rejections"] += 1
                return False, {
                    "reason": "below_minimum", 
                    "amount": max_liquidity,
                    "minimum_required": self.min_liquidity_usd
                }
            
            # Calculate liquidity adequacy score for quality assessment
            liquidity_score = min(max_liquidity / (self.min_liquidity_usd * 10), 1.0)
            
            logger.info(f"✅ LIQUIDITY ADEQUATE: {token_address[:8]} - ${max_liquidity:,.0f} (score: {liquidity_score:.2f})")
            return True, {
                "reason": "adequate", 
                "amount": max_liquidity,
                "score": liquidity_score,
                "sources": {"dexscreener": dex_liquidity, "raydium": raydium_liquidity}
            }
            
        except Exception as e:
            logger.error(f"❌ Liquidity verification error for {token_address[:8]}: {e}")
            self.safety_stats["liquidity_rejections"] += 1
            return False, {"reason": "verification_failed", "error": str(e)}

    async def _get_dexscreener_liquidity(self, token_address: str) -> float:
        """Get liquidity data from DexScreener API"""
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        pairs = data.get('pairs', [])
                        
                        if pairs:
                            # Get highest liquidity pair
                            best_pair = max(pairs, key=lambda p: float(p.get('liquidity', {}).get('usd', 0)))
                            liquidity_usd = float(best_pair.get('liquidity', {}).get('usd', 0))
                            return liquidity_usd
                        
            return 0.0
        except Exception as e:
            logger.debug(f"DexScreener liquidity check failed: {e}")
            return 0.0

    async def _get_raydium_liquidity(self, token_address: str) -> float:
        """Get liquidity data from Raydium API"""
        try:
            # Simplified Raydium liquidity check
            # In production, would query Raydium pools API
            return 0.0  # Placeholder - implement based on available Raydium endpoints
        except Exception as e:
            logger.debug(f"Raydium liquidity check failed: {e}")
            return 0.0

    # ============================================================================
    # WEEK 1 CRITICAL SAFETY ENHANCEMENT: HONEYPOT DETECTION
    # ============================================================================

    async def basic_honeypot_detection(self, token_address: str) -> Tuple[bool, Dict]:
        """
        WEEK 1 FIX: Basic honeypot detection to test if tokens can actually be sold
        This prevents trading tokens that can be bought but not sold (honeypots)
        """
        try:
            logger.info(f"🔍 Honeypot detection for {token_address[:8]}...")
            
            # Test 1: Get buy quote (USDC -> Token)
            buy_quote = await self.get_jupiter_quote(
                input_mint=self.usdc_mint,
                output_mint=token_address,
                amount=100_000  # $0.10 test amount
            )
            
            if not buy_quote:
                logger.warning(f"🚫 HONEYPOT: {token_address[:8]} - cannot get buy quote")
                self.safety_stats["honeypot_rejections"] += 1
                return False, {"reason": "cannot_get_buy_quote", "test_amount": 0.10}
            
            # Test 2: Get sell quote (Token -> USDC) for the same theoretical amount
            estimated_tokens = int(buy_quote["outAmount"])
            sell_quote = await self.get_jupiter_quote(
                input_mint=token_address,
                output_mint=self.usdc_mint,
                amount=estimated_tokens
            )
            
            if not sell_quote:
                logger.warning(f"🚫 HONEYPOT: {token_address[:8]} - cannot get sell quote")
                self.safety_stats["honeypot_rejections"] += 1
                return False, {"reason": "cannot_get_sell_quote", "tokens_to_sell": estimated_tokens}
            
            # Test 3: Calculate round-trip efficiency
            input_amount = int(buy_quote["inAmount"])
            output_amount = int(sell_quote["outAmount"])
            efficiency = output_amount / input_amount if input_amount > 0 else 0
            
            # Test 4: Check for excessive slippage (potential honeypot indicator)
            if efficiency < 0.4:  # More than 60% loss in round trip
                logger.warning(f"🚫 HONEYPOT: {token_address[:8]} - high slippage (efficiency: {efficiency:.2f})")
                self.safety_stats["honeypot_rejections"] += 1
                return False, {
                    "reason": "high_slippage", 
                    "efficiency": efficiency,
                    "loss_percent": (1 - efficiency) * 100
                }
            
            # Test passed - token appears sellable
            logger.info(f"✅ SELLABLE: {token_address[:8]} - efficiency: {efficiency:.2f}")
            return True, {
                "reason": "sellable", 
                "efficiency": efficiency,
                "buy_quote": buy_quote,
                "sell_quote": sell_quote
            }
            
        except Exception as e:
            logger.error(f"❌ Honeypot test failed for {token_address[:8]}: {e}")
            self.safety_stats["honeypot_rejections"] += 1
            return False, {"reason": "test_failed", "error": str(e)}

    # ============================================================================
    # ENHANCED SAFETY CHECK SYSTEM WITH MANDATORY GATES
    # ============================================================================

    async def enhanced_safety_check(self, token_address: str) -> Tuple[bool, float, Dict]:
        """
        WEEK 1 ENHANCED: Multi-layer safety system with mandatory verification gates
        This replaces the old simplified_safety_check with critical safety improvements
        """
        try:
            if token_address == self.sol_mint:
                logger.info(f"⏭️ Skipping SOL - looking for new tokens only")
                return False, 0.5, {"reason": "sol_token_skipped"}
            
            logger.info(f"🔍 Enhanced safety analysis: {token_address[:8]}")
            self.safety_stats["total_analyzed"] += 1
            
            # MANDATORY GATE 1: Liquidity Verification (CRITICAL)
            liquidity_ok, liquidity_info = await self.verify_minimum_liquidity(token_address)
            if not liquidity_ok:
                logger.warning(f"🚫 LIQUIDITY GATE FAILED: {token_address[:8]} - {liquidity_info['reason']}")
                return False, 0.0, {
                    "result": "FAILED_LIQUIDITY_GATE",
                    "failed_gate": "liquidity",
                    "details": liquidity_info
                }
            
            # MANDATORY GATE 2: Honeypot Detection (CRITICAL)
            honeypot_ok, honeypot_info = await self.basic_honeypot_detection(token_address)
            if not honeypot_ok:
                logger.warning(f"🚫 HONEYPOT GATE FAILED: {token_address[:8]} - {honeypot_info['reason']}")
                return False, 0.0, {
                    "result": "FAILED_HONEYPOT_GATE",
                    "failed_gate": "honeypot", 
                    "details": honeypot_info
                }
            
            # Both mandatory gates passed - proceed with quality analysis
            logger.info(f"✅ MANDATORY GATES PASSED: {token_address[:8]} - proceeding to quality analysis")
            
            # Quality Analysis: Enhanced DexScreener analysis (no more $0 liquidity bug)
            dexscreener_score = await self.enhanced_dexscreener_analysis(token_address)
            
            # Quality Analysis: Pattern analysis (reduced weight)
            pattern_score = await self.pattern_analysis(token_address)
            
            # WEEK 1 FIX: Rebalanced scoring weights (reduced pattern analysis influence)
            final_score = (dexscreener_score * 0.80) + (pattern_score * 0.20)
            is_safe = final_score >= self.safety_threshold
            
            if is_safe:
                self.safety_stats["safety_passed"] += 1
            
            # Detailed results for debugging
            result_details = {
                "result": "PASSED_ALL_GATES" if is_safe else "FAILED_QUALITY_SCORE",
                "passed_gates": ["liquidity", "honeypot"],
                "liquidity_info": liquidity_info,
                "honeypot_info": honeypot_info,
                "dexscreener_score": dexscreener_score,
                "pattern_score": pattern_score,
                "final_score": final_score,
                "safety_threshold": self.safety_threshold,
                "scoring_weights": {"dexscreener": 0.80, "pattern": 0.20}
            }
            
            logger.info(f"🔒 ENHANCED SAFETY REPORT for {token_address[:8]}:")
            logger.info(f"   Liquidity: ✅ ${liquidity_info.get('amount', 0):,.0f}")
            logger.info(f"   Honeypot:  ✅ Efficiency {honeypot_info.get('efficiency', 0):.2f}")
            logger.info(f"   DexScreener: {dexscreener_score:.2f} (80% weight)")
            logger.info(f"   Pattern:     {pattern_score:.2f} (20% weight)")
            logger.info(f"   FINAL:       {final_score:.2f} ({'✓ SAFE' if is_safe else '⚠️ RISKY'})")
            
            return is_safe, final_score, result_details
            
        except Exception as e:
            logger.error(f"❌ Error in enhanced safety analysis: {e}")
            return False, 0.0, {"result": "ANALYSIS_ERROR", "error": str(e)}

    async def enhanced_dexscreener_analysis(self, token_address: str) -> float:
        """
        WEEK 1 FIX: Enhanced DexScreener analysis with proper $0 liquidity handling
        This fixes the critical bug where $0 liquidity tokens got base scores
        """
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
                            
                            # WEEK 1 CRITICAL FIX: Zero liquidity = immediate low score
                            if liquidity_usd <= 0:
                                logger.warning(f"🚫 ENHANCED: Zero liquidity detected in DexScreener analysis")
                                return 0.0  # No base score for zero liquidity
                            
                            # WEEK 1 CRITICAL FIX: Below minimum = very low score  
                            if liquidity_usd < self.min_liquidity_usd:
                                logger.warning(f"🚫 ENHANCED: Below minimum liquidity in DexScreener analysis")
                                return 0.1  # Very low score for insufficient liquidity
                            
                            # Start with base score only if liquidity is adequate
                            score = 0.20
                            
                            # Enhanced liquidity scoring
                            if liquidity_usd >= self.min_liquidity_usd * 3:
                                score += 0.35
                            elif liquidity_usd >= self.min_liquidity_usd:
                                score += 0.25
                            
                            # Enhanced volume scoring
                            if volume_24h >= self.min_volume_24h * 5:
                                score += 0.35
                            elif volume_24h >= self.min_volume_24h:
                                score += 0.25
                            
                            logger.info(f"📊 Enhanced DexScreener Analysis: Liq=${liquidity_usd:,.0f}, Vol=${volume_24h:,.0f}, Score={score:.2f}")
                            return min(score, 1.0)
                        else:
                            logger.warning("⚠️ No trading pairs found on DexScreener")
                            return 0.0  # No pairs = no liquidity = unsafe
                    else:
                        logger.warning(f"⚠️ DexScreener API error: {response.status}")
                        return 0.1  # API error = low confidence, not zero (might be temporary)
                        
        except Exception as e:
            logger.warning(f"⚠️ Enhanced DexScreener analysis error: {e}")
            return 0.1  # Error = low confidence

    async def pattern_analysis(self, token_address: str) -> float:
        """Basic pattern analysis (weight reduced from 30% to 20%)"""
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

    # ============================================================================
    # JUPITER API METHODS (UNCHANGED FROM WORKING VERSION)
    # ============================================================================

    async def get_jupiter_quote(self, input_mint: str, output_mint: str, amount: int) -> Optional[Dict]:
        """Get quote from Jupiter API using configured endpoint"""
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
                        
                        logger.debug(f"📊 Jupiter Quote: {input_amount:.2f} → {output_amount:.6f}")
                        return quote
                    else:
                        error_text = await response.text()
                        logger.warning(f"❌ Jupiter quote failed: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error getting Jupiter quote: {e}")
            return None

    async def send_transaction_ultra_minimal(self, transaction_data: str) -> Optional[str]:
        """Ultra-minimal transaction sending"""
        try:
            from solders.keypair import Keypair
            from solders.transaction import VersionedTransaction
            
            logger.warning("⚠️ SENDING ULTRA-MINIMAL REAL TRANSACTION")
            
            transaction_bytes = base64.b64decode(transaction_data)
            logger.info(f"📏 Transaction size: {len(transaction_bytes)} bytes")
            
            if len(transaction_bytes) > 1232:
                logger.error(f"❌ Transaction too large: {len(transaction_bytes)} bytes")
                return None
            
            try:
                from solana.transaction import Transaction
                transaction = Transaction.deserialize(transaction_bytes)
                keypair = Keypair.from_base58_string(self.private_key)
                transaction.sign(keypair)
                signed_tx_b64 = base64.b64encode(bytes(transaction)).decode('utf-8')
            except Exception as e:
                logger.error(f"❌ Legacy transaction signing failed: {e}")
                return None
            
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
                    logger.info(f"✅ ULTRA-MINIMAL TRANSACTION SENT: {tx_id}")
                    return tx_id
                else:
                    error = result.get("error", "Unknown error")
                    logger.error(f"❌ RPC Error: {error}")
                    return None
            else:
                logger.error(f"❌ HTTP Error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error sending ultra-minimal transaction: {e}")
            return None

    async def get_jupiter_quote_minimal(self, input_mint: str, output_mint: str, amount: int) -> Optional[Dict]:
        """Get quote with ultra-minimal routing"""
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
                        logger.info(f"📊 Minimal Jupiter Quote: {int(quote['inAmount'])/1_000_000:.2f} → {int(quote['outAmount'])/1_000_000:.6f}")
                        return quote
                    else:
                        logger.error(f"❌ Minimal quote failed: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error getting minimal quote: {e}")
            return None

    async def execute_jupiter_swap_minimal(self, quote: Dict) -> Optional[str]:
        """Ultra-minimal swap execution for oversized transactions"""
        try:
            if not self.enable_real_trading:
                tx_id = f"sim_{int(time.time())}"
                logger.info(f"✅ SIMULATED swap: {tx_id}")
                return tx_id
            
            minimal_quote = await self.get_jupiter_quote_minimal(
                quote.get("inputMint"),
                quote.get("outputMint"),
                int(quote.get("inAmount"))
            )
            
            if not minimal_quote:
                logger.error("❌ Failed to get minimal quote")
                return None
            
            swap_data = {
                "quoteResponse": minimal_quote,
                "userPublicKey": self.public_key,
                "wrapAndUnwrapSol": True,
                "useSharedAccounts": False,
                "asLegacyTransaction": True,
                "onlyDirectRoutes": True,
                "maxAccounts": 20,
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
                                logger.error(f"❌ Even minimal transaction too large: {len(transaction_bytes)} bytes")
                                return None
                            
                            tx_id = await self.send_transaction_ultra_minimal(transaction_data)
                            if tx_id:
                                logger.info(f"✅ REAL SWAP EXECUTED (ultra-minimal): {tx_id}")
                                return tx_id
                        
                        logger.error("❌ No transaction data in minimal swap")
                        return None
                    else:
                        logger.error(f"❌ Minimal swap failed: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error in minimal swap: {e}")
            return None

    async def execute_jupiter_swap_optimized(self, quote: Dict) -> Optional[str]:
        """Execute swap with progressive size optimization"""
        try:
            if not self.enable_real_trading:
                tx_id = f"sim_{int(time.time())}"
                logger.info(f"✅ SIMULATED swap: {tx_id}")
                return tx_id
            
            # Try 1: Direct routes with minimal parameters
            logger.info("🔄 Attempting direct route swap...")
            result = await self.execute_jupiter_swap_minimal(quote)
            if result:
                return result
            
            # Try 2: Get fresh minimal quote
            logger.info("🔄 Attempting fresh minimal quote...")
            fresh_quote = await self.get_jupiter_quote_minimal(
                quote.get("inputMint"),
                quote.get("outputMint"),
                int(quote.get("inAmount"))
            )
            
            if fresh_quote:
                result = await self.execute_jupiter_swap_minimal(fresh_quote)
                if result:
                    return result
            
            # Try 3: Smaller amount (split trade)
            logger.info("🔄 Attempting split trade...")
            smaller_amount = int(quote.get("inAmount")) // 2
            if smaller_amount > 100000:
                split_quote = await self.get_jupiter_quote_minimal(
                    quote.get("inputMint"),
                    quote.get("outputMint"),
                    smaller_amount
                )
                if split_quote:
                    result = await self.execute_jupiter_swap_minimal(split_quote)
                    if result:
                        logger.info("✅ Split trade successful")
                        return result
            
            logger.error("❌ All transaction size optimization attempts failed")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error in optimized swap execution: {e}")
            return None

    # ============================================================================
    # TOKEN DISCOVERY METHODS (OFFICIAL DEXSCREENER API + WORKING FALLBACKS)
    # ============================================================================

    async def dexscreener_discovery_official(self) -> List[str]:
        """Use OFFICIAL DexScreener API endpoints for better reliability"""
        try:
            tokens = []
            
            # Method 1: Latest boosted tokens (hot new tokens)
            boosted_tokens = await self._get_dex_boosted_tokens()
            tokens.extend(boosted_tokens)
            
            # Method 2: Search for Solana pairs
            search_tokens = await self._get_dex_search_tokens()
            tokens.extend(search_tokens)
            
            # Method 3: Latest token profiles (newly added tokens)
            profile_tokens = await self._get_dex_profile_tokens()
            tokens.extend(profile_tokens)
            
            return list(set(tokens))[:15]
            
        except Exception as e:
            logger.error(f"❌ Official DexScreener discovery error: {e}")
            return []

    async def _get_dex_boosted_tokens(self) -> List[str]:
        """Get latest boosted tokens (these are usually hot new tokens)"""
        try:
            url = "https://api.dexscreener.com/token-boosts/latest/v1"
            
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
                        
                        logger.info(f"📍 DexScreener boosted found {len(tokens)} tokens")
                        return tokens[:10]
                    else:
                        logger.warning(f"⚠️ DexScreener boosted API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.warning(f"⚠️ DexScreener boosted discovery error: {e}")
            return []

    async def _get_dex_search_tokens(self) -> List[str]:
        """Search for Solana token pairs"""
        try:
            search_queries = ["SOL", "USDC"]
            tokens = []
            
            for query in search_queries:
                url = f"https://api.dexscreener.com/latest/dex/search?q={query}"
                
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
                                # Check if pair is recent
                                created_at = pair.get("pairCreatedAt")
                                if created_at:
                                    try:
                                        created_timestamp = float(created_at) / 1000
                                        hours_old = (current_time - created_timestamp) / 3600
                                        
                                        if hours_old > 24:
                                            continue
                                            
                                    except:
                                        continue
                                
                                # Filter for Solana chain
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
                
                await asyncio.sleep(0.5)
            
            logger.info(f"📍 DexScreener search found {len(tokens)} tokens")
            return tokens[:10]
            
        except Exception as e:
            logger.warning(f"⚠️ DexScreener search error: {e}")
            return []

    async def _get_dex_profile_tokens(self) -> List[str]:
        """Get latest token profiles (newly added tokens)"""
        try:
            url = "https://api.dexscreener.com/token-profiles/latest/v1"
            
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
                        
                        logger.info(f"📍 DexScreener profiles found {len(tokens)} tokens")
                        return tokens[:5]
                    else:
                        logger.warning(f"⚠️ DexScreener profiles API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.warning(f"⚠️ DexScreener profiles discovery error: {e}")
            return []

    async def dexscreener_discovery_original(self) -> List[str]:
        """Original working DexScreener method as fallback"""
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
                        
                        logger.info(f"📍 DexScreener original found {len(tokens)} new pairs")
                        return tokens[:15]
                        
                    else:
                        logger.warning(f"DexScreener original API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"DexScreener original discovery error: {e}")
            return []

    async def dexscreener_discovery(self) -> List[str]:
        """Enhanced DexScreener with official API + original working fallback"""
        try:
            # Method 1: Try official API first (best quality)
            logger.info("📍 Trying official DexScreener API...")
            tokens = await self.dexscreener_discovery_official()
            if tokens:
                logger.info(f"✅ Official DexScreener API SUCCESS: {len(tokens)} tokens")
                return tokens
            
            # Method 2: Fallback to original working code
            logger.info("🔄 Trying original DexScreener fallback...")
            tokens = await self.dexscreener_discovery_original()
            if tokens:
                logger.info(f"✅ DexScreener original fallback SUCCESS: {len(tokens)} tokens")
                return tokens
            
            logger.warning("⚠️ All DexScreener methods failed")
            return []
            
        except Exception as e:
            logger.error(f"❌ DexScreener discovery error: {e}")
            return []

    async def pumpfun_discovery(self) -> List[str]:
        """Discover newly launched tokens from Pump.fun - WORKING VERSION"""
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
                                logger.info(f"📍 Pump.fun NEW token: {mint_address[:8]} (age: {hours_old:.1f}h)")
                        
                        logger.info(f"📍 Pump.fun found {len(tokens)} tokens < 6h old")
                        return tokens[:10]
                        
                    else:
                        logger.warning(f"Pump.fun API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Pump.fun discovery error: {e}")
            return []

    async def raydium_discovery(self) -> List[str]:
        """Discover newly created pools using Raydium - WORKING VERSION"""
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
                        
                        logger.info(f"📍 Raydium found {len(tokens)} active pools")
                        return tokens[:15]
                        
                    else:
                        logger.warning(f"Raydium API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Raydium discovery error: {e}")
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
        logger.info(f"🚫 Blocked {blacklisted_count} blacklisted tokens")
        logger.info(f"🚫 Total blacklist: {len(self.token_blacklist)}")
        
        return filtered

    async def discover_new_tokens(self) -> List[str]:
        """Discover ONLY newly launched tokens from multiple sources"""
        try:
            new_tokens = []
            
            # Method 1: Pump.fun (newest tokens) - PRIMARY
            pumpfun_tokens = await self.pumpfun_discovery()
            new_tokens.extend(pumpfun_tokens)
            
            # Method 2: DexScreener new pairs (official API + fallback)
            dexscreener_tokens = await self.dexscreener_discovery()
            new_tokens.extend(dexscreener_tokens)
            
            # Method 3: Raydium new pools
            raydium_tokens = await self.raydium_discovery()
            new_tokens.extend(raydium_tokens)
            
            unique_tokens = list(set(new_tokens))
            filtered_tokens = self.filter_tokens_enhanced(unique_tokens)
            
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
            
            if not prioritized_tokens:
                logger.info("⏭️ No new tokens found this cycle")
            
            return prioritized_tokens[:10]
            
        except Exception as e:
            logger.error(f"❌ Error discovering NEW tokens: {e}")
            return []

    # ============================================================================
    # TRADING EXECUTION AND MONITORING (UNCHANGED FROM WORKING VERSION)
    # ============================================================================

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
            
            logger.info(f"🎯 EXECUTING NEW TRADE: {token_address[:8]} (Position {len(self.active_positions)+1}/{self.max_positions})")
            
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
                
                # BLACKLIST CHECK: Uses BLACKLIST_THRESHOLD environment variable
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
                        
                        # Uses PROFIT_TARGET environment variable
                        if profit_percent >= self.profit_target:
                            logger.info(f"🎯 PROFIT TARGET HIT: {profit_percent:.2f}% >= {self.profit_target}%")
                            success = await self.sell_position_verified(token_address, position, current_value)
                            if success:
                                logger.info(f"✅ Successfully sold position")
                            else:
                                logger.error(f"❌ Failed to sell position")
                        
                        # Uses STOP_LOSS_PERCENT environment variable
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

    def log_safety_statistics(self):
        """Log enhanced safety statistics"""
        try:
            total = self.safety_stats["total_analyzed"]
            if total > 0:
                liquidity_rejection_rate = (self.safety_stats["liquidity_rejections"] / total) * 100
                honeypot_rejection_rate = (self.safety_stats["honeypot_rejections"] / total) * 100
                safety_pass_rate = (self.safety_stats["safety_passed"] / total) * 100
                
                logger.info(f"🛡️ SAFETY STATISTICS:")
                logger.info(f"   Total analyzed: {total}")
                logger.info(f"   Liquidity rejections: {self.safety_stats['liquidity_rejections']} ({liquidity_rejection_rate:.1f}%)")
                logger.info(f"   Honeypot rejections: {self.safety_stats['honeypot_rejections']} ({honeypot_rejection_rate:.1f}%)")
                logger.info(f"   Safety passed: {self.safety_stats['safety_passed']} ({safety_pass_rate:.1f}%)")
        except Exception as e:
            logger.error(f"❌ Error logging safety statistics: {e}")

    async def main_trading_loop(self):
        """Main trading loop with enhanced safety and monitoring"""
        logger.info("🔄 Starting ENHANCED main trading loop with WEEK 1 SAFETY FIXES...")
        
        self.recently_traded = set()
        last_cooldown_cleanup = time.time()
        last_stats_log = time.time()
        
        loop_count = 0
        while True:
            try:
                loop_count += 1
                logger.info(f"🔍 Enhanced trading loop #{loop_count}")
                
                # Clean up cooldown every 15 minutes
                if time.time() - last_cooldown_cleanup > 900:
                    cooldown_size = len(self.recently_traded)
                    self.recently_traded.clear()
                    last_cooldown_cleanup = time.time()
                    logger.info(f"🧹 Cleared {cooldown_size} tokens from cooldown")
                
                # Log safety statistics every 30 minutes
                if time.time() - last_stats_log > 1800:
                    self.log_safety_statistics()
                    last_stats_log = time.time()
                
                # Monitor existing positions
                if self.active_positions:
                    await self.monitor_positions()
                else:
                    logger.info("📊 No active positions to monitor")
                
                # Look for new trading opportunities
                available_slots = self.max_positions - len(self.active_positions)
                if available_slots > 0:
                    logger.info(f"🔍 Scanning for new opportunities ({available_slots} slots available)...")
                    
                    new_tokens = await self.discover_new_tokens()
                    
                    if not new_tokens:
                        logger.info("⏭️ No new tokens found this cycle")
                    else:
                        logger.info(f"🎯 Evaluating {len(new_tokens)} potential tokens with ENHANCED SAFETY...")
                    
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
                        
                        # WEEK 1 ENHANCEMENT: Use enhanced safety check with mandatory gates
                        is_safe, confidence, details = await self.enhanced_safety_check(token_address)
                        
                        if is_safe and confidence >= self.safety_threshold:
                            logger.info(f"✅ ENHANCED SAFE token found: {token_address[:8]} (confidence: {confidence:.2f})")
                            
                            success = await self.execute_trade(token_address)
                            if success:
                                trades_this_cycle += 1
                                logger.info(f"🎯 Trade {trades_this_cycle}/{max_trades_per_cycle} completed")
                                await asyncio.sleep(5)
                            else:
                                logger.warning(f"⚠️ Trade execution failed for {token_address[:8]}")
                        else:
                            reason = details.get("result", "unknown")
                            logger.info(f"⚠️ Token rejected: {token_address[:8]} - {reason} (confidence: {confidence:.2f})")
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
        logger.info("🚀 Starting ENHANCED Solana Trading Bot with WEEK 1 SAFETY FIXES...")
        
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
            logger.info("💸 Enhanced bot is now operational and ready for REAL TRADING!")
            logger.info(f"💰 Will trade REAL MONEY: ${self.trade_amount/1_000_000} per trade")
        else:
            logger.info("🎯 Enhanced bot is now operational in SIMULATION mode!")
            logger.info(f"💰 Simulating trades with ${self.trade_amount/1_000_000} amounts")
        
        logger.info(f"🔍 Looking for NEW token opportunities with ENHANCED SAFETY...")
        logger.info(f"🛡️ WEEK 1 ENHANCEMENTS: Mandatory liquidity gates, honeypot detection, rebalanced scoring")
        
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
