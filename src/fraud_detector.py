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
        self.session: Optional[aiohttp.ClientSession] = None
        
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
        try:
            # Run all analysis methods in parallel
            results = await asyncio.gather(
                self._quillcheck_analysis(token_address),
                self._rpc_fraud_analysis(token_address),
                self._pattern_analysis(token_address),
                return_exceptions=True
            )
            
            quill_result, rpc_result, pattern_result = results
            
            # Aggregate results
            safety_score = 0
            total_checks = 0
            analysis_report = {
                'token_address': token_address,
                'timestamp': asyncio.get_event_loop().time(),
                'checks': {}
            }
            
            # QuillCheck results
            if isinstance(quill_result, dict) and not isinstance(quill_result, Exception):
                analysis_report['checks']['quillcheck'] = quill_result
                if quill_result.get('is_safe', False):
                    safety_score += 40  # 40% weight
                total_checks += 40
            
            # RPC analysis results
            if isinstance(rpc_result, dict) and not isinstance(rpc_result, Exception):
                analysis_report['checks']['rpc_analysis'] = rpc_result
                if rpc_result.get('is_safe', False):
                    safety_score += 35  # 35% weight
                total_checks += 35
            
            # Pattern analysis results
            if isinstance(pattern_result, dict) and not isinstance(pattern_result, Exception):
                analysis_report['checks']['pattern_analysis'] = pattern_result
                if pattern_result.get('is_safe', False):
                    safety_score += 25  # 25% weight
                total_checks += 25
            
            # Calculate final safety score
            final_score = (safety_score / total_checks * 100) if total_checks > 0 else 0
            is_safe = final_score >= 70  # 70% threshold for safety
            
            analysis_report['safety_score'] = final_score
            analysis_report['is_safe'] = is_safe
            analysis_report['recommendation'] = 'TRADE' if is_safe else 'SKIP'
            
            logger.info(f"Token {token_address} safety analysis: {final_score:.1f}% - {'SAFE' if is_safe else 'UNSAFE'}")
            
            return is_safe, analysis_report
            
        except Exception as e:
            logger.error(f"Error analyzing token safety for {token_address}: {e}")
            return False, {'error': str(e), 'is_safe': False}
    
    async def _quillcheck_analysis(self, token_address: str) -> Dict:
        """Free QuillCheck API analysis"""
        try:
            url = f"{self.config.QUILLCHECK_API_URL}/scan/{token_address}"
            
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Parse QuillCheck response
                    is_honeypot = data.get('is_honeypot', False)
                    is_rugpull = data.get('is_rugpull', False)
                    risk_level = data.get('risk_level', 'unknown')
                    
                    is_safe = not is_honeypot and not is_rugpull and risk_level.lower() in ['low', 'safe']
                    
                    return {
                        'service': 'quillcheck',
                        'is_safe': is_safe,
                        'is_honeypot': is_honeypot,
                        'is_rugpull': is_rugpull,
                        'risk_level': risk_level,
                        'response_status': response.status
                    }
                else:
                    return {'service': 'quillcheck', 'is_safe': False, 'error': f'HTTP {response.status}'}
                    
        except Exception as e:
            logger.warning(f"QuillCheck analysis failed for {token_address}: {e}")
            return {'service': 'quillcheck', 'is_safe': False, 'error': str(e)}
    
    async def _rpc_fraud_analysis(self, token_address: str) -> Dict:
        """Free RPC-based fraud analysis"""
        try:
            pubkey = Pubkey.from_string(token_address)
            
            # Get token account info
            account_info = await self.solana_client.get_account_info(pubkey)
            
            if not account_info.value:
                return {'service': 'rpc_analysis', 'is_safe': False, 'error': 'Token account not found'}
            
            # Basic safety checks
            checks = {
                'account_exists': True,
                'is_executable': account_info.value.executable,
                'has_data': len(account_info.value.data) > 0,
                'lamports': account_info.value.lamports
            }
            
            # Check mint authority and freeze authority
            try:
                mint_info = await self.solana_client.get_account_info(pubkey)
                if mint_info.value and len(mint_info.value.data) >= 82:
                    # Parse mint data (simplified)
                    data = mint_info.value.data
                    
                    # Check for mint authority (bytes 4-36)
                    mint_authority_option = data[4]
                    has_mint_authority = mint_authority_option == 1
                    
                    # Check for freeze authority (bytes 46-78)
                    freeze_authority_option = data[46] if len(data) > 46 else 0
                    has_freeze_authority = freeze_authority_option == 1
                    
                    checks['has_mint_authority'] = has_mint_authority
                    checks['has_freeze_authority'] = has_freeze_authority
                    
                    # Token is safer if authorities are disabled
                    authority_safe = not has_mint_authority and not has_freeze_authority
                    checks['authority_safe'] = authority_safe
                else:
                    checks['mint_data_parsed'] = False
                    authority_safe = False
                    
            except Exception as e:
                logger.warning(f"Error parsing mint data: {e}")
                authority_safe = False
                checks['mint_parse_error'] = str(e)
            
            # Overall safety assessment
            is_safe = (
                checks['account_exists'] and
                checks['has_data'] and
                not checks.get('has_mint_authority', True) and  # Safer if no mint authority
                not checks.get('has_freeze_authority', True)    # Safer if no freeze authority
            )
            
            return {
                'service': 'rpc_analysis',
                'is_safe': is_safe,
                'checks': checks,
                'authority_disabled': authority_safe
            }
            
        except Exception as e:
            logger.error(f"RPC fraud analysis failed for {token_address}: {e}")
            return {'service': 'rpc_analysis', 'is_safe': False, 'error': str(e)}
    
    async def _pattern_analysis(self, token_address: str) -> Dict:
        """Pattern-based fraud detection"""
        try:
            # Get token metadata for pattern analysis
            metadata = await self._get_token_metadata(token_address)
            
            red_flags = []
            green_flags = []
            
            # Check address patterns
            if token_address.endswith('pump'):
                red_flags.append('pump_address_pattern')
            
            # Check for common scam patterns in metadata
            if metadata:
                name = metadata.get('name', '').lower()
                symbol = metadata.get('symbol', '').lower()
                
                # Red flag patterns
                scam_keywords = ['elon', 'trump', 'moon', 'safe', 'baby', 'doge', 'shib', 'inu']
                if any(keyword in name or keyword in symbol for keyword in scam_keywords):
                    red_flags.append('scam_keyword_detected')
                
                # Green flag patterns
                if len(symbol) <= 8 and symbol.isalpha():
                    green_flags.append('reasonable_symbol')
                
                if len(name) <= 50:
                    green_flags.append('reasonable_name_length')
            
            # Risk assessment
            risk_score = len(red_flags) * 20 - len(green_flags) * 10
            is_safe = risk_score <= 20  # Allow some risk but not too much
            
            return {
                'service': 'pattern_analysis',
                'is_safe': is_safe,
                'risk_score': risk_score,
                'red_flags': red_flags,
                'green_flags': green_flags,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Pattern analysis failed for {token_address}: {e}")
            return {'service': 'pattern_analysis', 'is_safe': False, 'error': str(e)}
    
    async def _get_token_metadata(self, token_address: str) -> Dict:
        """Get token metadata (simplified)"""
        try:
            # This is a simplified metadata fetch
            # In production, you might want to parse the actual metadata account
            return {
                'name': f'Token_{token_address[:8]}',
                'symbol': f'TK{token_address[:4]}',
                'address': token_address
            }
        except:
            return {}
