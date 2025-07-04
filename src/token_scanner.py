import asyncio
import aiohttp
import json
import logging
from typing import List, Dict, Optional
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey
from config import Config

logger = logging.getLogger(__name__)

class TokenScanner:
    def __init__(self, config: Config):
        self.config = config
        self.solana_client = AsyncClient(config.SOLANA_RPC_URL)
        self.session: Optional[aiohttp.ClientSession] = None
        self.discovered_tokens = set()
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def scan_new_tokens(self) -> List[Dict]:
        """Discover new tokens using multiple methods"""
        new_tokens = []
        
        try:
            # Method 1: QuickNode Metis API (Primary)
            if self.config.QUICKNODE_HTTP_URL:
                metis_tokens = await self._scan_metis_new_pools()
                new_tokens.extend(metis_tokens)
            
            # Method 2: Raydium Pool Monitoring (Backup)
            raydium_tokens = await self._scan_raydium_pools()
            new_tokens.extend(raydium_tokens)
            
            # Method 3: DexScreener trending
            dexscreener_tokens = await self._scan_dexscreener_trending()
            new_tokens.extend(dexscreener_tokens)
            
            # Remove duplicates
            unique_tokens = self._deduplicate_tokens(new_tokens)
            
            logger.info(f"Discovered {len(unique_tokens)} new tokens")
            return unique_tokens
            
        except Exception as e:
            logger.error(f"Error scanning tokens: {e}")
            return []
    
    async def _scan_metis_new_pools(self) -> List[Dict]:
        """Scan new pools using QuickNode Metis API"""
        try:
            if not self.config.QUICKNODE_HTTP_URL:
                return []
                
            url = f"{self.config.QUICKNODE_HTTP_URL}/new-pools"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    tokens = []
                    for pool in data.get('data', [])[:20]:  # Limit to 20 most recent
                        if pool.get('exchange') in ['raydium', 'pump.fun']:
                            token_info = {
                                'address': pool.get('tokenAddress'),
                                'quote_address': pool.get('quoteAddress', self.config.USDC_MINT),
                                'lp_address': pool.get('lpAddress'),
                                'timestamp': pool.get('timestamp'),
                                'exchange': pool.get('exchange'),
                                'signature': pool.get('lpSignature')
                            }
                            
                            if token_info['address'] and token_info['address'] not in self.discovered_tokens:
                                tokens.append(token_info)
                                self.discovered_tokens.add(token_info['address'])
                    
                    return tokens
                else:
                    logger.warning(f"Metis API returned status {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error scanning Metis API: {e}")
            return []
    
    async def _scan_raydium_pools(self) -> List[Dict]:
        """Scan Raydium pools using direct API"""
        try:
            url = "https://api-v3.raydium.io/pools/info/list"
            params = {
                'poolType': 'Standard',
                'poolSortField': 'created_time',
                'sortType': 'desc',
                'pageSize': 15
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    tokens = []
                    for pool in data.get('data', {}).get('data', []):
                        mint_a = pool.get('mintA', {}).get('address')
                        mint_b = pool.get('mintB', {}).get('address')
                        
                        # Identify the non-SOL/USDC token
                        target_token = None
                        if mint_a not in [self.config.SOL_MINT, self.config.USDC_MINT]:
                            target_token = mint_a
                        elif mint_b not in [self.config.SOL_MINT, self.config.USDC_MINT]:
                            target_token = mint_b
                        
                        if target_token and target_token not in self.discovered_tokens:
                            token_info = {
                                'address': target_token,
                                'quote_address': self.config.USDC_MINT,
                                'lp_address': pool.get('id'),
                                'timestamp': pool.get('created_time'),
                                'exchange': 'raydium',
                                'tvl': pool.get('tvl', 0)
                            }
                            tokens.append(token_info)
                            self.discovered_tokens.add(target_token)
                    
                    return tokens
                else:
                    return []
                    
        except Exception as e:
            logger.error(f"Error scanning Raydium pools: {e}")
            return []
    
    async def _scan_dexscreener_trending(self) -> List[Dict]:
        """Scan DexScreener for trending tokens"""
        try:
            url = "https://api.dexscreener.com/latest/dex/search/?q=solana"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    tokens = []
                    for pair in data.get('pairs', [])[:10]:  # Top 10 trending
                        base_token = pair.get('baseToken', {})
                        quote_token = pair.get('quoteToken', {})
                        
                        base_address = base_token.get('address')
                        quote_address = quote_token.get('address')
                        
                        if (quote_address in [self.config.SOL_MINT, self.config.USDC_MINT] 
                            and base_address 
                            and base_address not in self.discovered_tokens):
                            
                            token_info = {
                                'address': base_address,
                                'quote_address': quote_address,
                                'exchange': 'dexscreener',
                                'timestamp': pair.get('pairCreatedAt'),
                                'volume_24h': pair.get('volume', {}).get('h24', 0),
                                'liquidity': pair.get('liquidity', {}).get('usd', 0)
                            }
                            tokens.append(token_info)
                            self.discovered_tokens.add(base_address)
                    
                    return tokens
                else:
                    return []
                    
        except Exception as e:
            logger.error(f"Error scanning DexScreener: {e}")
            return []
    
    def _deduplicate_tokens(self, tokens: List[Dict]) -> List[Dict]:
        """Remove duplicate tokens by address"""
        seen = set()
        unique_tokens = []
        
        for token in tokens:
            if token['address'] not in seen:
                seen.add(token['address'])
                unique_tokens.append(token)
        
        return unique_tokens
    
    async def get_token_metadata(self, token_address: str) -> Dict:
        """Get token metadata from Solana"""
        try:
            pubkey = Pubkey.from_string(token_address)
            account_info = await self.solana_client.get_account_info(pubkey)
            
            if account_info.value:
                return {
                    'address': token_address,
                    'owner': str(account_info.value.owner),
                    'executable': account_info.value.executable,
                    'lamports': account_info.value.lamports,
                    'data_length': len(account_info.value.data)
                }
            return {}
            
        except Exception as e:
            logger.error(f"Error getting token metadata for {token_address}: {e}")
            return {}
