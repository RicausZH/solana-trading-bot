import asyncio
import aiohttp
import logging
from typing import Dict, List, Tuple, Optional
from aiohttp import ClientSession
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey
from config import Config
import time

logger = logging.getLogger(__name__)

class FraudDetector:
    def __init__(self, config: Config):
        self.config = config
        self.solana_client = AsyncClient(config.SOLANA_RPC_URL)
        self.session: Optional[ClientSession] = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def analyze_token_safety(self, token_address: str) -> Tuple[bool, Dict]:
        """
        Comprehensive token safety analysis using reliable FREE APIs
        Returns: (is_safe, analysis_report)
        """
        logger.info(f"🔍 Analyzing token safety: {token_address}")
        
        try:
            # Run all working analysis methods in parallel
            results = await asyncio.gather(
                self.dexscreener_analysis(token_address),   # Market data
                self.solscan_analysis(token_address),       # NEW - Free Solana data
                self.jupiter_liquidity_check(token_address), # NEW - Jupiter API check
                self.rpc_analysis(token_address),           # On-chain analysis
                self.pattern_analysis(token_address),       # Address analysis
                return_exceptions=True
            )
            
            dexscreener_result, solscan_result, jupiter_result, rpc_result, pattern_result = results
            
            # Initialize scoring with optimized weights
            weighted_score = 0
            total_weight = 0
            analysis_report = {
                'token_address': token_address,
                'timestamp': time.time(),
                'checks': {}
            }
            
            # Process DexScreener results (35% weight) - PRIMARY
            if isinstance(dexscreener_result, dict) and not isinstance(dexscreener_result, Exception):
                analysis_report['checks']['dexscreener'] = dexscreener_result
                score = dexscreener_result.get('score', 0.25)
                weighted_score += score * 0.35
                total_weight += 0.35
            else:
                logger.warning(f"DexScreener error: {dexscreener_result}")
                analysis_report['checks']['dexscreener'] = {'error': str(dexscreener_result), 'score': 0.25}
                weighted_score += 0.25 * 0.35
                total_weight += 0.35
            
            # Process Solscan results (25% weight) - NEW
            if isinstance(solscan_result, dict) and not isinstance(solscan_result, Exception):
                analysis_report['checks']['solscan'] = solscan_result
                score = solscan_result.get('score', 0.40)
                weighted_score += score * 0.25
                total_weight += 0.25
            else:
                logger.warning(f"Solscan error: {solscan_result}")
                analysis_report['checks']['solscan'] = {'error': str(solscan_result), 'score': 0.40}
                weighted_score += 0.40 * 0.25
                total_weight += 0.25
            
            # Process Jupiter results (15% weight) - NEW
            if isinstance(jupiter_result, dict) and not isinstance(jupiter_result, Exception):
                analysis_report['checks']['jupiter'] = jupiter_result
                score = jupiter_result.get('score', 0.50)
                weighted_score += score * 0.15
                total_weight += 0.15
            else:
                logger.warning(f"Jupiter error: {jupiter_result}")
                analysis_report['checks']['jupiter'] = {'error': str(jupiter_result), 'score': 0.50}
                weighted_score += 0.50 * 0.15
                total_weight += 0.15
            
            # Process RPC analysis results (15% weight)
            if isinstance(rpc_result, dict) and not isinstance(rpc_result, Exception):
                analysis_report['checks']['rpc_analysis'] = rpc_result
                score = rpc_result.get('score', 0.40)
                weighted_score += score * 0.15
                total_weight += 0.15
            else:
                logger.warning(f"RPC analysis error: {rpc_result}")
                analysis_report['checks']['rpc_analysis'] = {'error': str(rpc_result), 'score': 0.40}
                weighted_score += 0.40 * 0.15
                total_weight += 0.15
            
            # Process Pattern analysis results (10% weight)
            if isinstance(pattern_result, dict) and not isinstance(pattern_result, Exception):
                analysis_report['checks']['pattern_analysis'] = pattern_result
                score = pattern_result.get('score', 0.60)
                weighted_score += score * 0.10
                total_weight += 0.10
            else:
                logger.warning(f"Pattern analysis error: {pattern_result}")
                analysis_report['checks']['pattern_analysis'] = {'error': str(pattern_result), 'score': 0.60}
                weighted_score += 0.60 * 0.10
                total_weight += 0.10
            
            # Calculate final safety score
            final_score = weighted_score / total_weight if total_weight > 0 else 0
            is_safe = final_score >= self.config.SAFETY_THRESHOLD
            
            analysis_report['safety_score'] = final_score
            analysis_report['is_safe'] = is_safe
            analysis_report['recommendation'] = 'TRADE' if is_safe else 'RISKY' if final_score >= 0.50 else 'UNSAFE'
            
            logger.info(f"🔒 SAFETY REPORT for {token_address[:8]}:")
            
            # Log individual scores
            for service, data in analysis_report['checks'].items():
                if isinstance(data, dict):
                    service_score = data.get('score', 0)
                    message = data.get('message', data.get('error', 'Analysis complete'))
                    service_name = service.replace('_', ' ').title()
                    logger.info(f"   {service_name:12}: {service_score:.2f} - {message}")
            
            logger.info(f"   FINAL:      {final_score:.2f} ({'✓ SAFE' if is_safe else '⚠️ RISKY' if final_score >= 0.50 else '❌ UNSAFE'})")
            
            return is_safe, analysis_report
            
        except Exception as e:
            logger.error(f"Error analyzing token safety for {token_address}: {e}")
            return False, {'error': str(e), 'is_safe': False}
    
    async def dexscreener_analysis(self, token_address: str) -> Dict:
        """DexScreener API analysis - FREE and RELIABLE"""
        try:
            url = f"{self.config.DEXSCREENER_API}/{token_address}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            async with self.session.get(url, headers=headers, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    pairs = data.get('pairs', [])
                    
                    if pairs:
                        # Get the pair with highest liquidity
                        pair = max(pairs, key=lambda p: float(p.get('liquidity', {}).get('usd', 0)))
                        
                        # Extract market data
                        liquidity_usd = float(pair.get('liquidity', {}).get('usd', 0))
                        volume_24h = float(pair.get('volume', {}).get('h24', 0))
                        fdv = float(pair.get('fdv', 0))
                        price_change_24h = float(pair.get('priceChange', {}).get('h24', 0))
                        
                        # Safety criteria
                        has_liquidity = liquidity_usd >= self.config.MIN_LIQUIDITY_USD
                        has_volume = volume_24h >= self.config.MIN_VOLUME_24H
                        has_fdv = fdv > 0
                        reasonable_volatility = abs(price_change_24h) < 300  # Not extremely volatile
                        
                        # Calculate score
                        score = 0.20  # Base score
                        
                        if has_liquidity:
                            score += 0.30
                        if has_volume:
                            score += 0.25
                        if has_fdv:
                            score += 0.15
                        if reasonable_volatility:
                            score += 0.10
                        
                        # Bonus for excellent metrics
                        if liquidity_usd > 50000:
                            score += 0.05
                        if volume_24h > 10000:
                            score += 0.05
                        
                        is_safe = has_liquidity and has_volume and has_fdv and reasonable_volatility
                        
                        # Create message
                        message = f"Liq: ${liquidity_usd:,.0f}, Vol: ${volume_24h:,.0f}"
                        if not reasonable_volatility:
                            message += f", High volatility: {price_change_24h:.1f}%"
                        
                        return {
                            'service': 'dexscreener',
                            'is_safe': is_safe,
                            'score': min(score, 1.0),
                            'liquidity_usd': liquidity_usd,
                            'volume_24h': volume_24h,
                            'fdv': fdv,
                            'price_change_24h': price_change_24h,
                            'pair_count': len(pairs),
                            'message': message
                        }
                    else:
                        return {
                            'service': 'dexscreener',
                            'is_safe': False,
                            'score': 0.15,
                            'error': 'No trading pairs found',
                            'message': 'No trading pairs found'
                        }
                else:
                    return {
                        'service': 'dexscreener',
                        'is_safe': False,
                        'score': 0.15,
                        'error': f'API returned status {response.status}',
                        'message': f'DexScreener API error: {response.status}'
                    }
                    
        except asyncio.TimeoutError:
            return {
                'service': 'dexscreener',
                'is_safe': False,
                'score': 0.15,
                'error': 'Request timeout',
                'message': 'DexScreener timeout'
            }
        except Exception as e:
            return {
                'service': 'dexscreener',
                'is_safe': False,
                'score': 0.15,
                'error': str(e),
                'message': f'DexScreener error: {str(e)[:50]}'
            }
    
    async def solscan_analysis(self, token_address: str) -> Dict:
        """Solscan API analysis - FREE Solana-specific data"""
        try:
            url = f"https://public-api.solscan.io/token/meta?tokenAddress={token_address}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            async with self.session.get(url, headers=headers, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Extract token metadata
                    symbol = data.get('symbol', '')
                    name = data.get('name', '')
                    decimals = data.get('decimals', 0)
                    supply = float(data.get('supply', 0))
                    
                    # Calculate score based on metadata quality
                    score = 0.30  # Base score
                    
                    # Symbol quality (0-20%)
                    if symbol and len(symbol) <= 10 and symbol.replace('$', '').isalnum():
                        score += 0.20
                    elif symbol and len(symbol) <= 15:
                        score += 0.15
                    elif symbol:
                        score += 0.10
                    
                    # Name quality (0-15%)
                    if name and len(name) <= 50 and len(name) >= 3:
                        score += 0.15
                    elif name:
                        score += 0.10
                    
                    # Decimals standard (0-10%)
                    if decimals in [6, 8, 9]:  # Standard token decimals
                        score += 0.10
                    elif decimals > 0:
                        score += 0.05
                    
                    # Supply analysis (0-15%)
                    if supply > 0:
                        if 1000 <= supply <= 1_000_000_000:  # Reasonable supply
                            score += 0.15
                        elif supply <= 10_000_000_000:  # High but acceptable
                            score += 0.10
                        else:
                            score += 0.05
                    
                    is_safe = score >= 0.60
                    
                    message = f"Symbol: {symbol}, Decimals: {decimals}, Supply: {supply:,.0f}"
                    
                    return {
                        'service': 'solscan',
                        'is_safe': is_safe,
                        'score': score,
                        'symbol': symbol,
                        'name': name,
                        'decimals': decimals,
                        'supply': supply,
                        'message': message
                    }
                    
                elif response.status == 404:
                    return {
                        'service': 'solscan',
                        'is_safe': False,
                        'score': 0.25,
                        'error': 'Token not found',
                        'message': 'Token not in Solscan database'
                    }
                else:
                    return {
                        'service': 'solscan',
                        'is_safe': False,
                        'score': 0.30,
                        'error': f'API returned status {response.status}',
                        'message': f'Solscan API error: {response.status}'
                    }
                    
        except asyncio.TimeoutError:
            return {
                'service': 'solscan',
                'is_safe': False,
                'score': 0.30,
                'error': 'Request timeout',
                'message': 'Solscan timeout'
            }
        except Exception as e:
            return {
                'service': 'solscan',
                'is_safe': False,
                'score': 0.30,
                'error': str(e),
                'message': f'Solscan error: {str(e)[:50]}'
            }
    
    async def jupiter_liquidity_check(self, token_address: str) -> Dict:
        """Jupiter API liquidity check - Using your existing Jupiter integration"""
        try:
            # Try to get a quote to see if Jupiter can trade this token
            quote_url = "https://quote-api.jup.ag/v6/quote"
            params = {
                "inputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
                "outputMint": token_address,
                "amount": 1000000,  # $1 USDC
                "slippageBps": 300,  # 3% slippage
                "onlyDirectRoutes": "false"
            }
            
            async with self.session.get(quote_url, params=params, timeout=10) as response:
                if response.status == 200:
                    quote_data = await response.json()
                    
                    if quote_data and 'outAmount' in quote_data:
                        out_amount = int(quote_data.get('outAmount', 0))
                        price_impact = float(quote_data.get('priceImpactPct', 0))
                        
                        # Calculate score based on tradability
                        score = 0.40  # Base score for being tradable
                        
                        # Price impact analysis (0-30%)
                        if price_impact < 1:  # Less than 1% impact
                            score += 0.30
                        elif price_impact < 3:  # Less than 3% impact
                            score += 0.20
                        elif price_impact < 10:  # Less than 10% impact
                            score += 0.10
                        else:
                            score += 0.05
                        
                        # Route quality (0-20%)
                        route_plan = quote_data.get('routePlan', [])
                        if len(route_plan) == 1:  # Direct route
                            score += 0.20
                        elif len(route_plan) <= 3:  # Short route
                            score += 0.15
                        else:
                            score += 0.10
                        
                        is_safe = score >= 0.60 and price_impact < 15
                        
                        message = f"Tradable via Jupiter, Impact: {price_impact:.2f}%, Routes: {len(route_plan)}"
                        
                        return {
                            'service': 'jupiter',
                            'is_safe': is_safe,
                            'score': score,
                            'price_impact': price_impact,
                            'route_count': len(route_plan),
                            'tradable': True,
                            'message': message
                        }
                    else:
                        return {
                            'service': 'jupiter',
                            'is_safe': False,
                            'score': 0.20,
                            'error': 'Invalid quote response',
                            'message': 'Jupiter quote failed'
                        }
                        
                elif response.status == 400:
                    return {
                        'service': 'jupiter',
                        'is_safe': False,
                        'score': 0.10,
                        'error': 'Token not tradable on Jupiter',
                        'message': 'Not supported by Jupiter'
                    }
                else:
                    return {
                        'service': 'jupiter',
                        'is_safe': False,
                        'score': 0.25,
                        'error': f'Jupiter API error: {response.status}',
                        'message': f'Jupiter error: {response.status}'
                    }
                    
        except asyncio.TimeoutError:
            return {
                'service': 'jupiter',
                'is_safe': False,
                'score': 0.25,
                'error': 'Request timeout',
                'message': 'Jupiter timeout'
            }
        except Exception as e:
            return {
                'service': 'jupiter',
                'is_safe': False,
                'score': 0.25,
                'error': str(e),
                'message': f'Jupiter error: {str(e)[:50]}'
            }
    
    async def rpc_analysis(self, token_address: str) -> Dict:
        """Enhanced RPC-based on-chain analysis"""
        try:
            pubkey = Pubkey.from_string(token_address)
            
            # Get account info
            response = await self.solana_client.get_account_info(pubkey)
            
            if response.value is None:
                return {
                    'service': 'rpc_analysis',
                    'is_safe': False,
                    'score': 0.20,
                    'error': 'Token account not found',
                    'message': 'Token account not found'
                }
            
            account_info = response.value
            
            # Analyze account data
            issues = []
            good_signs = []
            
            # Check if account has data
            if account_info.data is None or len(account_info.data) == 0:
                issues.append("No metadata")
            else:
                good_signs.append("Has metadata")
            
            # Check account owner (should be Token Program)
            token_program = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            if str(account_info.owner) != token_program:
                issues.append("Non-standard owner")
            else:
                good_signs.append("Standard token")
            
            # Check lamports (rent)
            if account_info.lamports < 1000000:  # Less than 0.001 SOL
                issues.append("Low rent")
            else:
                good_signs.append("Adequate rent")
            
            # Score based on analysis
            total_factors = len(issues) + len(good_signs)
            safety_ratio = len(good_signs) / total_factors if total_factors > 0 else 0
            
            is_safe = safety_ratio >= 0.7 and len(issues) <= 1
            score = 0.25 + (safety_ratio * 0.50)  # Scale from 0.25 to 0.75
            
            # Create message
            message_parts = []
            if issues:
                message_parts.append(f"Issues: {', '.join(issues)} ❌")
            if good_signs:
                message_parts.append(f"Good: {', '.join(good_signs)} ✓")
            
            message = ' | '.join(message_parts) if message_parts else 'RPC analysis complete'
            
            return {
                'service': 'rpc_analysis',
                'is_safe': is_safe,
                'score': score,
                'message': message,
                'issues': issues,
                'good_signs': good_signs,
                'safety_ratio': safety_ratio,
                'lamports': account_info.lamports
            }
            
        except Exception as e:
            return {
                'service': 'rpc_analysis',
                'is_safe': False,
                'score': 0.40,
                'error': str(e),
                'message': f'RPC error: {str(e)[:50]}'
            }
    
    async def pattern_analysis(self, token_address: str) -> Dict:
        """Enhanced pattern analysis for token addresses"""
        try:
            score_factors = []
            
            # Check address length (should be 44 characters for Solana)
            if len(token_address) == 44:
                score_factors.append(0.25)  # Correct length
            else:
                score_factors.append(0.0)
            
            # Check character variety
            unique_chars = len(set(token_address))
            if unique_chars >= 25:
                score_factors.append(0.30)  # Excellent variety
            elif unique_chars >= 20:
                score_factors.append(0.25)  # Good variety
            elif unique_chars >= 15:
                score_factors.append(0.15)  # Moderate variety
            else:
                score_factors.append(0.05)  # Poor variety
            
            # Check for suspicious patterns
            suspicious_patterns = ['1111', '0000', 'aaaa', 'zzzz', 'pump', '9999', '2222']
            has_suspicious = any(pattern in token_address.lower() for pattern in suspicious_patterns)
            
            if not has_suspicious:
                score_factors.append(0.20)  # No suspicious patterns
            else:
                score_factors.append(0.0)
            
            # Check if starts with number or letter (randomness indicator)
            first_char = token_address[0]
            if first_char.isdigit() or first_char.isupper():
                score_factors.append(0.15)  # Good start
            else:
                score_factors.append(0.05)
            
            # Check case and digit mixing
            has_upper = any(c.isupper() for c in token_address)
            has_lower = any(c.islower() for c in token_address)
            has_digit = any(c.isdigit() for c in token_address)
            
            if has_upper and has_lower and has_digit:
                score_factors.append(0.10)  # Good mixing
            else:
                score_factors.append(0.02)
            
            # Calculate final score
            total_score = sum(score_factors)
            is_safe = total_score >= 0.70
            
            # Create descriptive message
            message_parts = []
            if len(token_address) == 44:
                message_parts.append("Valid address")
            if unique_chars >= 20:
                message_parts.append("Good char variety")
            if first_char.isdigit():
                message_parts.append("Starts with number")
            if not has_suspicious:
                message_parts.append("No suspicious patterns")
            
            message = ', '.join(message_parts) if message_parts else 'Pattern analysis complete'
            
            return {
                'service': 'pattern_analysis',
                'is_safe': is_safe,
                'score': total_score,
                'message': message,
                'unique_chars': unique_chars,
                'has_suspicious_patterns': has_suspicious,
                'char_variety_score': score_factors[1] if len(score_factors) > 1 else 0,
                'pattern_score': score_factors[2] if len(score_factors) > 2 else 0
            }
            
        except Exception as e:
            return {
                'service': 'pattern_analysis',
                'is_safe': False,
                'score': 0.50,
                'error': str(e),
                'message': f'Pattern analysis error: {str(e)[:50]}'
            }
