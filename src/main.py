#!/usr/bin/env python3</span>
<span class="python-string">"""
Solana Trading Bot - ENHANCED WITH WEEK 1 CRITICAL SAFETY FIXES
⚠️ WARNING: This version uses REAL MONEY on Solana mainnet when enabled
Features: Mandatory Liquidity Verification, Honeypot Detection, Enhanced Safety
Updated: 2025-07-04 - Week 1 Critical Safety Fixes Applied
"""</span>

<span class="python-keyword">import</span> os
<span class="python-keyword">import</span> asyncio
<span class="python-keyword">import</span> aiohttp
<span class="python-keyword">import</span> json
<span class="python-keyword">import</span> base64
<span class="python-keyword">import</span> logging
<span class="python-keyword">import</span> time
<span class="python-keyword">import</span> datetime
<span class="python-keyword">import</span> requests
<span class="python-keyword">from</span> typing <span class="python-keyword">import</span> Dict, List, Optional, Tuple
<span class="python-keyword">from</span> datetime <span class="python-keyword">import</span> datetime <span class="python-keyword">as</span> dt, timedelta
<span class="python-keyword">from</span> dotenv <span class="python-keyword">import</span> load_dotenv

<span class="python-comment"># Load environment variables</span>
load_dotenv()

<span class="python-comment"># Configure logging</span>
logging.basicConfig(
    level=logging.INFO,
    format=<span class="python-string">'%(asctime)s - %(levelname)s - %(message)s'</span>,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

<span class="python-keyword">class</span> <span class="python-class">SolanaTradingBot</span>:
    <span class="python-keyword">def</span> <span class="python-function">__init__</span>(self):
        <span class="python-string">"""Initialize the trading bot with ALL environment variables properly loaded"""</span>
        
        <span class="python-comment"># WALLET CONFIGURATION</span>
        self.private_key = os.getenv(<span class="python-string">"SOLANA_PRIVATE_KEY"</span>)
        self.public_key = os.getenv(<span class="python-string">"SOLANA_PUBLIC_KEY"</span>) 
        
        <span class="python-comment"># RPC ENDPOINTS</span>
        self.rpc_url = os.getenv(<span class="python-string">"SOLANA_RPC_URL"</span>, <span class="python-string">"https://api.mainnet-beta.solana.com"</span>)
        self.quicknode_http = os.getenv(<span class="python-string">"QUICKNODE_HTTP_URL"</span>)
        self.quicknode_wss = os.getenv(<span class="python-string">"QUICKNODE_WSS_URL"</span>)
        
        <span class="python-comment"># TRADING CONFIGURATION</span>
        self.enable_real_trading = os.getenv(<span class="python-string">"ENABLE_REAL_TRADING"</span>, <span class="python-string">"false"</span>).lower() == <span class="python-string">"true"</span>
        self.trade_amount = int(float(os.getenv(<span class="python-string">"TRADE_AMOUNT"</span>, <span class="python-string">"1.0"</span>)) * 1_000_000)
        self.profit_target = float(os.getenv(<span class="python-string">"PROFIT_TARGET"</span>, <span class="python-string">"3.0"</span>))
        self.stop_loss_percent = float(os.getenv(<span class="python-string">"STOP_LOSS_PERCENT"</span>, <span class="python-string">"15.0"</span>))
        self.max_positions = int(os.getenv(<span class="python-string">"MAX_POSITIONS"</span>, <span class="python-string">"10"</span>))
        self.slippage = int(os.getenv(<span class="python-string">"SLIPPAGE_BPS"</span>, <span class="python-string">"50"</span>))
        
        <span class="python-comment"># SAFETY THRESHOLDS (CRITICAL FOR ANALYSIS)</span>
        self.safety_threshold = float(os.getenv(<span class="python-string">"SAFETY_THRESHOLD"</span>, <span class="python-string">"0.55"</span>))
        self.min_liquidity_usd = float(os.getenv(<span class="python-string">"MIN_LIQUIDITY_USD"</span>, <span class="python-string">"2500"</span>))
        self.min_volume_24h = float(os.getenv(<span class="python-string">"MIN_VOLUME_24H"</span>, <span class="python-string">"500"</span>))
        
        <span class="python-comment"># TOKEN ADDRESSES</span>
        self.usdc_mint = os.getenv(<span class="python-string">"USDC_MINT"</span>, <span class="python-string">"EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"</span>)
        self.sol_mint = os.getenv(<span class="python-string">"SOL_MINT"</span>, <span class="python-string">"So11111111111111111111111111111111111111112"</span>)
        
        <span class="python-comment"># API ENDPOINTS</span>
        self.jupiter_quote_url = os.getenv(<span class="python-string">"JUPITER_QUOTE_API"</span>, <span class="python-string">"https://quote-api.jup.ag/v6/quote"</span>)
        self.jupiter_swap_url = os.getenv(<span class="python-string">"JUPITER_SWAP_API"</span>, <span class="python-string">"https://quote-api.jup.ag/v6/swap"</span>)
        self.dexscreener_url = os.getenv(<span class="python-string">"DEXSCREENER_API"</span>, <span class="python-string">"https://api.dexscreener.com/latest/dex/tokens"</span>)
        
        <span class="python-comment"># BLACKLIST SYSTEM</span>
        self.blacklist_threshold = float(os.getenv(<span class="python-string">"BLACKLIST_THRESHOLD"</span>, <span class="python-string">"20.0"</span>))
        self.token_blacklist = set()
        self.blacklist_file = <span class="python-string">"token_blacklist.json"</span>
        
        <span class="python-comment"># TRADING STATE</span>
        self.active_positions = {}
        self.recently_traded = set()
        self.total_trades = 0
        self.profitable_trades = 0
        self.total_profit = 0.0
        
        <span class="python-comment"># Load existing blacklist</span>
        self.load_blacklist()
        
        <span class="python-comment"># Log configuration</span>
        logger.info(<span class="python-string">"🤖 Solana Trading Bot initialized with WEEK 1 SAFETY FIXES"</span>)
        logger.info(<span class="python-string">f"💰 Trade Amount: ${self.trade_amount/1_000_000}"</span>)
        logger.info(<span class="python-string">f"🎯 Profit Target: {self.profit_target}%"</span>)
        logger.info(<span class="python-string">f"🛑 Stop Loss: {self.stop_loss_percent}%"</span>)
        logger.info(<span class="python-string">f"📊 Max Positions: {self.max_positions}"</span>)
        logger.info(<span class="python-string">f"🔒 Safety Threshold: {self.safety_threshold}"</span>)
        logger.info(<span class="python-string">f"💧 Min Liquidity: ${self.min_liquidity_usd:,.0f}"</span>)
        logger.info(<span class="python-string">f"📈 Min Volume 24h: ${self.min_volume_24h:,.0f}"</span>)
        logger.info(<span class="python-string">f"🚫 Blacklist threshold: {self.blacklist_threshold}%"</span>)
        logger.info(<span class="python-string">f"🚫 Blacklisted tokens: {len(self.token_blacklist)}"</span>)
        
        <span class="python-keyword">if</span> self.enable_real_trading:
            logger.warning(<span class="python-string">"⚠️ REAL TRADING ENABLED - WILL USE REAL MONEY!"</span>)
        <span class="python-keyword">else</span>:
            logger.info(<span class="python-string">"💡 Simulation mode - No real money will be used"</span>)

    <span class="python-comment"># ============================================================================</span>
    <span class="python-comment"># WEEK 1 CRITICAL SAFETY FIXES - NEW METHODS</span>
    <span class="python-comment"># ============================================================================</span>

    <span class="highlight-change"><span class="python-keyword">async def</span> <span class="python-function">verify_minimum_liquidity</span>(self, token_address: str) -> Tuple[bool, float, Dict]:</span>
        <span class="python-string">"""🚨 WEEK 1 FIX: Mandatory liquidity verification - HARD BLOCKER"""</span>
        <span class="python-keyword">try</span>:
            logger.info(<span class="python-string">f"🔍 LIQUIDITY CHECK: {token_address[:8]}..."</span>)
            
            <span class="python-comment"># Get liquidity from DexScreener</span>
            url = <span class="python-string">f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"</span>
            
            headers = {
                <span class="python-string">'Accept'</span>: <span class="python-string">'*/*'</span>,
                <span class="python-string">'User-Agent'</span>: <span class="python-string">'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'</span>
            }
            
            <span class="python-keyword">async with</span> aiohttp.ClientSession() <span class="python-keyword">as</span> session:
                <span class="python-keyword">async with</span> session.get(url, headers=headers, timeout=10) <span class="python-keyword">as</span> response:
                    <span class="python-keyword">if</span> response.status == 200:
                        data = <span class="python-keyword">await</span> response.json()
                        pairs = data.get(<span class="python-string">'pairs'</span>, [])
                        
                        <span class="python-keyword">if</span> <span class="python-keyword">not</span> pairs:
                            logger.warning(<span class="python-string">f"🚫 NO PAIRS: {token_address[:8]} - no trading pairs found"</span>)
                            <span class="python-keyword">return</span> False, 0.0, {<span class="python-string">"reason"</span>: <span class="python-string">"no_pairs"</span>, <span class="python-string">"amount"</span>: 0}
                        
                        <span class="python-comment"># Get best liquidity pair</span>
                        best_pair = max(pairs, key=<span class="python-keyword">lambda</span> p: float(p.get(<span class="python-string">'liquidity'</span>, {}).get(<span class="python-string">'usd'</span>, 0)))
                        liquidity_usd = float(best_pair.get(<span class="python-string">'liquidity'</span>, {}).get(<span class="python-string">'usd'</span>, 0))
                        
                        <span class="python-comment"># 🚨 CRITICAL FIX: Zero liquidity = immediate failure</span>
                        <span class="python-keyword">if</span> liquidity_usd <= 0:
                            logger.error(<span class="python-string">f"🚫 ZERO LIQUIDITY: {token_address[:8]} - ${liquidity_usd}"</span>)
                            <span class="python-keyword">return</span> False, 0.0, {<span class="python-string">"reason"</span>: <span class="python-string">"zero_liquidity"</span>, <span class="python-string">"amount"</span>: liquidity_usd}
                        
                        <span class="python-comment"># 🚨 CRITICAL FIX: Below minimum = immediate failure</span>
                        <span class="python-keyword">if</span> liquidity_usd < self.min_liquidity_usd:
                            logger.error(<span class="python-string">f"🚫 INSUFFICIENT: {token_address[:8]} - ${liquidity_usd:,.0f} < ${self.min_liquidity_usd:,.0f}"</span>)
                            <span class="python-keyword">return</span> False, 0.0, {<span class="python-string">"reason"</span>: <span class="python-string">"below_minimum"</span>, <span class="python-string">"amount"</span>: liquidity_usd}
                        
                        <span class="python-comment"># Calculate liquidity quality score</span>
                        liquidity_score = min(liquidity_usd / (self.min_liquidity_usd * 4), 1.0)
                        
                        logger.info(<span class="python-string">f"✅ LIQUIDITY OK: {token_address[:8]} - ${liquidity_usd:,.0f} (score: {liquidity_score:.2f})"</span>)
                        <span class="python-keyword">return</span> True, liquidity_score, {<span class="python-string">"reason"</span>: <span class="python-string">"adequate"</span>, <span class="python-string">"amount"</span>: liquidity_usd}
                    
                    <span class="python-keyword">else</span>:
                        logger.warning(<span class="python-string">f"⚠️ API ERROR: Cannot verify liquidity for {token_address[:8]} (status: {response.status})"</span>)
                        <span class="python-keyword">return</span> False, 0.0, {<span class="python-string">"reason"</span>: <span class="python-string">"api_error"</span>, <span class="python-string">"status"</span>: response.status}
                        
        <span class="python-keyword">except</span> Exception <span class="python-keyword">as</span> e:
            logger.error(<span class="python-string">f"❌ LIQUIDITY CHECK ERROR: {token_address[:8]} - {e}"</span>)
            <span class="python-keyword">return</span> False, 0.0, {<span class="python-string">"reason"</span>: <span class="python-string">"error"</span>, <span class="python-string">"error"</span>: str(e)}

    <span class="highlight-change"><span class="python-keyword">async def</span> <span class="python-function">basic_honeypot_detection</span>(self, token_address: str) -> Tuple[bool, float, Dict]:</span>
        <span class="python-string">"""🚨 WEEK 1 FIX: Basic honeypot detection - Test if token can be sold"""</span>
        <span class="python-keyword">try</span>:
            logger.info(<span class="python-string">f"🍯 HONEYPOT CHECK: {token_address[:8]}..."</span>)
            
            <span class="python-comment"># Test 1: Can we get a buy quote?</span>
            buy_quote = <span class="python-keyword">await</span> self.get_jupiter_quote(
                input_mint=self.usdc_mint,
                output_mint=token_address,
                amount=100_000  <span class="python-comment"># $0.10 test amount</span>
            )
            
            <span class="python-keyword">if</span> <span class="python-keyword">not</span> buy_quote:
                logger.warning(<span class="python-string">f"🚫 CANNOT BUY: {token_address[:8]} - no buy quote available"</span>)
                <span class="python-keyword">return</span> False, 0.0, {<span class="python-string">"reason"</span>: <span class="python-string">"cannot_buy"</span>, <span class="python-string">"test"</span>: <span class="python-string">"buy_quote"</span>}
            
            <span class="python-comment"># Test 2: Can we get a sell quote for the estimated tokens?</span>
            estimated_tokens = int(buy_quote[<span class="python-string">"outAmount"</span>])
            sell_quote = <span class="python-keyword">await</span> self.get_jupiter_quote(
                input_mint=token_address,
                output_mint=self.usdc_mint,
                amount=estimated_tokens
            )
            
            <span class="python-keyword">if</span> <span class="python-keyword">not</span> sell_quote:
                logger.error(<span class="python-string">f"🚫 HONEYPOT DETECTED: {token_address[:8]} - can buy but cannot sell!"</span>)
                <span class="python-keyword">return</span> False, 0.0, {<span class="python-string">"reason"</span>: <span class="python-string">"cannot_sell"</span>, <span class="python-string">"test"</span>: <span class="python-string">"sell_quote"</span>}
            
            <span class="python-comment"># Test 3: Calculate round-trip efficiency</span>
            input_amount = int(buy_quote[<span class="python-string">"inAmount"</span>])
            output_amount = int(sell_quote[<span class="python-string">"outAmount"</span>])
            efficiency = output_amount / input_amount
            
            <span class="python-comment"># 🚨 CRITICAL: If we lose more than 70% in round trip = suspicious</span>
            <span class="python-keyword">if</span> efficiency < 0.3:
                logger.error(<span class="python-string">f"🚫 HIGH SLIPPAGE: {token_address[:8]} - {efficiency:.2f} efficiency (>70% loss)"</span>)
                <span class="python-keyword">return</span> False, 0.0, {<span class="python-string">"reason"</span>: <span class="python-string">"high_slippage"</span>, <span class="python-string">"efficiency"</span>: efficiency}
            
            <span class="python-comment"># Calculate sellability score</span>
            sellability_score = min(efficiency * 2, 1.0)  <span class="python-comment"># 50% efficiency = 1.0 score</span>
            
            logger.info(<span class="python-string">f"✅ SELLABLE: {token_address[:8]} - {efficiency:.2f} efficiency (score: {sellability_score:.2f})"</span>)
            <span class="python-keyword">return</span> True, sellability_score, {
                <span class="python-string">"reason"</span>: <span class="python-string">"sellable"</span>, 
                <span class="python-string">"efficiency"</span>: efficiency,
                <span class="python-string">"input_amount"</span>: input_amount,
                <span class="python-string">"output_amount"</span>: output_amount
            }
            
        <span class="python-keyword">except</span> Exception <span class="python-keyword">as</span> e:
            logger.error(<span class="python-string">f"❌ HONEYPOT CHECK ERROR: {token_address[:8]} - {e}"</span>)
            <span class="python-keyword">return</span> False, 0.0, {<span class="python-string">"reason"</span>: <span class="python-string">"test_failed"</span>, <span class="python-string">"error"</span>: str(e)}

    <span class="highlight-change"><span class="python-keyword">async def</span> <span class="python-function">enhanced_safety_check</span>(self, token_address: str) -> Tuple[bool, float, Dict]:</span>
        <span class="python-string">"""🚨 WEEK 1 FIX: Enhanced safety check with mandatory gates"""</span>
        <span class="python-keyword">try</span>:
            <span class="python-keyword">if</span> token_address == self.sol_mint:
                logger.info(<span class="python-string">f"⏭️ Skipping SOL - looking for new tokens only"</span>)
                <span class="python-keyword">return</span> False, 0.5, {<span class="python-string">"reason"</span>: <span class="python-string">"sol_token"</span>}
            
            logger.info(<span class="python-string">f"🔍 ENHANCED SAFETY CHECK: {token_address[:8]}"</span>)
            
            <span class="python-comment"># 🚨 MANDATORY GATE 1: Liquidity verification</span>
            liquidity_ok, liquidity_score, liquidity_details = <span class="python-keyword">await</span> self.verify_minimum_liquidity(token_address)
            <span class="python-keyword">if</span> <span class="python-keyword">not</span> liquidity_ok:
                logger.error(<span class="python-string">f"🚫 FAILED LIQUIDITY: {token_address[:8]} - {liquidity_details['reason']}"</span>)
                <span class="python-keyword">return</span> False, 0.0, {
                    <span class="python-string">"result"</span>: <span class="python-string">"FAILED_LIQUIDITY"</span>,
                    <span class="python-string">"liquidity_details"</span>: liquidity_details
                }
            
            <span class="python-comment"># 🚨 MANDATORY GATE 2: Honeypot detection</span>
            sellable_ok, sellable_score, sellable_details = <span class="python-keyword">await</span> self.basic_honeypot_detection(token_address)
            <span class="python-keyword">if</span> <span class="python-keyword">not</span> sellable_ok:
                logger.error(<span class="python-string">f"🚫 FAILED HONEYPOT: {token_address[:8]} - {sellable_details['reason']}"</span>)
                <span class="python-keyword">return</span> False, 0.0, {
                    <span class="python-string">"result"</span>: <span class="python-string">"FAILED_HONEYPOT"</span>,
                    <span class="python-string">"sellable_details"</span>: sellable_details
                }
            
            <span class="python-comment"># If mandatory gates pass, run quality analysis</span>
            dexscreener_score = <span class="python-keyword">await</span> self.dexscreener_analysis_fixed(token_address)
            pattern_score = <span class="python-keyword">await</span> self.pattern_analysis(token_address)
            
            <span class="python-comment"># 🚨 REBALANCED SCORING: Reduced pattern weight from 30% to 15%</span>
            weighted_score = (
                (liquidity_score * 0.35) +      <span class="python-comment"># Liquidity importance increased</span>
                (sellable_score * 0.25) +       <span class="python-comment"># Sellability importance added</span>
                (dexscreener_score * 0.25) +    <span class="python-comment"># Market data importance reduced</span>
                (pattern_score * 0.15)          <span class="python-comment"># Pattern importance reduced</span>
            )
            
            is_safe = weighted_score >= self.safety_threshold
            
            logger.info(<span class="python-string">f"🔒 SAFETY REPORT for {token_address[:8]}:"</span>)
            logger.info(<span class="python-string">f"   Liquidity:    {liquidity_score:.2f} (✓)"</span>)
            logger.info(<span class="python-string">f"   Sellability:  {sellable_score:.2f} (✓)"</span>)
            logger.info(<span class="python-string">f"   DexScreener:  {dexscreener_score:.2f}"</span>)
            logger.info(<span class="python-string">f"   Pattern:      {pattern_score:.2f}"</span>)
            logger.info(<span class="python-string">f"   FINAL:        {weighted_score:.2f} ({'✓ SAFE' if is_safe else '⚠️ RISKY'})"</span>)
            
            <span class="python-keyword">return</span> is_safe, weighted_score, {
                <span class="python-string">"result"</span>: <span class="python-string">"PASSED_ALL_CHECKS"</span> <span class="python-keyword">if</span> is_safe <span class="python-keyword">else</span> <span class="python-string">"LOW_QUALITY_SCORE"</span>,
                <span class="python-string">"final_score"</span>: weighted_score,
                <span class="python-string">"component_scores"</span>: {
                    <span class="python-string">"liquidity"</span>: liquidity_score,
                    <span class="python-string">"sellability"</span>: sellable_score,
                    <span class="python-string">"dexscreener"</span>: dexscreener_score,
                    <span class="python-string">"pattern"</span>: pattern_score
                },
                <span class="python-string">"weights"</span>: {
                    <span class="python-string">"liquidity"</span>: 0.35,
                    <span class="python-string">"sellability"</span>: 0.25,
                    <span class="python-string">"dexscreener"</span>: 0.25,
                    <span class="python-string">"pattern"</span>: 0.15
                }
            }
            
        <span class="python-keyword">except</span> Exception <span class="python-keyword">as</span> e:
            logger.error(<span class="python-string">f"❌ Error in enhanced safety check: {e}"</span>)
            <span class="python-keyword">return</span> False, 0.0, {<span class="python-string">"result"</span>: <span class="python-string">"ERROR"</span>, <span class="python-string">"error"</span>: str(e)}

    <span class="highlight-change"><span class="python-keyword">async def</span> <span class="python-function">dexscreener_analysis_fixed</span>(self, token_address: str) -> float:</span>
        <span class="python-string">"""🚨 WEEK 1 FIX: Fixed DexScreener analysis - no more false positives for zero liquidity"""</span>
        <span class="python-keyword">try</span>:
            url = <span class="python-string">f"{self.dexscreener_url}/{token_address}"</span>
            
            headers = {
                <span class="python-string">'Accept'</span>: <span class="python-string">'*/*'</span>,
                <span class="python-string">'User-Agent'</span>: <span class="python-string">'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'</span>
            }
            
            <span class="python-keyword">async with</span> aiohttp.ClientSession() <span class="python-keyword">as</span> session:
                <span class="python-keyword">async with</span> session.get(url, headers=headers, timeout=15) <span class="python-keyword">as</span> response:
                    <span class="python-keyword">if</span> response.status == 200:
                        data = <span class="python-keyword">await</span> response.json()
                        pairs = data.get(<span class="python-string">'pairs'</span>, [])
                        
                        <span class="python-keyword">if</span> pairs:
                            pair = max(pairs, key=<span class="python-keyword">lambda</span> p: float(p.get(<span class="python-string">'liquidity'</span>, {}).get(<span class="python-string">'usd'</span>, 0)))
                            
                            liquidity_usd = float(pair.get(<span class="python-string">'liquidity'</span>, {}).get(<span class="python-string">'usd'</span>, 0))
                            volume_24h = float(pair.get(<span class="python-string">'volume'</span>, {}).get(<span class="python-string">'h24'</span>, 0))
                            
                            <span class="python-comment"># 🚨 CRITICAL FIX: Zero/low liquidity = immediate low score</span>
                            <span class="python-keyword">if</span> liquidity_usd <= 0:
                                logger.warning(<span class="python-string">f"⚠️ DexScreener: Zero liquidity detected"</span>)
                                <span class="python-keyword">return</span> 0.0
                            
                            <span class="python-keyword">if</span> liquidity_usd < self.min_liquidity_usd:
                                logger.warning(<span class="python-string">f"⚠️ DexScreener: Below minimum liquidity (${liquidity_usd:,.0f})"</span>)
                                <span class="python-keyword">return</span> 0.1
                            
                            <span class="python-comment"># Start scoring only with adequate liquidity</span>
                            score = 0.0
                            
                            <span class="python-comment"># Liquidity scoring</span>
                            <span class="python-keyword">if</span> liquidity_usd >= self.min_liquidity_usd * 4:
                                score += 0.4
                            <span class="python-keyword">elif</span> liquidity_usd >= self.min_liquidity_usd * 2:
                                score += 0.3
                            <span class="python-keyword">elif</span> liquidity_usd >= self.min_liquidity_usd:
                                score += 0.2
                            
                            <span class="python-comment"># Volume scoring</span>
                            <span class="python-keyword">if</span> volume_24h >= self.min_volume_24h * 5:
                                score += 0.4
                            <span class="python-keyword">elif</span> volume_24h >= self.min_volume_24h * 2:
                                score += 0.3
                            <span class="python-keyword">elif</span> volume_24h >= self.min_volume_24h:
                                score += 0.2
                            
                            <span class="python-comment"># Base score for having data</span>
                            score += 0.2
                            
                            logger.info(<span class="python-string">f"📊 DexScreener Analysis: Liq=${liquidity_usd:,.0f}, Vol=${volume_24h:,.0f}, Score={score:.2f}"</span>)
                            <span class="python-keyword">return</span> min(score, 1.0)
                        <span class="python-keyword">else</span>:
                            logger.warning(<span class="python-string">"⚠️ No trading pairs found on DexScreener"</span>)
                            <span class="python-keyword">return</span> 0.0
                    <span class="python-keyword">else</span>:
                        logger.warning(<span class="python-string">f"⚠️ DexScreener API error: {response.status}"</span>)
                        <span class="python-keyword">return</span> 0.1
                        
        <span class="python-keyword">except</span> Exception <span class="python-keyword">as</span> e:
            logger.warning(<span class="python-string">f"⚠️ DexScreener analysis error: {e}"</span>)
            <span class="python-keyword">return</span> 0.1

    <span class="python-comment"># ============================================================================</span>
    <span class="python-comment"># UPDATED MAIN METHODS TO USE NEW SAFETY SYSTEM</span>
    <span class="python-comment"># ============================================================================</span>

    <span class="highlight-change"><span class="python-keyword">async def</span> <span class="python-function">check_token_safety</span>(self, token_address: str) -> Tuple[bool, float]:</span>
        <span class="python-string">"""🚨 UPDATED: Use enhanced safety check with mandatory gates"""</span>
        <span class="python-keyword">try</span>:
            is_safe, confidence, details = <span class="python-keyword">await</span> self.enhanced_safety_check(token_address)
            <span class="python-keyword">return</span> is_safe, confidence
        <span class="python-keyword">except</span> Exception <span class="python-keyword">as</span> e:
            logger.error(<span class="python-string">f"❌ Error in safety check: {e}"</span>)
            <span class="python-keyword">return</span> False, 0.0

    <span class="python-comment"># ============================================================================</span>
    <span class="python-comment"># ALL YOUR EXISTING METHODS REMAIN UNCHANGED</span>
    <span class="python-comment"># (load_blacklist, save_blacklist, validate_configuration, etc.)</span>
    <span class="python-comment"># ============================================================================</span>

    <span class="python-keyword">def</span> <span class="python-function">load_blacklist</span>(self):
        <span class="python-string">"""Load blacklist from persistent storage"""</span>
        <span class="python-keyword">try</span>:
            <span class="python-keyword">if</span> os.path.exists(self.blacklist_file):
                <span class="python-keyword">with</span> open(self.blacklist_file, <span class="python-string">'r'</span>) <span class="python-keyword">as</span> f:
                    data = json.load(f)
                    self.token_blacklist = set(data.get(<span class="python-string">'blacklisted_tokens'</span>, []))
                    logger.info(<span class="python-string">f"📋 Loaded {len(self.token_blacklist)} blacklisted tokens"</span>)
            <span class="python-keyword">else</span>:
                logger.info(<span class="python-string">"📋 No existing blacklist file found"</span>)
        <span class="python-keyword">except</span> Exception <span class="python-keyword">as</span> e:
            logger.error(<span class="python-string">f"❌ Error loading blacklist: {e}"</span>)
            self.token_blacklist = set()

    <span class="python-comment"># ... (All other existing methods remain exactly the same) ...</span>
    <span class="python-comment"># This includes: save_blacklist, add_to_blacklist, validate_configuration,</span>
    <span class="python-comment"># check_wallet_balance, get_token_balance, get_sol_balance, verify_token_balance,</span>
    <span class="python-comment"># get_jupiter_quote, send_transaction_ultra_minimal, execute_jupiter_swap_optimized,</span>
    <span class="python-comment"># pattern_analysis, pumpfun_discovery, dexscreener_discovery, raydium_discovery,</span>
    <span class="python-comment"># filter_tokens_enhanced, discover_new_tokens, execute_trade, sell_position_verified,</span>
    <span class="python-comment"># monitor_positions, main_trading_loop, run</span>

    <span class="python-keyword">async def</span> <span class="python-function">run</span>(self):
        <span class="python-string">"""Start the trading bot with enhanced safety"""</span>
        logger.info(<span class="python-string">"🚀 Starting Enhanced Solana Trading Bot with WEEK 1 SAFETY FIXES..."</span>)
        
        <span class="python-keyword">if</span> self.enable_real_trading:
            logger.warning(<span class="python-string">"⚠️⚠️⚠️ REAL TRADING MODE ENABLED ⚠️⚠️⚠️"</span>)
            logger.warning(<span class="python-string">"⚠️ This bot will use REAL MONEY on Solana mainnet"</span>)
            logger.warning(<span class="python-string">"⚠️ Enhanced safety features active - mandatory liquidity & honeypot checks"</span>)
            
            <span class="python-keyword">for</span> i <span class="python-keyword">in</span> range(10, 0, -1):
                logger.warning(<span class="python-string">f"⚠️ Starting real trading in {i} seconds... (Ctrl+C to cancel)"</span>)
                <span class="python-keyword">await</span> asyncio.sleep(1)
        
        <span class="python-keyword">if</span> <span class="python-keyword">not</span> <span class="python-keyword">await</span> self.validate_configuration():
            logger.error(<span class="python-string">"❌ Configuration validation failed"</span>)
            <span class="python-keyword">return</span>
        
        logger.info(<span class="python-string">"✅ Bot configuration validated"</span>)
        logger.info(<span class="python-string">"🛡️ Week 1 Safety Features Active:"</span>)
        logger.info(<span class="python-string">"   - Mandatory liquidity verification"</span>)
        logger.info(<span class="python-string">"   - Basic honeypot detection"</span>)
        logger.info(<span class="python-string">"   - Enhanced safety scoring"</span>)
        logger.info(<span class="python-string">"   - Zero tolerance for $0 liquidity"</span>)
        
        <span class="python-keyword">if</span> self.enable_real_trading:
            logger.info(<span class="python-string">"💸 Bot is now operational and ready for SAFE REAL TRADING!"</span>)
            logger.info(<span class="python-string">f"💰 Will trade REAL MONEY: ${self.trade_amount/1_000_000} per trade"</span>)
        <span class="python-keyword">else</span>:
            logger.info(<span class="python-string">"🎯 Bot is now operational in SAFE SIMULATION mode!"</span>)
            logger.info(<span class="python-string">f"💰 Simulating trades with ${self.trade_amount/1_000_000} amounts"</span>)
        
        logger.info(<span class="python-string">f"🔍 Looking for SAFE NEW token opportunities..."</span>)
        
        <span class="python-keyword">await</span> self.main_trading_loop()

<span class="python-keyword">async def</span> <span class="python-function">main</span>():
    <span class="python-string">"""Entry point"""</span>
    <span class="python-keyword">try</span>:
        bot = SolanaTradingBot()
        <span class="python-keyword">await</span> bot.run()
    <span class="python-keyword">except</span> Exception <span class="python-keyword">as</span> e:
        logger.error(<span class="python-string">f"❌ Fatal error: {e}"</span>)
    <span class="python-keyword">finally</span>:
        logger.info(<span class="python-string">"🏁 Enhanced bot shutdown complete"</span>)

<span class="python-keyword">if</span> __name__ == <span class="python-string">"__main__"</span>:
    asyncio.run(main())
