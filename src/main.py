import asyncio
import logging
import sys
from typing import Optional
from config import Config
from token_scanner import TokenScanner
from fraud_detector import FraudDetector
from jupiter_trader import JupiterTrader
from position_monitor import PositionMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('trading_bot.log')
    ]
)

logger = logging.getLogger(__name__)

class SolanaTradingBot:
    def __init__(self):
        self.config = Config()
        self.running = False
        self.scanner: Optional[TokenScanner] = None
        self.fraud_detector: Optional[FraudDetector] = None
        self.trader: Optional[JupiterTrader] = None
        self.monitor: Optional[PositionMonitor] = None
        
    async def start(self):
        """Start the trading bot"""
        try:
            logger.info("Starting Solana Trading Bot...")
            
            # Initialize components
            self.scanner = TokenScanner(self.config)
            self.fraud_detector = FraudDetector(self.config)
            self.trader = JupiterTrader(self.config)
            self.monitor = PositionMonitor(self.config, self.trader)
            
            # Check initial wallet balance
            usdc_balance = await self.trader.get_wallet_balance(self.config.USDC_MINT)
            sol_balance = await self.trader.get_wallet_balance()
            
            logger.info(f"Initial balances - USDC: ${usdc_balance:.2f}, SOL: {sol_balance:.4f}")
            
            if usdc_balance < self.config.TRADE_AMOUNT:
                logger.error(f"Insufficient USDC balance: ${usdc_balance:.2f} < ${self.config.TRADE_AMOUNT}")
                return
            
            # Start monitoring in background
            monitor_task = asyncio.create_task(self.monitor.start_monitoring())
            
            # Start main trading loop
            self.running = True
            await self._main_trading_loop()
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
        finally:
            await self._cleanup()
    
    async def _main_trading_loop(self):
        """Main trading loop"""
        logger.info("Starting main trading loop...")
        
        async with self.scanner, self.fraud_detector:
            while self.running:
                try:
                    # Check if we can make new trades
                    if len(self.trader.active_positions) >= self.config.MAX_POSITIONS:
                        logger.info(f"Max positions ({self.config.MAX_POSITIONS}) reached, waiting...")
                        await asyncio.sleep(30)
                        continue
                    
                    # Check wallet balance
                    usdc_balance = await self.trader.get_wallet_balance(self.config.USDC_MINT)
                    if usdc_balance < self.config.TRADE_AMOUNT:
                        logger.warning(f"Insufficient balance for new trades: ${usdc_balance:.2f}")
                        await asyncio.sleep(60)
                        continue
                    
                    # Discover new tokens
                    logger.info("Scanning for new tokens...")
                    new_tokens = await self.scanner.scan_new_tokens()
                    
                    if not new_tokens:
                        logger.info("No new tokens found, waiting...")
                        await asyncio.sleep(30)
                        continue
                    
                    # Analyze each token
                    for token_info in new_tokens[:5]:  # Limit to 5 tokens per cycle
                        if not self.running:
                            break
                            
                        await self._analyze_and_trade_token(token_info)
                        await asyncio.sleep(2)  # Brief pause between analyses
                    
                    # Wait before next scan
                    await asyncio.sleep(20)
                    
                except Exception as e:
                    logger.error(f"Error in main trading loop: {e}")
                    await asyncio.sleep(60)
    
    async def _analyze_and_trade_token(self, token_info: Dict):
        """Analyze a token and execute trade if safe"""
        token_address = token_info['address']
        
        try:
            logger.info(f"Analyzing token: {token_address}")
            
            # Skip if already trading this token
            if token_address in self.trader.active_positions:
                return
            
            # Fraud detection analysis
            start_time = asyncio.get_event_loop().time()
            is_safe, analysis = await self.fraud_detector.analyze_token_safety(token_address)
            analysis_time = asyncio.get_event_loop().time() - start_time
            
            logger.info(f"Fraud analysis completed in {analysis_time:.1f}s - Safe: {is_safe}")
            
            if not is_safe:
                logger.info(f"Token {token_address} failed safety check - skipping")
                return
            
            # Execute trade
            logger.info(f"Executing trade for safe token: {token_address}")
            success, trade_info = await self.trader.execute_trade(token_address, self.config.TRADE_AMOUNT)
            
            if success:
                logger.info(f"Trade executed successfully: {trade_info['transaction_id']}")
                logger.info(f"Active positions: {len(self.trader.active_positions)}")
            else:
                logger.warning(f"Trade execution failed: {trade_info.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Error analyzing/trading token {token_address}: {e}")
    
    async def _cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up...")
        self.running = False
        
        if self.monitor:
            self.monitor.stop_monitoring()
    
    def stop(self):
        """Stop the bot"""
        self.running = False

async def main():
    """Main entry point"""
    bot = SolanaTradingBot()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        bot.stop()

if __name__ == "__main__":
    # Use uvloop for better performance if available
    try:
        import uvloop
        uvloop.install()
    except ImportError:
        pass
    
    asyncio.run(main())
