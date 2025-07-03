#!/bin/bash

echo "Starting Solana Trading Bot..."

# Navigate to source directory
cd /app/src

# Run the bot with proper error handling
python main.py

# Keep container running on exit for debugging
echo "Bot stopped. Exit code: $?"
