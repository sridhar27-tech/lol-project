// WhatsApp Medical Symptom Checker Bot using whatsapp-web.js
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');

// Create a new client instance with local authentication
const client = new Client({
    authStrategy: new LocalAuth(), // Saves login session locally
    puppeteer: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
});

// Medical symptoms database with common misspellings
const medicalSymptoms = {
    fever: {
        info: "Fever can be a sign of infection, inflammation, or other medical conditions.",
        questions: ["How high is your temperature?", "How long have you had this fever?", "Do you have any other symptoms along with the fever?"],
        variations: ["fever", "feverish", "hot", "burning up", "temperature", "fvr", "feverr"]
    },
    cough: {
        info: "Coughing may indicate respiratory infections, allergies, or asthma.",
        questions: ["Is your cough dry or productive?", "How long have you had this cough?", "Does anything seem to make it better or worse?"],
        variations: ["cough", "coughing", "coughh", "coff", "koff", "cuf", "coug"]
    },
    headache: {
        info: "Headaches can be caused by tension, migraines, dehydration, or more serious conditions.",
        questions: ["Where exactly is your headache located?", "How would you describe the pain?", "How long have you been experiencing these headaches?"],
        variations: ["headache", "head ache", "hedache", "hedake", "migraine", "head pain", "headhurts"]
    },
    dizzy: {
        info: "Dizziness might be related to inner ear problems, low blood pressure, or neurological issues.",
        questions: ["Does the dizziness come with spinning sensations?", "How often do you feel dizzy?", "Does it happen when you stand up quickly?"],
        variations: ["dizzy", "dizziness", "dizzyness", "dizzy spell", "lightheaded", "dizy", "dizzie"]
    },
    nausea: {
        info: "Nausea can be a symptom of gastrointestinal issues, pregnancy, or infections.",
        questions: ["Have you vomited?", "How long have you been feeling nauseous?", "Does anything seem to trigger the nausea?"],
        variations: ["nausea", "nauseous", "nausia", "nauseated", "sick to stomach", "feeling sick", "nautious"]
    },
    fatigue: {
        info: "Fatigue may indicate anemia, sleep disorders, thyroid problems, or chronic fatigue syndrome.",
        questions: ["How long have you been feeling unusually tired?", "Is your fatigue constant or does it come and go?", "Do you have trouble sleeping?"],
        variations: ["fatigue", "tired", "exhausted", "weak", "low energy", "fatigued", "fatique", "fatige"]
    },
    chestpain: {
        info: "Chest pain requires immediate medical attention as it could indicate heart problems.",
        questions: ["Please describe the chest pain in more detail.", "Does the pain radiate to other areas?", "Are you having any trouble breathing?"],
        variations: ["chest pain", "chest hurt", "chest discomfort", "heart pain", "chestpang", "chestpane"],
        urgent: true
    },
    shortness: {
        info: "Shortness of breath can be a sign of asthma, heart conditions, or anxiety.",
        questions: ["When did you first notice this shortness of breath?", "Does it occur at rest or only with activity?", "Do you have any history of respiratory issues?"],
        variations: ["shortness of breath", "breathless", "can't breathe", "difficulty breathing", "short breath", "breathing problem"]
    },
    sorethroat: {
        info: "Sore throat is commonly caused by viral or bacterial infections.",
        questions: ["How long has your throat been sore?", "Do you have difficulty swallowing?", "Do you have swollen glands in your neck?"],
        variations: ["sore throat", "throat pain", "throat hurt", "scratchy throat", "sorethrote", "throatsore"]
    },
    cold: {
        info: "Colds may be caused by viruses or weather changes. It's not safe to ignore persistent symptoms.",
        questions: ["How long have you had these cold symptoms?", "Do you have a fever along with your cold?", "Are you experiencing any sinus pressure?"],
        variations: ["cold", "common cold", "cold symptoms", "have a cold", "kold", "colde"]
    }
};

// Emotional distress phrases and responses
const emotionalSupport = {
    phrases: [
        "i want to die", "i'm going to die", "i cant do this anymore", "i give up",
        "i hate my life", "end it all", "kill myself", "suicide", "no will to live",
        "nothing matters", "so depressed", "extremely sad", "can't go on", "hopeless"
    ],
    responses: [
        "I'm really concerned about what you're saying. Your life is precious, and there are people who want to help you. Please reach out to a mental health professional or crisis helpline immediately.",
        "It sounds like you're going through an incredibly difficult time. Please know that you don't have to face this alone. There are people who care and want to help. Can you reach out to someone you trust?",
        "I hear the pain in your words, and I want you to know that your feelings are valid. But please know that these intense feelings can pass with proper support. Would you consider contacting a helpline?",
        "I'm really worried about you. When we feel this overwhelmed, it's important to talk to someone who can help. There are professionals available right now who want to support you.",
        "Thank you for sharing this with me. It takes courage to express these feelings. Please know that there is hope and help available. Would you like me to provide some resources?"
    ],
    resources: [
        "National Suicide Prevention Lifeline: 1-800-273-8255",
        "Crisis Text Line: Text HOME to 741741",
        "International Association for Suicide Prevention: https://www.iasp.info/resources/Crisis_Centres/",
        "Emergency services: 911 or your local emergency number"
    ]
};

// User conversation memory
const userSessions = new Map();

// Response variations for common interactions
const responseVariations = {
    greeting: [
        "Hello {name}! 👋 I'm here to help with any health questions you might have. How are you feeling today?",
        "Hi {name}! 😊 I'm your medical information assistant. What can I help you with today?",
        "Hey {name}! 👋 Ready to talk about your health concerns? How can I assist you?",
        "Good to see you, {name}! 🌟 I'm here to provide health information. What's on your mind?"
    ],
    thanks: [
        "You're very welcome! 😊 I'm always here if you have more questions.",
        "Happy to help! 🌟 Don't hesitate to reach out if anything else comes up.",
        "Anytime! 😊 Remember, I'm here 24/7 for your health information needs.",
        "Glad I could assist! 🌟 Take care and feel free to message again if needed."
    ],
    goodbye: [
        "Goodbye! 👋 Hope you feel better soon!",
        "Take care! 😊 Remember to consult a doctor for persistent symptoms.",
        "See you later! 🌟 Don't hesitate to message if you have more questions.",
        "Bye for now! 👋 Wishing you good health!"
    ],
    noUnderstanding: [
        "I'm not quite sure I understand. Could you tell me more about how you're feeling?",
        "Hmm, I'm not following. Could you describe your symptoms in different words?",
        "I want to make sure I help correctly. Could you rephrase that?",
        "Let me try to understand better. Could you tell me what symptoms you're experiencing?"
    ]
};

// Helper functions
function getRandomResponse(type, name = "there") {
    const responses = responseVariations[type];
    const randomIndex = Math.floor(Math.random() * responses.length);
    return responses[randomIndex].replace("{name}", name);
}

function initializeUserSession(userId) {
    userSessions.set(userId, {
        lastMessage: "",
        messageCount: 0,
        symptomHistory: [],
        conversationState: "idle",
        emotionalState: "neutral"
    });
}

function updateUserSession(userId, message, symptom = null) {
    if (!userSessions.has(userId)) {
        initializeUserSession(userId);
    }
    
    const session = userSessions.get(userId);
    session.messageCount++;
    
    if (message === session.lastMessage) {
        session.repeatCount = (session.repeatCount || 0) + 1;
    } else {
        session.repeatCount = 0;
    }
    
    session.lastMessage = message;
    
    if (symptom) {
        session.symptomHistory.push(symptom);
        session.conversationState = "discussing_symptoms";
    }
    
    return session;
}

function checkForEmotionalDistress(message) {
    const lowerMessage = message.toLowerCase();
    for (const phrase of emotionalSupport.phrases) {
        if (lowerMessage.includes(phrase)) {
            return true;
        }
    }
    return false;
}

function getEmotionalSupportResponse() {
    const randomIndex = Math.floor(Math.random() * emotionalSupport.responses.length);
    let response = emotionalSupport.responses[randomIndex] + "\n\n";
    
    // Add a couple of resources
    response += "Here are some resources that might help:\n";
    response += emotionalSupport.resources[0] + "\n";
    response += emotionalSupport.resources[1] + "\n\n";
    response += "Please reach out to someone. You don't have to go through this alone.";
    
    return response;
}

function findSymptomInMessage(message) {
    const lowerMessage = message.toLowerCase();
    
    // Check for emotional distress first
    if (checkForEmotionalDistress(lowerMessage)) {
        return { type: "emotional", response: getEmotionalSupportResponse() };
    }
    
    // Check for symptoms with tolerance for typos
    for (const [symptomKey, symptomData] of Object.entries(medicalSymptoms)) {
        for (const variation of symptomData.variations) {
            if (lowerMessage.includes(variation)) {
                return { type: "symptom", symptom: { symptom: symptomKey, ...symptomData } };
            }
        }
    }
    
    return null;
}

// Generate QR code for WhatsApp Web login
client.on('qr', (qr) => {
    console.log('QR Code received! Scan this with your WhatsApp:');
    qrcode.generate(qr, { small: true });
});

// When the client is ready
client.on('ready', () => {
    console.log('✅ WhatsApp Medical Bot is ready and connected!');
    console.log('🤖 Bot is now listening for messages...');
});

// Listen for incoming messages
client.on('message', async (message) => {
    // Ignore group messages
    const chat = await message.getChat();
    if (chat.isGroup) {
        return;
    }
    
    console.log(`📱 Message from ${message.from}: ${message.body}`);
    
    const contact = await message.getContact();
    const userName = contact.pushname || contact.name || "there";
    const userId = message.from;
    
    // Update user session
    const session = updateUserSession(userId, message.body.toLowerCase());
    
    // Check for emotional distress or symptoms
    const detectedIssue = findSymptomInMessage(message.body);
    
    // Handle emotional distress with priority
    if (detectedIssue && detectedIssue.type === "emotional") {
        await message.reply(detectedIssue.response);
        return;
    }
    
    // Handle repeated messages
    if (session.repeatCount > 0) {
        if (session.repeatCount === 1) {
            await message.reply("I already responded to that. Is there something else you'd like to know?");
            return;
        } else if (session.repeatCount >= 2) {
            await message.reply("I notice you're sending the same message. Would you like to talk to a human instead? Type 'help' to see what I can assist with.");
            return;
        }
    }
    
    // Bot responses based on message content
    const messageText = message.body.toLowerCase();
    
    // Auto-reply logic
    if (messageText === 'hi' || messageText === 'hello' || messageText === 'hey') {
        await message.reply(getRandomResponse('greeting', userName));
        
    } else if (messageText === 'help' || messageText === 'commands') {
        await message.reply(`🤖 Medical Bot - Available commands:
        
• hi/hello - Greeting
• help - Show this menu
• time - Current time
• joke - Random joke
• about - About this bot
• ping - Test response

💊 Describe your symptoms and I'll provide information about possible causes.

Common symptoms I recognize: fever, cough, headache, dizzy, nausea, fatigue, chest pain, shortness of breath, and more.`);
        
    } else if (messageText === 'time') {
        const now = new Date();
        await message.reply(`🕐 It's currently ${now.toLocaleTimeString()} on ${now.toLocaleDateString()}`);
        
    } else if (messageText === 'joke') {
        const jokes = [
            "Why don't scientists trust atoms? Because they make up everything! 😄",
            "Why did the scarecrow win an award? He was outstanding in his field! 🌾",
            "Why don't eggs tell jokes? They'd crack each other up! 🥚",
            "What do you call a fake noodle? An impasta! 🍝",
            "Why did the coffee file a police report? It got mugged! ☕"
        ];
        const randomJoke = jokes[Math.floor(Math.random() * jokes.length)];
        await message.reply(randomJoke);
        
    } else if (messageText === 'about') {
        await message.reply(`🤖 Medical Symptom Checker Bot v2.0
        
I'm here to provide general health information and symptom checking. Remember:

• I'm not a substitute for professional medical advice
• Always consult a healthcare provider for proper diagnosis
• In emergencies, please contact local emergency services immediately

Type 'help' to see what I can do!`);
        
    } else if (messageText === 'ping') {
        await message.reply('🏓 Pong! Everything seems to be working perfectly!');
        
    } else if (messageText.includes('thank')) {
        await message.reply(getRandomResponse('thanks', userName));
        
    } else if (messageText === 'bye' || messageText === 'goodbye') {
        await message.reply(getRandomResponse('goodbye', userName));
        
    } else if (detectedIssue && detectedIssue.type === "symptom") {
        // Respond with medical information
        const symptom = detectedIssue.symptom;
        
        let response = `I understand you're concerned about ${symptom.symptom}. ${symptom.info}\n\n`;
        
        // Add urgent warning if needed
        if (symptom.urgent) {
            response += "🚨 This symptom may require urgent medical attention. Please consider contacting a healthcare professional soon.\n\n";
        }
        
        // Ask a follow-up question
        if (symptom.questions && symptom.questions.length > 0) {
            const randomQuestion = symptom.questions[Math.floor(Math.random() * symptom.questions.length)];
            response += `To help me understand better: ${randomQuestion}`;
        }
        
        response += "\n\n⚠️ Remember: This is for informational purposes only. Please consult a healthcare professional for proper medical advice.";
        
        await message.reply(response);
        
    } else {
        // Default response for unrecognized messages
        await message.reply(getRandomResponse('noUnderstanding'));
    }
});

// Handle client authentication failure
client.on('auth_failure', msg => {
    console.error('❌ Authentication failed:', msg);
});

// Handle disconnection
client.on('disconnected', (reason) => {
    console.log('❌ Client was logged out:', reason);
    // Clear user sessions on disconnect
    userSessions.clear();
});

// Start the client
console.log('🚀 Starting WhatsApp Medical Bot...');
client.initialize();

// Clean up old sessions periodically (24 hours)
setInterval(() => {
    console.log('Cleaning up old user sessions...');
    userSessions.clear();
}, 24 * 60 * 60 * 1000);