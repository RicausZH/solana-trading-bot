import asyncio
import aiohttp
import logging
from typing import Dict, List, Tuple
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
        Comprehensive token safety analysis using free methods
        Returns: (is_safe, analysis_report)
        """
        logger.info(f"🔍 Analyzing token safety: {token_address}")
        
        try:
            # Run all analysis methods in parallel
            results = await asyncio.gather(
                self.quillcheck_analysis(token_address),
                self.goplus_analysis(token_address),
                self.rpc_analysis(token_address),
                self.pattern_analysis(token_address),
                return_exceptions=True
            )
            
            quill_result, goplus_result, rpc_result, pattern_result = results
            
            # Initialize scores
            safety_score = 0
            total_checks = 0
            analysis_report = {
                'token_address': token_address,
                'timestamp': asyncio.get_event_loop().time(),
                'checks': {}
            }
            
            # Process QuillCheck results
            if isinstance(quill_result, dict) and not isinstance(quill_result, Exception):
                analysis_report['checks']['quillcheck'] = quill_result
                if quill_result.get('is_safe', False):
                    safety_score += 40  # 40% weight
                total_checks += 40
            else:
                logger.warning(f"QuillCheck error: {quill_result}")
                analysis_report['checks']['quillcheck'] = {'error': str(quill_result), 'score': 0.30}
                safety_score += 12  # Default low score (30% of 40)
                total_checks += 40
            
            # Process GoPlus results
            if isinstance(goplus_result, dict) and not isinstance(goplus_result, Exception):
                analysis_report['checks']['goplus'] = goplus_result
                if goplus_result.get('is_safe', False):
                    safety_score += 25  # 25% weight
                total_checks += 25
            else:
                logger.warning(f"GoPlus error: {goplus_result}")
                analysis_report['checks']['goplus'] = {'error': str(goplus_result), 'score': 0.35}
                safety_score += 9  # Default low score (35% of 25)
                total_checks += 25
            
            # Process RPC analysis results
            if isinstance(rpc_result, dict) and not isinstance(rpc_result, Exception):
                analysis_report['checks']['rpc_analysis'] = rpc_result
                if rpc_result.get('is_safe', False):
                    safety_score += 20  # 20% weight
                total_checks += 20
            else:
                logger.warning(f"RPC analysis error: {rpc_result}")
                analysis_report['checks']['rpc_analysis'] = {'error': str(rpc_result), 'score': 0.39}
                safety_score += 8  # Default low score (39% of 20)
                total_checks += 20
            
            # Process Pattern analysis results
            if isinstance(pattern_result, dict) and not isinstance(pattern_result, Exception):
                analysis_report['checks']['pattern_analysis'] = pattern_result
                if pattern_result.get('is_safe', False):
                    safety_score += 15  # 15% weight
                total_checks += 15
            else:
                logger.warning(f"Pattern analysis error: {pattern_result}")
                analysis_report['checks']['pattern_analysis'] = {'error': str(pattern_result), 'score': 0.60}
                safety_score += 9  # Default score (60% of 15)
                total_checks += 15
            
            # Calculate final safety score
            final_score = (safety_score / total_checks) if total_checks > 0 else 0
            is_safe = final_score >= 0.70  # 70% threshold for safety
            
            analysis_report['safety_score'] = final_score
            analysis_report['is_safe'] = is_safe
            analysis_report['recommendation'] = 'TRADE' if is_safe else 'RISKY' if final_score >= 0.50 else 'UNSAFE'
            
            logger.info(f"🔒 SAFETY REPORT for {token_address[:8]}:")
            
            # Log individual scores
            if 'quillcheck' in analysis_report['checks']:
                qc_score = analysis_report['checks']['quillcheck'].get('score', 0.30)
                qc_msg = analysis_report['checks']['quillcheck'].get('error', 'OK')
                logger.info(f"   QuillCheck: {qc_score:.2f} - {qc_msg}")
            
            if 'rpc_analysis' in analysis_report['checks']:
                rpc_score = analysis_report['checks']['rpc_analysis'].get('score', 0.39)
                rpc_msg = analysis_report['checks']['rpc_analysis'].get('message', 'Analysis complete')
                logger.info(f"   RPC Check:  {rpc_score:.2f} - {rpc_msg}")
            
            if 'pattern_analysis' in analysis_report['checks']:
                pat_score = analysis_report['checks']['pattern_analysis'].get('score', 0.60)
                pat_msg = analysis_report['checks']['pattern_analysis'].get('message', 'Pattern analysis complete')
                logger.info(f"   Pattern:    {pat_score:.2f} - {pat_msg}")
            
            logger.info(f"   FINAL:      {final_score:.2f} ({'✓ SAFE' if is_safe else '⚠️ RISKY' if final_score >= 0.50 else '❌ UNSAFE'})")
            
            return is_safe, analysis_report
            
        except Exception as e:
            logger.error(f"Error analyzing token safety for {token_address}: {e}")
            return False, {'error': str(e), 'is_safe': False}
    
    async def quillcheck_analysis(self, token_address: str) -> Dict:
        """Enhanced QuillCheck API analysis with multiple endpoints"""
        
        # Try multiple potential endpoints
        endpoints = [
            f"{self.config.QUILLCHECK_API}/tokens/solana/{token_address}",
            f"{self.config.QUILLCHECK_API}/scan/{token_address}",
            f"{self.config.QUILLCHECK_API}/v1/tokens/solana/{token_address}",
            f"https://check.quillai.network/api/v1/tokens/solana/{token_address}",
            f"https://check.quillai.network/api/scan/{token_address}"
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        for url in endpoints:
            try:
                async with self.session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Parse QuillCheck response
                        is_honeypot = data.get('is_honeypot', False)
                        is_rugpull = data.get('is_rugpull', False)
                        risk_level = data.get('risk_level', 'unknown').lower()
                        
                        # Calculate safety score
                        is_safe = not is_honeypot and not is_rugpull and risk_level in ['low', 'safe']
                        score = 0.85 if is_safe else 0.30
                        
                        return {
                            'service': 'quillcheck',
                            'is_safe': is_safe,
                            'score': score,
                            'is_honeypot': is_honeypot,
                            'is_rugpull': is_rugpull,
                            'risk_level': risk_level,
                            'endpoint_used': url
                        }
                    elif response.status == 429:
                        logger.warning(f"QuillCheck rate limited on {url}")
                        continue
                    else:
                        logger.warning(f"QuillCheck API error {response.status} on {url}")
                        continue
                        
            except asyncio.TimeoutError:
                logger.warning(f"QuillCheck timeout on {url}")
                continue
            except Exception as e:
                logger.warning(f"QuillCheck error on {url}: {e}")
                continue
        
        # All endpoints failed
        return {
            'service': 'quillcheck',
            'is_safe': False,
            'score': 0.30,
            'error': 'Cannot connect to host api.quillai.network:443 ssl',
            'message': 'All QuillCheck endpoints failed'
        }
    
    async def goplus_analysis(self, token_address: str) -> Dict:
        """Enhanced GoPlus API analysis"""
        try:
            url = f"{self.config.GOPLUS_API}/token_security/solana"
            params = {'contract_addresses': token_address}
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with self.session.get(url, params=params, headers=headers, timeout=10) as response:
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
                        score = 0.80 if is_safe else 0.35
                        
                        return {
                            'service': 'goplus',
                            'is_safe': is_safe,
                            'score': score,
                            'is_honeypot': is_honeypot,
                            'is_blacklisted': is_blacklisted,
                            'is_whitelisted': is_whitelisted,
                            'can_take_back_ownership': can_take_back_ownership,
                            'raw_data': token_data
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
                issues.append("No account data")
            else:
                good_signs.append("Has account data")
            
            # Check account owner (should be Token Program)
            token_program = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            if str(account_info.owner) != token_program:
                issues.append("Not owned by Token Program")
            else:
                good_signs.append("Owned by Token Program")
            
            # Check lamports (rent)
            if account_info.lamports < 1000000:  # Less than 0.001 SOL
                issues.append("Low rent balance")
            else:
                good_signs.append("Adequate rent balance")
            
            # Score based on analysis
            total_factors = len(issues) + len(good_signs)
            safety_ratio = len(good_signs) / total_factors if total_factors > 0 else 0
            
            is_safe = safety_ratio >= 0.7 and len(issues) <= 1
            score = 0.20 + (safety_ratio * 0.6)  # Scale from 0.20 to 0.80
            
            message_parts = []
            if issues:
                message_parts.append(f"Issues: {', '.join(issues)} ❌")
            if good_signs:
                message_parts.append(f"Good: {', '.join(good_signs)} ✓")
            
            return {
                'service': 'rpc_analysis',
                'is_safe': is_safe,
                'score': score,
                'message': ' '.join(message_parts),
                'issues': issues,
                'good_signs': good_signs,
                'safety_ratio': safety_ratio
            }
            
        except Exception as e:
            return {
                'service': 'rpc_analysis',
                'is_safe': False,
                'score': 0.39,
                'error': str(e),
                'message': f"RPC analysis failed: {str(e)}"
            }
    
    async def pattern_analysis(self, token_address: str) -> Dict:
        """Enhanced pattern analysis for token addresses"""
        try:
            # Address pattern analysis
            score_factors = []
            
            # Check address length (should be 44 characters for Solana)
            if len(token_address) == 44:
                score_factors.append(0.2)  # Correct length
            else:
                score_factors.append(0.0)
            
            # Check character variety (good addresses have mixed chars)
            unique_chars = len(set(token_address))
            if unique_chars >= 20:
                score_factors.append(0.3)  # Good variety
            elif unique_chars >= 15:
                score_factors.append(0.2)  # Moderate variety
            else:
                score_factors.append(0.1)  # Poor variety
            
            # Check for suspicious patterns
            suspicious_patterns = ['1111', '0000', 'aaaa', 'zzzz', 'pump']
            has_suspicious = any(pattern in token_address.lower() for pattern in suspicious_patterns)
            
            if not has_suspicious:
                score_factors.append(0.2)  # No suspicious patterns
            else:
                score_factors.append(0.0)
            
            # Check if starts with number (common for good addresses)
            if token_address[0].isdigit():
                score_factors.append(0.15)  # Starts with number
            else:
                score_factors.append(0.05)
            
            # Check case mixing (good addresses often mix cases)
            has_upper = any(c.isupper() for c in token_address)
            has_lower = any(c.islower() for c in token_address)
            has_digit = any(c.isdigit() for c in token_address)
            
            if has_upper and has_lower and has_digit:
                score_factors.append(0.15)  # Good mixing
            else:
                score_factors.append(0.05)
            
            # Calculate final score
            total_score = sum(score_factors)
            is_safe = total_score >= 0.65
            
            # Create descriptive message
            message_parts = []
            if len(token_address) == 44:
                message_parts.append("Valid address")
            if unique_chars >= 20:
                message_parts.append("Good char variety")
            if token_address[0].isdigit():
                message_parts.append("Starts with number")
            if not has_suspicious:
                message_parts.append("No suspicious patterns")
            
            return {
                'service': 'pattern_analysis',
                'is_safe': is_safe,
                'score': total_score,
                'message': ', '.join(message_parts) if message_parts else 'Basic pattern analysis',
                'unique_chars': unique_chars,
                'has_suspicious_patterns': has_suspicious,
                'score_breakdown': {
                    'length_check': score_factors[0],
                    'char_variety': score_factors[1],
                    'suspicious_patterns': score_factors[2],
                    'starts_with_number': score_factors[3],
                    'case_mixing': score_factors[4]
                }
            }
            
        except Exception as e:
            return {
                'service': 'pattern_analysis',
                'is_safe': False,
                'score': 0.30,
                'error': str(e),
                'message': f"Pattern analysis failed: {str(e)}"
            }
