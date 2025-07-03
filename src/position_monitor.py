import asyncio
import logging
from typing import Dict, List
from jupiter_trader import JupiterTrader
from config import Config

logger = logging.getLogger(__name__)

class PositionMonitor:
    def __init__(self, config: Config, trader: JupiterTrader):
        self.config = config
        self.trader = trader
        self.monitoring = False
        
    async def start_monitoring(self):
        """Start monitoring active positions for profit targets"""
        self.monitoring = True
        logger.info("Position monitoring started")
        
        while self.monitoring:
            try:
                await self._check_positions()
                await asyncio.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logger.error(f"Error in position monitoring: {e}")
                await asyncio.sleep(30)  # Wait longer on error
    
    def stop_monitoring(self):
        """Stop position monitoring"""
        self.monitoring = False
        logger.info("Position monitoring stopped")
    
    async def _check_positions(self):
        """Check all positions for profit targets"""
        if not self.trader.active_positions:
            return
        
        try:
            # Get positions that hit profit targets
            profitable_positions = await self.trader.check_profit_targets()
            
            for profit_data in profitable_positions:
                position = profit_data['position']
                current_value = profit_data['current_value']
                profit_pct = profit_data['profit_percentage']
                
                logger.info(f"Profit target hit for {position['token_address']}: {profit_pct:.2f}%")
                
                # Execute sell order
                sell_result = await self.trader.execute_sell(position)
                
                if sell_result[0]:  # Success
                    sell_info = sell_result[1]
                    logger.info(f"Position closed successfully: ${sell_info['profit_usdc']:.2f} profit")
                    
                    # Log trade completion
                    await self._log_completed_trade(sell_info)
                else:
                    logger.error(f"Failed to sell position: {sell_result[1]}")
                    
        except Exception as e:
            logger.error(f"Error checking positions: {e}")
    
    async def _log_completed_trade(self, sell_info: Dict):
        """Log completed trade information"""
        try:
            trade_summary = {
                'token': sell_info['token_address'],
                'profit_usd': sell_info['profit_usdc'],
                'profit_percentage': sell_info['profit_percentage'],
                'buy_tx': sell_info['original_position']['transaction_id'],
                'sell_tx': sell_info['transaction_id'],
                'timestamp': sell_info['timestamp']
            }
            
            logger.info(f"Trade completed: {trade_summary}")
            
        except Exception as e:
            logger.error(f"Error logging trade: {e}")
