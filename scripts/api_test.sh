# TradeMemory Protocol — API Test Commands

# Start the server:
#   HOST=0.0.0.0 tradememory-api

# Health check
#curl http://localhost:8000/health

# Record a trade decision
#curl -X POST http://localhost:8000/trade/record_decision \
#  -H "Content-Type: application/json" \
#  -d '{
#    "trade_id": "test-trade-001",
#    "symbol": "EURUSD",
#    "direction": "long",
#    "lot_size": 0.5,
#    "strategy": "breakout",
#    "confidence": 0.8,
#    "reasoning": "Breakout above resistance with volume confirmation",
#    "market_context": {"price": 1.0850, "rsi": 65, "volatility": "medium", "trend": "bullish"}
#  }'

# Query trade history
#curl -X POST http://localhost:8000/trade/query_history \
#  -H "Content-Type: application/json" \
#  -d '{"symbol": "EURUSD", "limit": 10}'

# Get behavioral profile
#curl http://localhost:8000/owm/behavioral

# Run daily reflection
curl -X POST http://localhost:8000/reflect/run_daily \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-session"}'
