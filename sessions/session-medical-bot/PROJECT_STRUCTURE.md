# AI Companion - Project Structure

```
companion-ai/
│
├── README.md                 # Main documentation
├── .gitignore               # Git ignore rules
├── setup.sh                 # Automated setup script
│
├── client/                  # React frontend application
│   ├── public/
│   │   └── index.html       # HTML template
│   │
│   ├── src/
│   │   ├── App.jsx          # Main React component (chat interface + voice)
│   │   ├── App.css          # Styling for the application
│   │   ├── index.js         # React entry point
│   │   └── index.css        # Global styles
│   │
│   └── package.json         # Frontend dependencies
│
└── server/                  # Node.js backend server
    ├── server.js            # Express server + Claude API integration
    ├── package.json         # Backend dependencies
    ├── .env.example         # Environment variables template
    └── .env                 # Your actual API keys (create this)
```

## File Purposes

### Frontend Files

**App.jsx** - Main application logic including:
- Chat interface
- Voice recognition (speech-to-text)
- Text-to-speech
- Message handling
- API communication

**App.css** - Complete styling for:
- Chat bubbles
- Input controls
- Voice button animations
- Responsive design
- Color theme

### Backend Files

**server.js** - Backend server providing:
- REST API endpoint for chat
- Claude API integration
- System prompt for AI personality
- Error handling

### Configuration Files

**.env** - Environment variables:
- `ANTHROPIC_API_KEY` - Your Claude API key
- `PORT` - Server port (default: 3001)

**package.json** (both client and server):
- Dependencies list
- Start scripts
- Project metadata

## Data Flow

```
User speaks/types
    ↓
[Voice Recognition] → Text Input
    ↓
React Frontend (App.jsx)
    ↓
HTTP POST to /api/chat
    ↓
Express Server (server.js)
    ↓
Claude API (Anthropic)
    ↓
Response
    ↓
Express Server
    ↓
React Frontend
    ↓
Display + Text-to-Speech
```

## Key Components Breakdown

### 1. Voice Recognition (App.jsx)
- Uses Web Speech API
- Converts speech to text
- Visual feedback while listening

### 2. Chat Interface (App.jsx)
- Message history display
- User/assistant message differentiation
- Auto-scroll to latest message
- Typing indicator

### 3. API Integration (server.js)
- Claude Sonnet 4 model
- Custom system prompt for empathy
- Conversation history management
- Error handling

### 4. Styling (App.css)
- Gradient background
- Smooth animations
- Message bubbles
- Responsive layout

## Customization Points

### Change AI Personality
Edit `server/server.js` → `SYSTEM_PROMPT` constant

### Modify Colors
Edit `client/src/App.css` → Update color values
- Primary: `#667eea`
- Secondary: `#764ba2`

### Adjust Voice Settings
Edit `client/src/App.jsx` → `speakText` function parameters

### Add Features
- User authentication → Add auth service
- Save conversations → Add database (MongoDB, PostgreSQL)
- Mood tracking → Add new components
- Activity suggestions → Integrate external APIs

## Environment Setup

### Development
```bash
# Terminal 1
cd server && npm run dev

# Terminal 2
cd client && npm start
```

### Production Build
```bash
cd client
npm run build

cd ../server
# Deploy with PM2 or similar
```

## API Endpoints

### POST /api/chat
**Request:**
```json
{
  "message": "How are you?",
  "conversationHistory": [
    { "role": "user", "content": "Hello" },
    { "role": "assistant", "content": "Hi there!" }
  ]
}
```

**Response:**
```json
{
  "response": "I'm doing well, thanks for asking! How about you?",
  "conversationId": "msg_123xyz"
}
```

### GET /api/health
**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-10T10:30:00.000Z"
}
```

## Dependencies

### Frontend
- `react` - UI framework
- `react-dom` - DOM rendering
- `react-scripts` - Build tools

### Backend
- `express` - Web server
- `cors` - Cross-origin support
- `dotenv` - Environment variables
- `nodemon` - Development auto-restart

## Browser Requirements

- Modern browser with ES6+ support
- Microphone access for voice input
- Speaker/audio output for TTS

Best experience: **Google Chrome** (latest version)

## Security Notes

- Never commit `.env` file to git
- Keep API keys private
- Use environment variables for secrets
- Enable CORS only for trusted origins in production
- Consider rate limiting for production

## Performance Tips

- Conversation history limited to last 10 messages
- API responses cached client-side
- Minimal re-renders using React best practices
- Lazy loading for future features

## Testing

To add tests:
```bash
# Client tests
cd client
npm test

# Server tests (add jest first)
cd server
npm install --save-dev jest supertest
npm test
```
