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
        Comprehensive token safety analysis using reliable APIs
        Returns: (is_safe, analysis_report)
        """
        logger.info(f"🔍 Analyzing token safety: {token_address}")
        
        try:
            # Run all working analysis methods in parallel
            results = await asyncio.gather(
                self.dextools_analysis(token_address),
                self.dexscreener_analysis(token_address),
                self.rpc_analysis(token_address),
                self.pattern_analysis(token_address),
                return_exceptions=True
            )
            
            dextools_result, dexscreener_result, rpc_result, pattern_result = results
            
            # Initialize scoring
            weighted_score = 0
            total_weight = 0
            analysis_report = {
                'token_address': token_address,
                'timestamp': time.time(),
                'checks': {}
            }
            
            # Process DexTools results (40% weight) - PREMIUM API
            if isinstance(dextools_result, dict) and not isinstance(dextools_result, Exception):
                analysis_report['checks']['dextools'] = dextools_result
                score = dextools_result.get('score', 0.40)
                weighted_score += score * 0.40
                total_weight += 0.40
            else:
                logger.warning(f"DexTools error: {dextools_result}")
                analysis_report['checks']['dextools'] = {'error': str(dextools_result), 'score': 0.40}
                weighted_score += 0.40 * 0.40
                total_weight += 0.40
            
            # Process DexScreener results (30% weight)
            if isinstance(dexscreener_result, dict) and not isinstance(dexscreener_result, Exception):
                analysis_report['checks']['dexscreener'] = dexscreener_result
                score = dexscreener_result.get('score', 0.25)
                weighted_score += score * 0.30
                total_weight += 0.30
            else:
                logger.warning(f"DexScreener error: {dexscreener_result}")
                analysis_report['checks']['dexscreener'] = {'error': str(dexscreener_result), 'score': 0.25}
                weighted_score += 0.25 * 0.30
                total_weight += 0.30
            
            # Process RPC analysis results (20% weight)
            if isinstance(rpc_result, dict) and not isinstance(rpc_result, Exception):
                analysis_report['checks']['rpc_analysis'] = rpc_result
                score = rpc_result.get('score', 0.40)
                weighted_score += score * 0.20
                total_weight += 0.20
            else:
                logger.warning(f"RPC analysis error: {rpc_result}")
                analysis_report['checks']['rpc_analysis'] = {'error': str(rpc_result), 'score': 0.40}
                weighted_score += 0.40 * 0.20
                total_weight += 0.20
            
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
    
    async def dextools_analysis(self, token_address: str) -> Dict:
        """DexTools Premium API analysis with Bearer token authentication"""
        try:
            if not self.config.DEXTOOLS_API_KEY:
                return {
                    'service': 'dextools',
                    'is_safe': False,
                    'score': 0.40,
                    'error': 'DexTools API key not configured',
                    'message': 'API key required'
                }
            
            # CORRECTED: Bearer token authentication for long alphanumeric keys
            headers = {
                'Authorization': f'Bearer {self.config.DEXTOOLS_API_KEY}',
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Get token info and score
            token_url = f"{self.config.DEXTOOLS_API_BASE}/token/solana/{token_address}"
            score_url = f"{self.config.DEXTOOLS_API_BASE}/token/solana/{token_address}/score"
            
            logger.info(f"🔑 Using Bearer token authentication for DexTools")
            
            # Try token info first
            async with self.session.get(token_url, headers=headers, timeout=15) as response:
                logger.info(f"📡 DexTools response status: {response.status}")
                
                if response.status == 200:
                    token_data = await response.json()
                    
                    # Extract data
                    data = token_data.get('data', {})
                    
                    # Market metrics
                    market_cap = data.get('mcap', 0)
                    liquidity = data.get('liquidity', 0)
                    volume_24h = data.get('volume24h', 0)
                    price_variation = data.get('variation24h', 0)
                    
                    # Try to get DexTools score
                    dextools_score = 50  # Default
                    try:
                        async with self.session.get(score_url, headers=headers, timeout=10) as score_response:
                            if score_response.status == 200:
                                score_data = await score_response.json()
                                dextools_score = score_data.get('data', {}).get('dextScore', 50)
                    except:
                        pass  # Use default score
                    
                    # Calculate our score based on multiple factors
                    our_score = 0.30  # Base score
                    
                    # DexTools score component (0-40%)
                    if dextools_score >= 90:
                        our_score += 0.40
                    elif dextools_score >= 80:
                        our_score += 0.35
                    elif dextools_score >= 70:
                        our_score += 0.30
                    elif dextools_score >= 60:
                        our_score += 0.25
                    elif dextools_score >= 50:
                        our_score += 0.20
                    else:
                        our_score += 0.10
                    
                    # Liquidity component (0-20%)
                    if liquidity >= self.config.MIN_LIQUIDITY_USD * 10:  # 10x minimum
                        our_score += 0.20
                    elif liquidity >= self.config.MIN_LIQUIDITY_USD * 3:  # 3x minimum
                        our_score += 0.15
                    elif liquidity >= self.config.MIN_LIQUIDITY_USD:
                        our_score += 0.10
                    else:
                        our_score += 0.05
                    
                    # Volume component (0-15%)
                    if volume_24h >= self.config.MIN_VOLUME_24H * 20:  # 20x minimum
                        our_score += 0.15
                    elif volume_24h >= self.config.MIN_VOLUME_24H * 5:  # 5x minimum
                        our_score += 0.12
                    elif volume_24h >= self.config.MIN_VOLUME_24H:
                        our_score += 0.08
                    else:
                        our_score += 0.03
                    
                    # Volatility check (penalty for extreme volatility)
                    if abs(price_variation) > 500:  # More than 500% change
                        our_score -= 0.10
                    elif abs(price_variation) > 200:  # More than 200% change
                        our_score -= 0.05
                    
                    # Ensure score bounds
                    our_score = max(0.10, min(1.0, our_score))
                    
                    is_safe = our_score >= 0.65
                    
                    # Create comprehensive message
                    message = f"DT:{dextools_score}/100, Liq:${liquidity:,.0f}, Vol:${volume_24h:,.0f}"
                    if abs(price_variation) > 100:
                        message += f", Var:{price_variation:+.1f}%"
                    
                    logger.info(f"✅ DexTools Bearer auth successful: {message}")
                    
                    return {
                        'service': 'dextools',
                        'is_safe': is_safe,
                        'score': our_score,
                        'dextools_score': dextools_score,
                        'market_cap': market_cap,
                        'liquidity': liquidity,
                        'volume_24h': volume_24h,
                        'price_variation_24h': price_variation,
                        'message': message
                    }
                
                elif response.status == 401:
                    logger.error("❌ DexTools 401: Invalid Bearer token")
                    return {
                        'service': 'dextools',
                        'is_safe': False,
                        'score': 0.40,
                        'error': 'Invalid Bearer token',
                        'message': 'Bearer token authentication failed'
                    }
                elif response.status == 403:
                    logger.error("❌ DexTools 403: Access forbidden - check subscription")
                    return {
                        'service': 'dextools',
                        'is_safe': False,
                        'score': 0.40,
                        'error': 'Access forbidden - subscription issue',
                        'message': 'Check DexTools subscription status'
                    }
                elif response.status == 404:
                    logger.warning("⚠️ DexTools 404: Token not found")
                    return {
                        'service': 'dextools',
                        'is_safe': False,
                        'score': 0.30,
                        'error': 'Token not found in DexTools',
                        'message': 'Token too new or not tracked'
                    }
                elif response.status == 429:
                    logger.warning("⚠️ DexTools 429: Rate limited")
                    return {
                        'service': 'dextools',
                        'is_safe': False,
                        'score': 0.35,
                        'error': 'Rate limited',
                        'message': 'DexTools rate limit exceeded'
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"❌ DexTools {response.status}: {error_text}")
                    return {
                        'service': 'dextools',
                        'is_safe': False,
                        'score': 0.35,
                        'error': f'API returned status {response.status}',
                        'message': f'DexTools API error: {response.status}'
                    }
                    
        except asyncio.TimeoutError:
            logger.warning("⚠️ DexTools timeout")
            return {
                'service': 'dextools',
                'is_safe': False,
                'score': 0.35,
                'error': 'Request timeout',
                'message': 'DexTools API timeout'
            }
        except Exception as e:
            logger.error(f"❌ DexTools error: {e}")
            return {
                'service': 'dextools',
                'is_safe': False,
                'score': 0.35,
                'error': str(e),
                'message': f'DexTools error: {str(e)[:50]}'
            }
    
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
    
