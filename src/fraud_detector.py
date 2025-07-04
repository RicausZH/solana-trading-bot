import asyncio
import aiohttp
import logging
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
        Comprehensive token safety analysis using reliable alternatives
        Returns: (is_safe, analysis_report)
        """
        logger.info(f"🔍 Analyzing token safety: {token_address}")
        
        try:
            # Run all analysis methods in parallel
            results = await asyncio.gather(
                self.rugcheck_analysis(token_address),
                self.dexscreener_analysis(token_address),
                self.birdeye_analysis(token_address),
                self.goplus_analysis(token_address),
                self.rpc_analysis(token_address),
                self.pattern_analysis(token_address),
                return_exceptions=True
            )
            
            rugcheck_result, dexscreener_result, birdeye_result, goplus_result, rpc_result, pattern_result = results
            
            # Initialize scores and weights
            weighted_score = 0
            total_weight = 0
            analysis_report = {
                'token_address': token_address,
                'timestamp': asyncio.get_event_loop().time(),
                'checks': {}
            }
            
            # Process RugCheck results (30% weight)
            if isinstance(rugcheck_result, dict) and not isinstance(rugcheck_result, Exception):
                analysis_report['checks']['rugcheck'] = rugcheck_result
                score = rugcheck_result.get('score', 0.30)
                weighted_score += score * 0.30
                total_weight += 0.30
            else:
                logger.warning(f"RugCheck error: {rugcheck_result}")
                analysis_report['checks']['rugcheck'] = {'error': str(rugcheck_result), 'score': 0.30}
                weighted_score += 0.30 * 0.30
                total_weight += 0.30
            
            # Process DexScreener results (25% weight)
            if isinstance(dexscreener_result, dict) and not isinstance(dexscreener_result, Exception):
                analysis_report['checks']['dexscreener'] = dexscreener_result
                score = dexscreener_result.get('score', 0.20)
                weighted_score += score * 0.25
                total_weight += 0.25
            else:
                logger.warning(f"DexScreener error: {dexscreener_result}")
                analysis_report['checks']['dexscreener'] = {'error': str(dexscreener_result), 'score': 0.20}
                weighted_score += 0.20 * 0.25
                total_weight += 0.25
            
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
            
            # Process GoPlus results (15% weight)
            if isinstance(goplus_result, dict) and not isinstance(goplus_result, Exception):
                analysis_report['checks']['goplus'] = goplus_result
                score = goplus_result.get('score', 0.35)
                weighted_score += score * 0.15
                total_weight += 0.15
            else:
                logger.warning(f"GoPlus error: {goplus_result}")
                analysis_report['checks']['goplus'] = {'error': str(goplus_result), 'score': 0.35}
                weighted_score += 0.35 * 0.15
                total_weight += 0.15
            
            # Process RPC analysis results (8% weight)
            if isinstance(rpc_result, dict) and not isinstance(rpc_result, Exception):
                analysis_report['checks']['rpc_analysis'] = rpc_result
                score = rpc_result.get('score', 0.39)
                weighted_score += score * 0.08
                total_weight += 0.08
            else:
                logger.warning(f"RPC analysis error: {rpc_result}")
                analysis_report['checks']['rpc_analysis'] = {'error': str(rpc_result), 'score': 0.39}
                weighted_score += 0.39 * 0.08
                total_weight += 0.08
            
            # Process Pattern analysis results (2% weight)
            if isinstance(pattern_result, dict) and not isinstance(pattern_result, Exception):
                analysis_report['checks']['pattern_analysis'] = pattern_result
                score = pattern_result.get('score', 0.60)
                weighted_score += score * 0.02
                total_weight += 0.02
            else:
                logger.warning(f"Pattern analysis error: {pattern_result}")
                analysis_report['checks']['pattern_analysis'] = {'error': str(pattern_result), 'score': 0.60}
                weighted_score += 0.60 * 0.02
                total_weight += 0.02
            
            # Calculate final safety score
            final_score = weighted_score / total_weight if total_weight > 0 else 0
            is_safe = final_score >= self.config.SAFETY_THRESHOLD
            
            analysis_report['safety_score'] = final_score
            analysis_report['is_safe'] = is_safe
            analysis_report['recommendation'] = 'SAFE' if is_safe else 'RISKY' if final_score >= 0.50 else 'UNSAFE'
            
            # Log detailed results
            logger.info(f"🔒 SAFETY REPORT for {token_address[:8]}:")
            
            # Log individual service scores
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
    
    async def rugcheck_analysis(self, token_address: str) -> Dict:
        """RugCheck.xyz API analysis - FREE and RELIABLE"""
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
                    
                    # Analyze specific risks
                    high_risk_count = sum(1 for risk in risks if risk.get('level') == 'high')
                    medium_risk_count = sum(1 for risk in risks if risk.get('level') == 'medium')
                    
                    # Convert to our scoring system (0-1 scale)
                    if score >= 80 and high_risk_count == 0:
                        normalized_score = 0.85
                        is_safe = True
                    elif score >= 60 and high_risk_count == 0:
                        normalized_score = 0.65
                        is_safe = True
                    elif score >= 40 and high_risk_count <= 1:
                        normalized_score = 0.45
                        is_safe = False
                    else:
                        normalized_score = 0.25
                        is_safe = False
                    
                    risk_summary = f"Score: {score}/100, Risks: {len(risks)}"
                    if high_risk_count > 0:
                        risk_summary += f", High: {high_risk_count}"
                    
                    return {
                        'service': 'rugcheck',
                        'is_safe': is_safe,
                        'score': normalized_score,
                        'risks': risks,
                        'raw_score': score,
                        'high_risk_count': high_risk_count,
                        'medium_risk_count': medium_risk_count,
                        'message': risk_summary
                    }
                elif response.status == 429:
                    return {
                        'service': 'rugcheck',
                        'is_safe': False,
                        'score': 0.30,
                        'error': 'Rate limited - too many requests'
                    }
                else:
                    return {
                        'service': 'rugcheck',
                        'is_safe': False,
                        'score': 0.30,
                        'error': f'API returned status {response.status}'
                    }
                    
        except asyncio.TimeoutError:
            return {
                'service': 'rugcheck',
                'is_safe': False,
                'score': 0.30,
                'error': 'Request timeout'
            }
        except Exception as e:
            return {
                'service': 'rugcheck',
                'is_safe': False,
                'score': 0.30,
                'error': str(e)
            }
    
    async def dexscreener_analysis(self, token_address: str) -> Dict:
        """DexScreener API analysis - FREE and COMPREHENSIVE"""
        try:
            url = f"{self.config.DEXSCREENER_API}/{token_address}"
            
            async with self.session.get(url, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    pairs = data.get('pairs', [])
                    
                    if pairs:
                        # Analyze the best pair (highest liquidity)
                        best_pair = max(pairs, key=lambda p: float(p.get('liquidity', {}).get('usd', 0)))
                        
                        # Extract metrics
                        liquidity_usd = float(best_pair.get('liquidity', {}).get('usd', 0))
                        volume_24h = float(best_pair.get('volume', {}).get('h24', 0))
                        fdv = float(best_pair.get('fdv', 0))
                        price_change_24h = float(best_pair.get('priceChange', {}).get('h24', 0))
                        
                        # Safety criteria
                        has_liquidity = liquidity_usd >= self.config.MIN_LIQUIDITY_USD
                        has_volume = volume_24h >= self.config.MIN_VOLUME_24H
                        has_fdv = fdv > 0
                        reasonable_volatility = abs(price_change_24h) <= 500  # Not more than 500% change
                        
                        # Calculate score
                        score = 0.10  # Base score
                        
                        if has_liquidity:
                            score += 0.30
                        if has_volume:
                            score += 0.25
                        if has_fdv:
                            score += 0.15
                        if reasonable_volatility:
                            score += 0.10
                        if liquidity_usd > 50000:  # Bonus for high liquidity
                            score += 0.10
                        
                        is_safe = has_liquidity and has_volume and has_fdv and reasonable_volatility
                        
                        message = f"Liquidity: ${liquidity_usd:,.0f}, Volume: ${volume_24h:,.0f}"
                        if not reasonable_volatility:
                            message += f", High volatility: {price_change_24h:.1f}%"
                        
                        return {
                            'service': 'dexscreener',
                            'is_safe': is_safe,
                            'score': score,
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
                            'error': 'No trading pairs found'
                        }
                else:
                    return {
                        'service': 'dexscreener',
                        'is_safe': False,
                        'score': 0.15,
                        'error': f'API returned status {response.status}'
                    }
                    
        except asyncio.TimeoutError:
            return {
                'service': 'dexscreener',
                'is_safe': False,
                'score': 0.15,
                'error': 'Request timeout'
            }
        except Exception as e:
            return {
                'service': 'dexscreener',
                'is_safe': False,
                'score': 0.15,
                'error': str(e)
            }
    
    async def birdeye_analysis(self, token_address: str) -> Dict:
        """Birdeye API analysis - PROFESSIONAL GRADE"""
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
                    
                    # Parse Birdeye security data
                    success = data.get('success', False)
                    if success:
                        security_data = data.get('data', {})
                        
                        # Extract security indicators
                        is_honeypot = security_data.get('isHoneypot', False)
                        is_rugpull = security_data.get('isRugpull', False)
                        risk_level = security_data.get('riskLevel', 'unknown').lower()
                        
                        # Calculate safety
                        is_safe = not is_honeypot and not is_rugpull and risk_level in ['low', 'safe']
                        
                        if is_safe:
                            score = 0.80
                        elif risk_level == 'medium':
                            score = 0.50
                        else:
                            score = 0.20
                        
                        message = f"Risk: {risk_level}"
                        if is_honeypot:
                            message += ", Honeypot detected"
                        if is_rugpull:
                            message += ", Rugpull risk"
                        
                        return {
                            'service': 'birdeye',
                            'is_safe': is_safe,
                            'score': score,
                            'is_honeypot': is_honeypot,
                            'is_rugpull': is_rugpull,
                            'risk_level': risk_level,
                            'message': message
                        }
                    else:
                        return {
                            'service': 'birdeye',
                            'is_safe': False,
                            'score': 0.25,
                            'error': 'API returned unsuccessful response'
                        }
                elif response.status == 429:
                    return {
                        'service': 'birdeye',
                        'is_safe': False,
                        'score': 0.25,
                        'error': 'Rate limited'
                    }
                else:
                    return {
                        'service': 'birdeye',
                        'is_safe': False,
                        'score': 0.25,
                        'error': f'API returned status {response.status}'
                    }
                    
        except asyncio.TimeoutError:
            return {
                'service': 'birdeye',
                'is_safe': False,
                'score': 0.25,
                'error': 'Request timeout'
            }
        except Exception as e:
            return {
                'service': 'birdeye',
                'is_safe': False,
                'score': 0.25,
                'error': str(e)
            }
    
    async def goplus_analysis(self, token_address: str) -> Dict:
        """GoPlus API analysis - BACKUP SECURITY CHECK"""
        try:
            url = f"{self.config.GOPLUS_API}/token_security/solana"
            params = {'contract_addresses': token_address}
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with self.session.get(url, params=params, headers=headers, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    token_data = data.get('result', {}).get(token_address, {})
                    
                    if token_data:
                        # Analyze GoPlus security data
                        is_honeypot = token_data.get('is_honeypot', '0') == '1'
                        is_blacklisted = token_data.get('is_blacklisted', '0') == '1'
                        is_whitelisted = token_data.get('is_whitelisted', '0') == '1'
                        can_take_back_ownership = token_data.get('can_take_back_ownership', '0') == '1'
                        
                        # Calculate safety
                        is_safe = not is_honeypot and not is_blacklisted and not can_take_back_ownership
                        
                        if is_safe and is_whitelisted:
                            score = 0.75
                        elif is_safe:
                            score = 0.60
                        else:
                            score = 0.25
                        
                        issues = []
                        if is_honeypot:
                            issues.append("Honeypot")
                        if is_blacklisted:
                            issues.append("Blacklisted")
                        if can_take_back_ownership:
                            issues.append("Owner can take back")
                        
                        message = "Clean" if not issues else f"Issues: {', '.join(issues)}"
                        
                        return {
                            'service': 'goplus',
                            'is_safe': is_safe,
                            'score': score,
                            'is_honeypot': is_honeypot,
                            'is_blacklisted': is_blacklisted,
                            'is_whitelisted': is_whitelisted,
                            'can_take_back_ownership': can_take_back_ownership,
                            'message': message
                        }
                    else:
                        return {
                            'service': 'goplus',
                            'is_safe': False,
                            'score': 0.35,
                            'error': 'Token not found in GoPlus database'
                        }
                else:
                    return {
                        'service': 'goplus',
                        'is_safe': False,
                        'score': 0.35,
                        'error': f'API returned status {response.status}'
                    }
                    
        except asyncio.TimeoutError:
            return {
                'service': 'goplus',
                'is_safe': False,
                'score': 0.35,
                'error': 'Request timeout'
            }
        except Exception as e:
            return {
                'service': 'goplus',
                'is_safe': False,
                'score': 0.35,
                'error': str(e)
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
                    'error': 'Token account not found'
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
            score = 0.20 + (safety_ratio * 0.60)  # Scale from 0.20 to 0.80
            
            message_parts = []
            if issues:
                message_parts.append(f"Issues: {', '.join(issues)}")
            if good_signs:
                message_parts.append(f"Good: {', '.join(good_signs)}")
            
            return {
                'service': 'rpc_analysis',
                'is_safe': is_safe,
                'score': score,
                'message': ' | '.join(message_parts),
                'issues': issues,
                'good_signs': good_signs,
                'safety_ratio': safety_ratio
            }
            
        except Exception as e:
            return {
                'service': 'rpc_analysis',
                'is_safe': False,
                'score': 0.39,
                'error': str(e)
            }
    
    async def pattern_analysis(self, token_address: str) -> Dict:
        """Enhanced pattern analysis for token addresses"""
        try:
            # Address pattern analysis
            score_factors = []
            
            # Check address length (should be 44 characters for Solana)
            if len(token_address) == 44:
                score_factors.append(0.3)  # Correct length
            else:
                score_factors.append(0.0)
            
            # Check character variety
            unique_chars = len(set(token_address))
            if unique_chars >= 25:
                score_factors.append(0.4)  # Excellent variety
            elif unique_chars >= 20:
                score_factors.append(0.3)  # Good variety
            elif unique_chars >= 15:
                score_factors.append(0.2)  # Moderate variety
            else:
                score_factors.append(0.1)  # Poor variety
            
            # Check for suspicious patterns
            suspicious_patterns = ['1111', '0000', 'aaaa', 'zzzz', 'pump', '2222', '3333']
            has_suspicious = any(pattern in token_address.lower() for pattern in suspicious_patterns)
            
            if not has_suspicious:
                score_factors.append(0.2)  # No suspicious patterns
            else:
                score_factors.append(0.0)
            
            # Check case mixing
            has_upper = any(c.isupper() for c in token_address)
            has_lower = any(c.islower() for c in token_address)
            has_digit = any(c.isdigit() for c in token_address)
            
            if has_upper and has_lower and has_digit:
                score_factors.append(0.1)  # Good mixing
            else:
                score_factors.append(0.0)
            
            # Calculate final score
            total_score = sum(score_factors)
            is_safe = total_score >= 0.7
            
            # Create descriptive message
            message_parts = []
            if len(token_address) == 44:
                message_parts.append("Valid length")
            if unique_chars >= 20:
                message_parts.append("Good variety")
            if not has_suspicious:
                message_parts.append("No suspicious patterns")
            
            return {
                'service': 'pattern_analysis',
                'is_safe': is_safe,
                'score': total_score,
                'message': ', '.join(message_parts) if message_parts else 'Basic pattern check',
                'unique_chars': unique_chars,
                'has_suspicious_patterns': has_suspicious
            }
            
        except Exception as e:
            return {
                'service': 'pattern_analysis',
                'is_safe': False,
                'score': 0.30,
                'error': str(e)
            }
