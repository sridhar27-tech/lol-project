#!/bin/bash

echo "🚀 Setting up AI Companion Application..."
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null
then
    echo "❌ Node.js is not installed. Please install Node.js first."
    echo "Download from: https://nodejs.org/"
    exit 1
fi

echo "✅ Node.js found: $(node --version)"
echo ""

# Install server dependencies
echo "📦 Installing server dependencies..."
cd server
npm install
if [ $? -eq 0 ]; then
    echo "✅ Server dependencies installed"
else
    echo "❌ Failed to install server dependencies"
    exit 1
fi
echo ""

# Install client dependencies
echo "📦 Installing client dependencies..."
cd ../client
npm install
if [ $? -eq 0 ]; then
    echo "✅ Client dependencies installed"
else
    echo "❌ Failed to install client dependencies"
    exit 1
fi
echo ""

# Create .env file if it doesn't exist
cd ../server
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "⚠️  IMPORTANT: Edit server/.env and add your Anthropic API key!"
    echo "   Get your key from: https://console.anthropic.com/"
else
    echo "ℹ️  .env file already exists"
fi
echo ""

echo "✨ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit server/.env and add your Anthropic API key"
echo "2. Open two terminal windows:"
echo "   Terminal 1: cd server && npm run dev"
echo "   Terminal 2: cd client && npm start"
echo ""
echo "Happy coding! 🎉"
