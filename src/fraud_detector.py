# In your fraud_detector.py, add this comment at the top:
# Updated: 2025-07-04 - Removed QuillAI completelyimport asyncio
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
        Comprehensive token safety analysis using reliable alternatives to QuillAI
        Returns: (is_safe, analysis_report)
        """
        logger.info(f"🔍 Analyzing token safety: {token_address}")
        
        try:
            # Run all analysis methods in parallel (NO QuillAI)
            results = await asyncio.gather(
                self.rugcheck_analysis(token_address),      # 35% weight
                self.dexscreener_analysis(token_address),   # 30% weight  
                self.birdeye_analysis(token_address),       # 20% weight
                self.rpc_analysis(token_address),           # 10% weight
                self.pattern_analysis(token_address),       # 5% weight
                return_exceptions=True
            )
            
            rugcheck_result, dexscreener_result, birdeye_result, rpc_result, pattern_result = results
            
            # Initialize weighted scoring
            weighted_score = 0
            total_weight = 0
            analysis_report = {
                'token_address': token_address,
                'timestamp': time.time(),
                'checks': {}
            }
            
            # Process RugCheck results (35% weight)
            if isinstance(rugcheck_result, dict) and not isinstance(rugcheck_result, Exception):
                analysis_report['checks']['rugcheck'] = rugcheck_result
                score = rugcheck_result.get('score', 0.30)
                weighted_score += score * 0.35
                total_weight += 0.35
            else:
                logger.warning(f"RugCheck error: {rugcheck_result}")
                analysis_report['checks']['rugcheck'] = {'error': str(rugcheck_result), 'score': 0.30}
                weighted_score += 0.30 * 0.35
                total_weight += 0.35
            
            # Process DexScreener results (30% weight)
            if isinstance(dexscreener_result, dict) and not isinstance(dexscreener_result, Exception):
                analysis_report['checks']['dexscreener'] = dexscreener_result
                score = dexscreener_result.get('score', 0.20)
                weighted_score += score * 0.30
                total_weight += 0.30
            else:
                logger.warning(f"DexScreener error: {dexscreener_result}")
                analysis_report['checks']['dexscreener'] = {'error': str(dexscreener_result), 'score': 0.20}
                weighted_score += 0.20 * 0.30
                total_weight += 0.30
            
            # Process Birdeye results (20% weight)
            if isinstance(birdeye_result, dict) and not isinstance(birdeye_result, Exception):
                analysis_report['checks']['birdeye'] = birdeye_result
                score = birdeye_result.get('score', 0.25)
                weighted_score += score * 0.20
                total_weight += 0.20
            else:
                logger.warning(f"Birdeye error: {birdeye_result}")
                analysis_report['checks']['birdeye'] = {'error': str(birdeye_result), 'score': 0.25}
                weighted_score += 0.25 * 0.20
                total_weight += 0.20
            
            # Process RPC analysis results (10% weight)
            if isinstance(rpc_result, dict) and not isinstance(rpc_result, Exception):
                analysis_report['checks']['rpc_analysis'] = rpc_result
                score = rpc_result.get('score', 0.40)
                weighted_score += score * 0.10
                total_weight += 0.10
            else:
                logger.warning(f"RPC analysis error: {rpc_result}")
                analysis_report['checks']['rpc_analysis'] = {'error': str(rpc_result), 'score': 0.40}
                weighted_score += 0.40 * 0.10
                total_weight += 0.10
            
            # Process Pattern analysis results (5% weight)
            if isinstance(pattern_result, dict) and not isinstance(pattern_result, Exception):
                analysis_report['checks']['pattern_analysis'] = pattern_result
                score = pattern_result.get('score', 0.60)
                weighted_score += score * 0.05
                total_weight += 0.05
            else:
                logger.warning(f"Pattern analysis error: {pattern_result}")
                analysis_report['checks']['pattern_analysis'] = {'error': str(pattern_result), 'score': 0.60}
                weighted_score += 0.60 * 0.05
                total_weight += 0.05
            
            # Calculate final safety score
            final_score = weighted_score / total_weight if total_weight > 0 else 0
            is_safe = final_score >= self.config.SAFETY_THRESHOLD
            
            analysis_report['safety_score'] = final_score
            analysis_report['is_safe'] = is_safe
            analysis_report['recommendation'] = 'SAFE' if is_safe else 'RISKY' if final_score >= 0.45 else 'UNSAFE'
            
            # Log detailed results with proper service names
            logger.info(f"🔒 SAFETY REPORT for {token_address[:8]}:")
            
            # Log individual service scores
            if 'rugcheck' in analysis_report['checks']:
                data = analysis_report['checks']['rugcheck']
                score = data.get('score', 0.30)
                message = data.get('message', data.get('error', 'Analysis complete'))
                logger.info(f"   RugCheck:   {score:.2f} - {message}")
            
            if 'dexscreener' in analysis_report['checks']:
                data = analysis_report['checks']['dexscreener']
                score = data.get('score', 0.20)
                message = data.get('message', data.get('error', 'Analysis complete'))
                logger.info(f"   DexScreener:{score:.2f} - {message}")
            
            if 'birdeye' in analysis_report['checks']:
                data = analysis_report['checks']['birdeye']
                score = data.get('score', 0.25)
                message = data.get('message', data.get('error', 'Analysis complete'))
                logger.info(f"   Birdeye:    {score:.2f} - {message}")
            
            if 'rpc_analysis' in analysis_report['checks']:
                data = analysis_report['checks']['rpc_analysis']
                score = data.get('score', 0.40)
                message = data.get('message', data.get('error', 'Analysis complete'))
                logger.info(f"   RPC Check:  {score:.2f} - {message}")
            
            if 'pattern_analysis' in analysis_report['checks']:
                data = analysis_report['checks']['pattern_analysis']
                score = data.get('score', 0.60)
                message = data.get('message', data.get('error', 'Analysis complete'))
                logger.info(f"   Pattern:    {score:.2f} - {message}")
            
            logger.info(f"   FINAL:      {final_score:.2f} ({'✓ SAFE' if is_safe else '⚠️ RISKY' if final_score >= 0.45 else '❌ UNSAFE'})")
            
            return is_safe, analysis_report
            
        except Exception as e:
            logger.error(f"Error analyzing token safety for {token_address}: {e}")
            return False, {'error': str(e), 'is_safe': False}
    
    async def rugcheck_analysis(self, token_address: str) -> Dict:
        """RugCheck.xyz API analysis - FREE and RELIABLE (Replaces QuillAI)"""
        try:
            url = f"{self.config.RUGCHECK_API}/{token_address}/report"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            # Add API key if available
            if self.config.RUGCHECK_API_KEY:
                headers['Authorization'] = f'Bearer {self.config.RUGCHECK_API_KEY}'
            
            async with self.session.get(url, headers=headers, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Parse RugCheck response
                    risks = data.get('risks', [])
                    score = data.get('score', 0)  # 0-100 scale
                    
                    # Analyze risk severity
                    critical_risks = [r for r in risks if r.get('level', '').lower() in ['critical', 'high', 'danger']]
                    warning_risks = [r for r in risks if r.get('level', '').lower() in ['warning', 'medium']]
                    
                    # Convert to our scoring system (0-1 scale)
                    if score >= 80 and len(critical_risks) == 0:
                        normalized_score = 0.85
                        is_safe = True
                        status = "✅ Safe"
                    elif score >= 60 and len(critical_risks) == 0:
                        normalized_score = 0.65
                        is_safe = True
                        status = "⚠️ Caution"
                    elif score >= 40 and len(critical_risks) <= 1:
                        normalized_score = 0.45
                        is_safe = False
                        status = "⚠️ Risky"
                    else:
                        normalized_score = 0.25
                        is_safe = False
                        status = "❌ Unsafe"
                    
                    message = f"{status} - Score: {score}/100"
                    if critical_risks:
                        message += f", Critical: {len(critical_risks)}"
                    if warning_risks:
                        message += f", Warnings: {len(warning_risks)}"
                    
                    return {
                        'service': 'rugcheck',
                        'is_safe': is_safe,
                        'score': normalized_score,
                        'risks': risks,
                        'raw_score': score,
                        'critical_risk_count': len(critical_risks),
                        'warning_risk_count': len(warning_risks),
                        'message': message
                    }
                elif response.status == 429:
                    return {
                        'service': 'rugcheck',
                        'is_safe': False,
                        'score': 0.30,
                        'error': 'Rate limited',
                        'message': 'RugCheck rate limited'
                    }
                else:
                    return {
                        'service': 'rugcheck',
                        'is_safe': False,
                        'score': 0.30,
                        'error': f'API returned status {response.status}',
                        'message': f'RugCheck API error: {response.status}'
                    }
                    
        except asyncio.TimeoutError:
            return {
                'service': 'rugcheck',
                'is_safe': False,
                'score': 0.30,
                'error': 'Request timeout',
                'message': 'RugCheck timeout'
            }
        except Exception as e:
            return {
                'service': 'rugcheck',
                'is_safe': False,
                'score': 0.30,
                'error': str(e),
                'message': f'RugCheck error: {str(e)[:50]}'
            }
    
    async def dexscreener_analysis(self, token_address: str) -> Dict:
        """DexScreener API analysis - FREE Market Data Analysis"""
        try:
            url = f"{self.config.DEXSCREENER_API}/{token_address}"
            
            async with self.session.get(url, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    pairs = data.get('pairs', [])
                    
                    if pairs and len(pairs) > 0:
                        # Find the pair with highest liquidity
                        best_pair = max(pairs, key=lambda p: float(p.get('liquidity', {}).get('usd', 0)))
                        
                        # Extract key metrics
                        liquidity_usd = float(best_pair.get('liquidity', {}).get('usd', 0))
                        volume_24h = float(best_pair.get('volume', {}).get('h24', 0))
                        fdv = float(best_pair.get('fdv', 0))
                        price_change_24h = float(best_pair.get('priceChange', {}).get('h24', 0))
                        
                        # Evaluate safety criteria
                        has_good_liquidity = liquidity_usd >= self.config.MIN_LIQUIDITY_USD
                        has_good_volume = volume_24h >= self.config.MIN_VOLUME_24H
                        has_fdv = fdv > 0
                        reasonable_volatility = abs(price_change_24h) <= 300  # Not extremely volatile
                        
                        # Calculate score based on market health
                        score = 0.15  # Base score
                        
                        if has_good_liquidity:
                            score += 0.35  # Strong weight for liquidity
                        elif liquidity_usd >= 1000:  # Minimum acceptable
                            score += 0.20
                        
                        if has_good_volume:
                            score += 0.25  # Good volume
                        elif volume_24h >= 100:  # Some activity
                            score += 0.10
                        
                        if has_fdv:
                            score += 0.15  # Has market cap
                        
                        if reasonable_volatility:
                            score += 0.10  # Not too volatile
                        
                        # Bonus for very high liquidity
                        if liquidity_usd > 50000:
                            score += 0.05
                        
                        is_safe = has_good_liquidity and has_good_volume and reasonable_volatility
                        
                        # Create descriptive message
                        message = f"Liq: ${liquidity_usd:,.0f}, Vol: ${volume_24h:,.0f}"
                        if price_change_24h != 0:
                            message += f", 24h: {price_change_24h:+.1f}%"
                        if not reasonable_volatility:
                            message += " ⚠️ High volatility"
                        if not has_good_liquidity:
                            message += " ⚠️ Low liquidity"
                        
                        return {
                            'service': 'dexscreener',
                            'is_safe': is_safe,
                            'score': min(score, 1.0),  # Cap at 1.0
                            'liquidity_usd': liquidity_usd,
                            'volume_24h': volume_24h,
                            'fdv': fdv,
                            'price_change_24h': price_change_24h,
                            'pair_count': len(pairs),
                            'has_good_liquidity': has_good_liquidity,
                            'has_good_volume': has_good_volume,
                            'message': message
                        }
                    else:
                        return {
                            'service': 'dexscreener',
                            'is_safe': False,
                            'score': 0.10,
                            'error': 'No trading pairs found',
                            'message': 'No trading pairs found'
                        }
                else:
                    return {
                        'service': 'dexscreener',
                        'is_safe': False,
                        'score': 0.10,
                        'error': f'API returned status {response.status}',
                        'message': f'DexScreener API error: {response.status}'
                    }
                    
        except asyncio.TimeoutError:
            return {
                'service': 'dexscreener',
                'is_safe': False,
                'score': 0.10,
                'error': 'Request timeout',
                'message': 'DexScreener timeout'
            }
        except Exception as e:
            return {
                'service': 'dexscreener',
                'is_safe': False,
                'score': 0.10,
                'error': str(e),
                'message': f'DexScreener error: {str(e)[:50]}'
            }
    
    async def birdeye_analysis(self, token_address: str) -> Dict:
        """Birdeye API analysis - Professional Security Analysis"""
        try:
            url = f"{self.config.BIRDEYE_API}?address={token_address}"
            headers = {
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Add API key if available
            if self.config.BIRDEYE_API_KEY:
                headers['X-API-KEY'] = self.config.BIRDEYE_API_KEY
            
            async with self.session.get(url, headers=headers, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Check if API returned success
                    if data.get('success', False):
                        security_data = data.get('data', {})
                        
                        # Extract security indicators
                        is_honeypot = security_data.get('isHoneypot', False)
                        is_rugpull = security_data.get('isRugpull', False)
                        risk_level = security_data.get('riskLevel', 'unknown').lower()
                        
                        # Determine safety and score
                        issues = []
                        if is_honeypot:
                            issues.append("Honeypot")
                        if is_rugpull:
                            issues.append("Rugpull risk")
                        
                        if not issues and risk_level in ['low', 'safe']:
                            is_safe = True
                            score = 0.80
                            message = "✅ Security checks passed"
                        elif not issues and risk_level == 'medium':
                            is_safe = False
                            score = 0.50
                            message = "⚠️ Medium risk level"
                        elif issues:
                            is_safe = False
                            score = 0.20
                            message = f"❌ {', '.join(issues)}"
                        else:
                            is_safe = False
                            score = 0.30
                            message = f"⚠️ Risk level: {risk_level}"
                        
                        return {
                            'service': 'birdeye',
                            'is_safe': is_safe,
                            'score': score,
                            'is_honeypot': is_honeypot,
                            'is_rugpull': is_rugpull,
                            'risk_level': risk_level,
                            'issues': issues,
                            'message': message
                        }
                    else:
                        return {
                            'service': 'birdeye',
                            'is_safe': False,
                            'score': 0.25,
                            'error': 'API returned unsuccessful response',
                            'message': 'Birdeye API unsuccessful'
                        }
                elif response.status == 429:
                    return {
                        'service': 'birdeye',
                        'is_safe': False,
                        'score': 0.25,
                        'error': 'Rate limited',
                        'message': 'Birdeye rate limited'
                    }
                else:
                    return {
                        'service': 'birdeye',
                        'is_safe': False,
                        'score': 0.25,
                        'error': f'API returned status {response.status}',
                        'message': f'Birdeye API error: {response.status}'
                    }
                    
        except asyncio.TimeoutError:
            return {
                'service': 'birdeye',
                'is_safe': False,
                'score': 0.25,
                'error': 'Request timeout',
                'message': 'Birdeye timeout'
            }
        except Exception as e:
            return {
                'service': 'birdeye',
                'is_safe': False,
                'score': 0.25,
                'error': str(e),
                'message': f'Birdeye error: {str(e)[:50]}'
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
            
            # Analyze account characteristics
            issues = []
            good_signs = []
            
            # Check account data presence
            if account_info.data is None or len(account_info.data) == 0:
                issues.append("No metadata")
            else:
                good_signs.append("Has metadata")
            
            # Verify token program ownership
            token_program = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            if str(account_info.owner) != token_program:
                issues.append("Non-standard owner")
            else:
                good_signs.append("Standard token program")
            
            # Check rent-exempt status
            if account_info.lamports < 1000000:  # Less than 0.001 SOL
                issues.append("Insufficient rent")
            else:
                good_signs.append("Rent-exempt")
            
            # Calculate safety score
            total_factors = len(issues) + len(good_signs)
            if total_factors > 0:
                safety_ratio = len(good_signs) / total_factors
                is_safe = safety_ratio >= 0.66 and len(issues) <= 1
                score = 0.20 + (safety_ratio * 0.60)  # Scale from 0.20 to 0.80
            else:
                is_safe = False
                score = 0.20
                safety_ratio = 0
            
            # Create status message
            status_parts = []
            if issues:
                status_parts.append(f"Issues: {', '.join(issues)} ❌")
            if good_signs:
                status_parts.append(f"Good: {', '.join(good_signs)} ✓")
            
            message = ' | '.join(status_parts) if status_parts else 'Basic RPC analysis'
            
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
        """Pattern analysis for Solana token addresses"""
        try:
            # Validate address structure
            score_components = []
            
            # Length check (Solana addresses are 44 characters)
            if len(token_address) == 44:
                score_components.append(0.3)
                length_ok = True
            else:
                score_components.append(0.0)
                length_ok = False
            
            # Character diversity analysis
            unique_chars = len(set(token_address))
            if unique_chars >= 25:
                score_components.append(0.4)  # Excellent diversity
                diversity_level = "excellent"
            elif unique_chars >= 20:
                score_components.append(0.3)  # Good diversity
                diversity_level = "good"
            elif unique_chars >= 15:
                score_components.append(0.2)  # Moderate diversity
                diversity_level = "moderate"
            else:
                score_components.append(0.1)  # Poor diversity
                diversity_level = "poor"
            
            # Suspicious pattern detection
            suspicious_patterns = ['1111', '0000', 'aaaa', 'zzzz', 'pump', '2222', '3333', '4444']
            has_suspicious = any(pattern in token_address.lower() for pattern in suspicious_patterns)
            
            if not has_suspicious:
                score_components.append(0.2)
            else:
                score_components.append(0.0)
            
            # Character type mixing
            has_upper = any(c.isupper() for c in token_address)
            has_lower = any(c.islower() for c in token_address)
            has_digit = any(c.isdigit() for c in token_address)
            
            if has_upper and has_lower and has_digit:
                score_components.append(0.1)
            else:
                score_components.append(0.0)
            
            # Calculate final score
            total_score = sum(score_components)
            is_safe = total_score >= 0.7
            
            # Build descriptive message
            message_parts = []
            if length_ok:
                message_parts.append("Valid length")
            if diversity_level in ["good", "excellent"]:
                message_parts.append(f"{diversity_level.title()} char diversity")
            if not has_suspicious:
                message_parts.append("No suspicious patterns")
            if has_upper and has_lower and has_digit:
                message_parts.append("Good char mixing")
            
            message = ', '.join(message_parts) if message_parts else 'Basic pattern check'
            
            return {
                'service': 'pattern_analysis',
                'is_safe': is_safe,
                'score': total_score,
                'message': message,
                'unique_chars': unique_chars,
                'diversity_level': diversity_level,
                'has_suspicious_patterns': has_suspicious,
                'length_valid': length_ok
            }
            
        except Exception as e:
            return {
                'service': 'pattern_analysis',
                'is_safe': False,
                'score': 0.50,
                'error': str(e),
                'message': f'Pattern analysis error: {str(e)[:30]}'
            }
