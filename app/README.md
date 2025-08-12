# Marvin Mobile Client

A minimal Expo React Native client for the Marvin Memory Assistant backend.

## Quick Start

1. **Navigate to the app directory:**
   ```bash
   cd app
   ```

2. **Install dependencies:**
   ```bash
   npm install
   npm install -D dotenv
   ```

3. **Set up environment configuration:**
   ```bash
   # Copy the example environment file
   cp ../env.example .env
   
   # Edit .env with your backend URL and API key
   # nano .env  # or use your preferred editor
   ```

4. **Start the development server:**
   ```bash
   # For iOS Simulator
   npx expo start --ios
   
   # For Android Emulator
   npx expo start --android
   
   # For web browser
   npx expo start --web
   
   # Or scan QR code with Expo Go app
   npx expo start
   ```

## Configuration

Create an `app/.env` file with the following variables:

```env
# Backend server URL
HEROKU_URL=http://127.0.0.1:8000

# API key for authentication (optional)
API_AUTH_KEY=test-secret
```

### Backend URL Options

Choose the appropriate `HEROKU_URL` based on your setup:

| Scenario | URL | Notes |
|----------|-----|-------|
| **Local development** | `http://127.0.0.1:8000` | Backend running on your machine |
| **Android Emulator** | `http://10.0.2.2:8000` | Special IP that maps to host machine |
| **Real device (same Wi-Fi)** | `http://192.168.1.23:8000` | Replace with your machine's LAN IP |
| **ngrok tunnel** | `https://<subdomain>.ngrok.io` | Useful for testing on real devices |
| **Production** | `https://<your-app>.herokuapp.com` | Your deployed Heroku app |

### Finding Your LAN IP

To connect a real device on the same Wi-Fi network:

**macOS/Linux:**
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

**Windows:**
```cmd
ipconfig | findstr "IPv4"
```

## Features

### Store Memory
- Enter text to store as a memory
- Automatically uses Hebrew language (`he`) by default
- Displays server response with status

### Query Memory
- Search existing memories using natural language
- Returns ranked results with similarity scores
- Shows detailed JSON response

### Authentication
- Automatically includes API key if configured
- Shows current server URL and API key status
- Graceful handling when authentication is disabled

## UI Elements

- **Configuration Status**: Shows current server URL and API key status
- **Store Section**: Text input and store button for adding memories
- **Query Section**: Text input and search button for finding memories
- **Results Section**: Pretty-printed JSON response with status codes
- **Loading States**: Buttons disabled during API calls
- **Error Handling**: Clear error messages for network and API errors

## Development Notes

### Environment File Security

⚠️ **Important**: The `app/.env` file contains sensitive configuration and is excluded from Git via `.gitignore`. Never commit this file.

### API Response Format

The app displays raw JSON responses from the backend:

**Store Success (201):**
```json
{
  "duplicate_detected": false,
  "memory_id": "abc123..."
}
```

**Query Success (200):**
```json
{
  "candidates": [
    {
      "memory_id": "abc123...",
      "text": "Your stored memory",
      "similarity_score": 0.95
    }
  ]
}
```

**Error Response (4xx/5xx):**
```json
{
  "detail": "Error description"
}
```

### Network Troubleshooting

1. **"HEROKU_URL is not set"**: Create `app/.env` file with proper configuration
2. **Connection refused**: Check if backend server is running
3. **401 Unauthorized**: Verify API key is correct (if authentication is enabled)
4. **Network timeout**: Try different URL format (see configuration table above)

### Extending the Client

The client is designed to be minimal but extensible:

- Add new API endpoints in `api.js`
- Extend UI components in `App.js`
- Add navigation with React Navigation
- Implement voice input/output
- Add local caching with AsyncStorage

## File Structure

```
app/
├── App.js              # Main React Native component
├── api.js              # API client with authentication
├── app.config.js       # Expo configuration with env support
├── README.md           # This file
├── .env                # Environment variables (create from ../env.example)
└── package.json        # Dependencies and scripts
```