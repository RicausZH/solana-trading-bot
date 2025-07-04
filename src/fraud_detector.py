import asyncio
import aiohttp
import logging
import time
from typing import Dict, List, Tuple, Optional
from aiohttp import ClientSession
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey
from config import Config

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
        Comprehensive token safety analysis using reliable APIs only
        Returns: (is_safe, analysis_report)
        """
        logger.info(f"🔍 Analyzing token safety: {token_address}")
        
        try:
            # Run only working analysis methods in parallel
            results = await asyncio.gather(
                self.dextools_analysis(token_address),
                self.dexscreener_analysis(token_address),
                self.rpc_analysis(token_address),
                self.pattern_analysis(token_address),
                return_exceptions=True
            )
            
            dextools_result, dexscreener_result, rpc_result, pattern_result = results
            
            # Initialize weighted scoring
            weighted_score = 0
            total_weight = 0
            analysis_report = {
                'token_address': token_address,
                'timestamp': time.time(),
                'checks': {}
            }
            
            # Process DexTools results (45% weight - Premium API)
            if isinstance(dextools_result, dict) and not isinstance(dextools_result, Exception):
                analysis_report['checks']['dextools'] = dextools_result
                score = dextools_result.get('score', 0.40)
                weighted_score += score * self.config.DEXTOOLS_WEIGHT
                total_weight += self.config.DEXTOOLS_WEIGHT
            else:
                logger.warning(f"DexTools error: {dextools_result}")
                analysis_report['checks']['dextools'] = {'error': str(dextools_result), 'score': 0.40}
                weighted_score += 0.40 * self.config.DEXTOOLS_WEIGHT
                total_weight += self.config.DEXTOOLS_WEIGHT
            
            # Process DexScreener results (30% weight)
            if isinstance(dexscreener_result, dict) and not isinstance(dexscreener_result, Exception):
                analysis_report['checks']['dexscreener'] = dexscreener_result
                score = dexscreener_result.get('score', 0.25)
                weighted_score += score * self.config.DEXSCREENER_WEIGHT
                total_weight += self.config.DEXSCREENER_WEIGHT
            else:
                logger.warning(f"DexScreener error: {dexscreener_result}")
                analysis_report['checks']['dexscreener'] = {'error': str(dexscreener_result), 'score': 0.25}
                weighted_score += 0.25 * self.config.DEXSCREENER_WEIGHT
                total_weight += self.config.DEXSCREENER_WEIGHT
            
            # Process RPC analysis results (20% weight)
            if isinstance(rpc_result, dict) and not isinstance(rpc_result, Exception):
                analysis_report['checks']['rpc_analysis'] = rpc_result
                score = rpc_result.get('score', 0.40)
                weighted_score += score * self.config.RPC_WEIGHT
                total_weight += self.config.RPC_WEIGHT
            else:
                logger.warning(f"RPC analysis error: {rpc_result}")
                analysis_report['checks']['rpc_analysis'] = {'error': str(rpc_result), 'score': 0.40}
                weighted_score += 0.40 * self.config.RPC_WEIGHT
                total_weight += self.config.RPC_WEIGHT
            
            # Process Pattern analysis results (5% weight)
            if isinstance(pattern_result, dict) and not isinstance(pattern_result, Exception):
                analysis_report['checks']['pattern_analysis'] = pattern_result
                score = pattern_result.get('score', 0.60)
                weighted_score += score * self.config.PATTERN_WEIGHT
                total_weight += self.config.PATTERN_WEIGHT
            else:
                logger.warning(f"Pattern analysis error: {pattern_result}")
                analysis_report['checks']['pattern_analysis'] = {'error': str(pattern_result), 'score': 0.60}
                weighted_score += 0.60 * self.config.PATTERN_WEIGHT
                total_weight += self.config.PATTERN_WEIGHT
            
            # Calculate final safety score
            final_score = weighted_score / total_weight if total_weight > 0 else 0
            is_safe = final_score >= self.config.SAFETY_THRESHOLD
            
            analysis_report['safety_score'] = final_score
            analysis_report['is_safe'] = is_safe
            analysis_report['recommendation'] = 'SAFE' if is_safe else 'RISKY' if final_score >= 0.45 else 'UNSAFE'
            
            # Log detailed results
            logger.info(f"🔒 SAFETY REPORT for {token_address[:8]}:")
            
            # Log individual service scores
            for service, data in analysis_report['checks'].items():
                if isinstance(data, dict):
                    service_score = data.get('score', 0)
                    message = data.get('message', data.get('error', 'Analysis complete'))
                    service_name = service.replace('_', ' ').title()
                    logger.info(f"   {service_name:12}: {service_score:.2f} - {message}")
            
            logger.info(f"   FINAL:      {final_score:.2f} ({'✓ SAFE' if is_safe else '⚠️ RISKY' if final_score >= 0.45 else '❌ UNSAFE'})")
            
            return is_safe, analysis_report
            
        except Exception as e:
            logger.error(f"Error analyzing token safety for {token_address}: {e}")
            return False, {'error': str(e), 'is_safe': False}
    
    async def dextools_analysis(self, token_address: str) -> Dict:
        """DexTools Premium API analysis - INSTITUTIONAL GRADE"""
        try:
            if not self.config.DEXTOOLS_API_KEY:
                return {
                    'service': 'dextools',
                    'is_safe': False,
                    'score': 0.40,
                    'error': 'DexTools API key not configured'
                }
            
            headers = {
                'X-API-Key': self.config.DEXTOOLS_API_KEY,
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Get comprehensive token data
            token_url = f"{self.config.DEXTOOLS_API_BASE}/token/solana/{token_address}"
            score_url = f"{self.config.DEXTOOLS_API_BASE}/token/solana/{token_address}/score"
            
            try:
                async with self.session.get(token_url, headers=headers, timeout=15) as token_response:
                    async with self.session.get(score_url, headers=headers, timeout=15) as score_response:
                        
                        if token_response.status == 200:
                            token_data = await token_response.json()
                            
                            # Try to get score data (might fail for very new tokens)
                            score_data = {}
                            if score_response.status == 200:
                                score_data = await score_response.json()
                            
                            # Extract token information
                            token_info = token_data.get('data', {})
                            score_info = score_data.get('data', {})
                            
                            # DexTools metrics
                            dextools_score = score_info.get('dextScore', 0)
                            market_cap = token_info.get('mcap', 0)
                            liquidity = token_info.get('liquidity', {}).get('base', 0) if isinstance(token_info.get('liquidity'), dict) else token_info.get('liquidity', 0)
                            volume_24h = token_info.get('volume24h', 0)
                            social_score = token_info.get('socialScore', 0)
                            creation_block = token_info.get('creationBlock', 0)
                            
                            # Advanced scoring algorithm
                            our_score = 0.30  # Base score
                            
                            # DexTools score component (40% of total)
                            if dextools_score >= 90:
                                our_score += 0.40
                            elif dextools_score >= 70:
                                our_score += 0.32
                            elif dextools_score >= 50:
                                our_score += 0.24
                            elif dextools_score >= 30:
                                our_score += 0.16
                            else:
                                our_score += 0.08
                            
                            # Liquidity component (25% of total)
                            if liquidity >= 100000:  # $100K+
                                our_score += 0.25
                            elif liquidity >= 50000:  # $50K+
                                our_score += 0.20
                            elif liquidity >= 10000:  # $10K+
                                our_score += 0.15
                            elif liquidity >= 5000:   # $5K+
                                our_score += 0.10
                            else:
                                our_score += 0.05
                            
                            # Volume component (20% of total)
                            if volume_24h >= 100000:  # $100K+ daily volume
                                our_score += 0.20
                            elif volume_24h >= 50000:
                                our_score += 0.16
                            elif volume_24h >= 10000:
                                our_score += 0.12
                            elif volume_24h >= 1000:
                                our_score += 0.08
                            else:
                                our_score += 0.04
                            
                            # Social score component (10% of total)
                            if social_score >= 80:
                                our_score += 0.10
                            elif social_score >= 60:
                                our_score += 0.08
                            elif social_score >= 40:
                                our_score += 0.06
                            else:
                                our_score += 0.04
                            
                            # Token age bonus (5% of total)
                            if creation_block > 0:
                                our_score += 0.05  # Bonus for having creation data
                            
                            # Cap the score
                            our_score = min(our_score, 1.0)
                            
                            is_safe = our_score >= 0.65
                            
                            # Create comprehensive message
                            message_parts = []
                            if dextools_score > 0:
                                message_parts.append(f"DT Score: {dextools_score}/100")
                            if liquidity > 0:
                                message_parts.append(f"Liq: ${liquidity:,.0f}")
                            if volume_24h > 0:
                                message_parts.append(f"Vol: ${volume_24h:,.0f}")
                            if social_score > 0:
                                message_parts.append(f"Social: {social_score}")
                            
                            message = ", ".join(message_parts) if message_parts else "DexTools analysis complete"
                            
                            return {
                                'service': 'dextools',
                                'is_safe': is_safe,
                                'score': our_score,
                                'dextools_score': dextools_score,
                                'market_cap': market_cap,
                                'liquidity': liquidity,
                                'volume_24h': volume_24h,
                                'social_score': social_score,
                                'creation_block': creation_block,
                                'message': message
                            }
                        
                        elif token_response.status == 404:
                            return {
                                'service': 'dextools',
                                'is_safe': False,
                                'score': 0.35,
                                'error': 'Token not found in DexTools (too new)',
                                'message': 'Token not in DexTools database'
                            }
                        elif token_response.status == 429:
                            return {
                                'service': 'dextools',
                                'is_safe': False,
                                'score': 0.40,
                                'error': 'DexTools rate limit exceeded',
                                'message': 'DexTools rate limited'
                            }
                        else:
                            return {
                                'service': 'dextools',
                                'is_safe': False,
                                'score': 0.40,
                                'error': f'DexTools API error: {token_response.status}',
                                'message': f'DexTools API error: {token_response.status}'
                            }
                            
            except asyncio.TimeoutError:
                return {
                    'service': 'dextools',
                    'is_safe': False,
                    'score': 0.40,
                    'error': 'DexTools request timeout',
                    'message': 'DexTools timeout'
                }
                
        except Exception as e:
            return {
                'service': 'dextools',
                'is_safe': False,
                'score': 0.40,
                'error': str(e),
                'message': f'DexTools error: {str(e)[:50]}'
            }
    
    async def dexscreener_analysis(self, token_address: str) -> Dict:
        """DexScreener API analysis - FREE and COMPREHENSIVE"""
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
                        best_pair = max(pairs, key=lambda p: float(p.get('liquidity', {}).get('usd', 0)))
                        
                        # Extract market data
                        liquidity_usd = float(best_pair.get('liquidity', {}).get('usd', 0))
                        volume_24h = float(best_pair.get('volume', {}).get('h24', 0))
                        fdv = float(best_pair.get('fdv', 0))
                        price_change_24h = float(best_pair.get('priceChange', {}).get('h24', 0))
                        
                        # Enhanced safety criteria
                        has_liquidity = liquidity_usd >= self.config.MIN_LIQUIDITY_USD
                        has_volume = volume_24h >= self.config.MIN_VOLUME_24H
                        has_fdv = fdv > 0
                        reasonable_volatility = abs(price_change_24h) <= 300
                        
                        # Calculate enhanced score
                        score = 0.15  # Base score
                        
                        # Liquidity scoring (40% of total)
                        if liquidity_usd >= 100000:
                            score += 0.40
                        elif liquidity_usd >= 50000:
                            score += 0.32
                        elif liquidity_usd >= 20000:
                            score += 0.24
                        elif liquidity_usd >= 5000:
                            score += 0.16
                        elif liquidity_usd >= 1000:
                            score += 0.08
                        
                        # Volume scoring (30% of total)
                        if volume_24h >= 50000:
                            score += 0.30
                        elif volume_24h >= 20000:
                            score += 0.24
                        elif volume_24h >= 5000:
                            score += 0.18
                        elif volume_24h >= 1000:
                            score += 0.12
                        elif volume_24h >= 100:
                            score += 0.06
                        
                        # FDV and volatility (15% each)
                        if has_fdv:
                            score += 0.15
                        if reasonable_volatility:
                            score += 0.15
                        
                        is_safe = has_liquidity and has_volume and reasonable_volatility
                        
                        # Create comprehensive message
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
                            'message': 'No trading pairs'
                        }
                else:
                    return {
                        'service': 'dexscreener',
                        'is_safe': False,
                        'score': 0.15,
                        'error': f'API returned status {response.status}',
                        'message': f'DexScreener error: {response.status}'
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
                    'message': 'Account not found'
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
            score = 0.25 + (safety_ratio * 0.65)  # Scale from 0.25 to 0.90
            
            # Create message
            message_parts = []
            if good_signs:
                message_parts.append(f"Good: {', '.join(good_signs)} ✓")
            if issues:
                message_parts.append(f"Issues: {', '.join(issues)} ⚠️")
            
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
                score_factors.append(0.30)  # Correct length
            else:
                score_factors.append(0.0)
            
            # Check character variety
            unique_chars = len(set(token_address))
            if unique_chars >= 30:
                score_factors.append(0.35)  # Excellent variety
            elif unique_chars >= 25:
                score_factors.append(0.28)  # Very good variety
            elif unique_chars >= 20:
                score_factors.append(0.20)  # Good variety
            elif unique_chars >= 15:
                score_factors.append(0.12)  # Moderate variety
            else:
                score_factors.append(0.05)  # Poor variety
            
            # Check for suspicious patterns
            suspicious_patterns = ['1111', '0000', 'aaaa', 'zzzz', 'pump', '2222', '3333', '9999']
            has_suspicious = any(pattern in token_address.lower() for pattern in suspicious_patterns)
            
            if not has_suspicious:
                score_factors.append(0.20)  # No suspicious patterns
            else:
                score_factors.append(0.0)
            
            # Check character mixing
            has_upper = any(c.isupper() for c in token_address)
            has_lower = any(c.islower() for c in token_address)
            has_digit = any(c.isdigit() for c in token_address)
            
            if has_upper and has_lower and has_digit:
                score_factors.append(0.15)  # Good mixing
            elif (has_upper and has_lower) or (has_upper and has_digit) or (has_lower and has_digit):
                score_factors.append(0.10)  # Moderate mixing
            else:
                score_factors.append(0.0)   # Poor mixing
            
            # Calculate final score
            total_score = sum(score_factors)
            is_safe = total_score >= 0.70
            
            # Create descriptive message
            message_parts = []
            if len(token_address) == 44:
                message_parts.append("Valid address")
            if unique_chars >= 25:
                message_parts.append("Good char variety")
            if not has_suspicious:
                message_parts.append("No suspicious patterns")
            if token_address[0].isdigit():
                message_parts.append("Starts with number")
            
            message = ', '.join(message_parts) if message_parts else 'Pattern analysis complete'
            
            return {
                'service': 'pattern_analysis',
                'is_safe': is_safe,
                'score': total_score,
                'message': message,
                'unique_chars': unique_chars,
                'has_suspicious_patterns': has_suspicious
            }
            
        except Exception as e:
            return {
                'service': 'pattern_analysis',
                'is_safe': False,
                'score': 0.50,
                'error': str(e),
                'message': f'Pattern error: {str(e)[:50]}'
            }
