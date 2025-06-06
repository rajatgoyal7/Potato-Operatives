#!/bin/bash

echo "🚀 TravelMate - Treebo Travel Companion"
echo "======================================="
echo ""
echo "✅ Application Status: RUNNING"
echo "🌐 TravelMate Interface: http://localhost:5000"
echo "🔧 Health Check: http://localhost:5000/health"
echo ""
echo "📋 Available Features:"
echo "  • 🔐 User Authentication (Phone-based)"
echo "  • 🏨 Real Booking Search (External API)"
echo "  • 🌍 Multi-language Support (5 languages)"
echo "  • 🍽️ Restaurant Recommendations"
echo "  • 🏛️ Sightseeing Suggestions"
echo "  • 🛍️ Shopping & Nightlife"
echo "  • 🏧 ATM & Essential Services"
echo "  • 🚗 Car/Bike Rentals & Taxi Services"
echo "  • 📅 Personalized Itineraries"
echo "  • 🎁 Travel Packages (Revenue Features)"
echo ""
echo "🔑 API Integration:"
echo "  • External Booking API: ✅ Active"
echo "  • MapMyIndia: ✅ Integrated"
echo "  • User Authentication: ✅ Active"
echo ""
echo "💡 How to use:"
echo "  1. Open http://localhost:5000 in your browser"
echo "  2. Select your preferred language"
echo "  3. Enter your phone number (use 8003268879 for demo)"
echo "  4. Select your booking and explore recommendations"
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
echo "🎉 Enjoy using TravelMate - Your Treebo Travel Companion!"
