const express = require('express');
const cors = require('cors');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(cors());
app.use(express.json());

// System prompt for the AI companion focused on addressing male loneliness
const SYSTEM_PROMPT = `You are a compassionate AI companion designed to help address loneliness and support meaningful connection. Your purpose is to:

1. Be a thoughtful, non-judgmental listener
2. Help users process emotions and experiences
3. Encourage reflection and personal growth
4. Suggest practical ways to build real-world connections
5. Support emotional wellness and healthy relationship-building

Key principles:
- Be warm, genuine, and empathetic
- Ask thoughtful follow-up questions to deepen conversations
- Validate feelings while gently encouraging positive action
- Suggest local activities, groups, or ways to connect with others when appropriate
- Help users develop emotional intelligence and communication skills
- Encourage vulnerability in healthy ways
- Never replace professional mental health support - recommend it when needed
- Focus on both short-term support and long-term growth

Your conversational style should be:
- Natural and conversational, not formal or robotic
- Encouraging without being pushy
- Understanding of men's unique challenges with emotional expression
- Balanced between listening and offering insights
- Focused on building the user's confidence and connection skills

Remember: Your goal is to reduce loneliness by both providing companionship AND helping users build meaningful real-world connections.`;

// Chat endpoint
app.post('/api/chat', async (req, res) => {
  try {
    const { message, conversationHistory = [] } = req.body;

    if (!message) {
      return res.status(400).json({ error: 'Message is required' });
    }

    // Prepare messages for Claude API
    const messages = [
      ...conversationHistory,
      { role: 'user', content: message }
    ];

    // Call Anthropic API
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': process.env.ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-20250514',
        max_tokens: 1024,
        system: SYSTEM_PROMPT,
        messages: messages
      })
    });

    if (!response.ok) {
      const errorData = await response.json();
      console.error('Anthropic API error:', errorData);
      throw new Error(`API request failed: ${response.status}`);
    }

    const data = await response.json();
    const assistantMessage = data.content[0].text;

    res.json({
      response: assistantMessage,
      conversationId: data.id
    });

  } catch (error) {
    console.error('Error in chat endpoint:', error);
    res.status(500).json({ 
      error: 'Failed to get response from AI',
      details: error.message 
    });
  }
});

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ status: 'healthy', timestamp: new Date().toISOString() });
});

// Start server
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  console.log(`API available at http://localhost:${PORT}`);
});
