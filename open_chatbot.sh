#!/bin/bash

echo "🚀 Treebo Chatbot is now running!"
echo "=================================="
echo ""
echo "✅ Application Status: RUNNING"
echo "🌐 Web Interface: http://localhost:5000"
echo "📱 Mobile Interface: http://localhost:5000/mobile"
echo "🔧 Health Check: http://localhost:5000/health"
echo ""
echo "📋 Available Features:"
echo "  • Booking Event Simulation"
echo "  • MapMyIndia API Integration"
echo "  • Multi-language Support"
echo "  • Restaurant Recommendations"
echo "  • Sightseeing Suggestions"
echo "  • Shopping & Nightlife"
echo ""
echo "🔑 API Keys Status:"
echo "  • MapMyIndia: Test keys (get real keys from https://www.mapmyindia.com/api/)"
echo "  • Google Places: Test keys (fallback)"
echo "  • OpenAI: Test keys (for enhanced responses)"
echo ""
echo "💡 To test the system:"
echo "  1. Open http://localhost:5000 in your browser"
echo "  2. Click 'Sample Booking 1' or 'Sample Booking 2'"
echo "  3. Start chatting with the bot"
echo ""
echo "🛑 To stop the server: Press Ctrl+C in the terminal where it's running"
echo ""

# Try to open the browser automatically
if command -v open &> /dev/null; then
    echo "🌐 Opening web browser..."
    open http://localhost:5000
elif command -v xdg-open &> /dev/null; then
    echo "🌐 Opening web browser..."
    xdg-open http://localhost:5000
else
    echo "📝 Please manually open: http://localhost:5000"
fi

echo ""
echo "🎉 Enjoy testing the Treebo Chatbot!"
