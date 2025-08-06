# Marvin Memory Assistant - Mobile App

A React Native mobile application built with Expo for the Marvin personal memory assistant service.

## Features

- 🎤 **Voice Input**: Speech-to-text in Hebrew using react-native-voice
- 💬 **Chat Interface**: WhatsApp-style messaging with user and Marvin bubbles
- 🧠 **Memory Storage**: Store personal memories with automatic duplicate detection
- 🔍 **Smart Search**: Query memories using natural language with semantic similarity
- 📍 **Location Context**: Optional location tagging for memories
- 🔄 **Real-time Sync**: Connects to Heroku-hosted backend service
- 🌙 **Dark Theme**: Beautiful Nord-inspired color scheme

## Prerequisites

- Node.js (v16 or higher)
- Expo CLI: `npm install -g @expo/cli`
- A deployed Marvin backend service (see main project README)

## Setup

1. **Install dependencies:**
   ```bash
   cd app
   npm install
   ```

2. **Configure environment:**
   ```bash
   cp env.example .env
   ```
   
   Edit `.env` and set your Heroku URL:
   ```
   HEROKU_URL=https://your-marvin-app.herokuapp.com
   ```

3. **Start the development server:**
   ```bash
   npm start
   ```

## Voice Recognition Setup

The app uses `@react-native-voice/voice` for speech-to-text functionality:

- **iOS**: Requires microphone permission (automatically requested)
- **Android**: Requires RECORD_AUDIO permission (configured in app.json)
- **Supported locale**: Hebrew (he-IL) by default

## Text-to-Speech

Currently uses `expo-av` for audio playback. Future versions will include proper TTS integration.

## Project Structure

```
app/
├── App.js              # Main application component
├── api.js              # Backend API service module
├── package.json        # Dependencies and scripts
├── app.json           # Expo configuration
├── babel.config.js    # Babel configuration
├── env.example        # Environment variables template
└── assets/           # Images and icons (create this folder)
```

## API Integration

The app communicates with the Marvin backend through the following endpoints:

- `POST /api/v1/store` - Store new memories
- `POST /api/v1/query` - Search existing memories
- `POST /api/v1/update` - Update memories
- `POST /api/v1/delete` - Delete memories
- `POST /api/v1/cancel` - Handle cancellation requests
- `POST /api/v1/clarify` - Resolve ambiguous queries

## Development

### Running on different platforms:

```bash
# iOS Simulator
npm run ios

# Android Emulator  
npm run android

# Web browser
npm run web
```

### Environment Variables

- `HEROKU_URL`: Your deployed backend URL
- Additional configuration options available in `env.example`

## Permissions

The app requires the following permissions:

### iOS (automatically configured):
- NSMicrophoneUsageDescription
- NSSpeechRecognitionUsageDescription

### Android (configured in app.json):
- RECORD_AUDIO
- ACCESS_FINE_LOCATION
- ACCESS_COARSE_LOCATION

## Troubleshooting

### Voice Recognition Issues:
- Ensure microphone permissions are granted
- Check device audio settings
- Verify react-native-voice setup for your platform

### Connection Issues:
- Verify HEROKU_URL in .env file
- Check if backend service is running
- Test API endpoints manually

### Build Issues:
- Clear Expo cache: `expo r -c`
- Reinstall dependencies: `rm -rf node_modules && npm install`

## Language Support

The app is primarily designed for Hebrew:
- UI text is in Hebrew
- Voice recognition uses Hebrew locale (he-IL)
- Memory storage supports Hebrew content
- Date/time formatting uses Hebrew locale

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test on both iOS and Android
5. Submit a pull request

## License

MIT License - see main project for details.