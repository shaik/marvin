# Marvin — Personal Memory Assistant

[![Tests](https://github.com/shaik/marvin/actions/workflows/tests.yml/badge.svg)](https://github.com/shaik/marvin/actions/workflows/tests.yml)

Marvin is a semantic memory assistant with embedding-based storage, intelligent clarification, and natural language interaction. The system consists of a Python FastAPI backend with OpenAI embeddings and a React Native frontend for mobile access.

## 🚀 Current Status

**✅ IMPLEMENTED & DEPLOYED**
- Complete FastAPI backend with semantic memory storage
- OpenAI text-embedding-ada-002 integration for semantic search
- Intelligent clarification system for ambiguous queries
- SQLite database with embedding storage
- Comprehensive test suites (unit, E2E, clarification flow)
- React Native frontend scaffolding (Expo-based)
- Deployment scripts and configuration
- CI/CD pipeline with automated testing

## 🎯 Key Features

### Memory Operations
- **Store Memories**: Natural language input with semantic embedding
- **Query Memories**: Semantic search with similarity scoring
- **Duplicate Detection**: Automatic detection with 85% similarity threshold
- **Memory Management**: Update, delete, and retrieve specific memories

### Intelligent Clarification System
- **Ambiguity Detection**: Automatically detects when multiple memories have similar scores
- **Smart Questions**: Generates contextual clarification questions mentioning proper nouns
- **Resolution Flow**: Allows users to select from ambiguous candidates
- **Configurable Thresholds**: Environment-controllable sensitivity settings

### Technical Features
- **Semantic Search**: Cosine similarity on OpenAI embeddings
- **Structured Logging**: JSON-formatted logs for observability
- **Error Handling**: Comprehensive exception management with proper HTTP status codes
- **CORS Support**: Cross-origin requests for frontend integration
- **Modular Architecture**: Clean separation of concerns with FastAPI routers

## 📁 Project Structure

```
marvin/
├── agent/                    # Python FastAPI backend
│   ├── api/                 # API route modules
│   │   ├── models.py        # Pydantic request/response models
│   │   ├── query.py         # Memory search with clarification
│   │   ├── clarify.py       # Clarification resolution endpoint
│   │   ├── store.py         # Memory storage endpoint
│   │   └── exceptions.py    # Custom exception handlers
│   ├── memory.py            # Core memory engine (SQLite + OpenAI)
│   ├── config.py            # Application configuration
│   └── main.py              # FastAPI application setup
├── app/                     # React Native frontend (Expo)
│   ├── App.js              # Main chat interface
│   ├── api.js              # Backend communication
│   └── package.json        # Dependencies
├── tests/                   # Comprehensive test suites
│   ├── test_sanity.py      # Unit tests with mocked dependencies
│   ├── test_clarify.py     # Clarification flow tests
│   └── e2e/                # End-to-end tests with live OpenAI
├── .github/workflows/       # CI/CD automation
│   └── tests.yml           # GitHub Actions testing pipeline
├── requirements.txt         # Python dependencies
├── pytest.ini             # Test configuration
├── Procfile                # Heroku deployment config
├── marvin.cursor.yaml      # Cursor agent configuration
└── deploy.sh               # Automated deployment script
```

## 🛠 API Endpoints

### Memory Operations
- `POST /api/v1/store` - Store new memory with duplicate detection
- `POST /api/v1/query` - Semantic search with clarification support
- `POST /api/v1/clarify` - Resolve ambiguous query selections
- `PUT /api/v1/update` - Update existing memory
- `DELETE /api/v1/delete` - Delete memory by ID
- `GET /health` - Service health check

### Request/Response Examples

**Store Memory:**
```bash
POST /api/v1/store
{
  "text": "Code for Dalia from work is 1234",
  "language": "he",
  "location": "office"
}

Response: {
  "duplicate_detected": false,
  "memory_id": "abc-123-def"
}
```

**Query with Clarification:**
```bash
POST /api/v1/query
{"query": "What is Dalia's code?"}

Response: {
  "candidates": [...],
  "clarification_required": true,
  "clarification_question": "There are multiple entries mentioning 'Dalia'. Which one do you mean?"
}
```

**Resolve Clarification:**
```bash
POST /api/v1/clarify
{
  "query": "What is Dalia's code?",
  "chosen_memory_id": "abc-123-def"
}

Response: {
  "clarification_resolved": true,
  "memory_id": "abc-123-def",
  "text": "Code for Dalia from work is 1234"
}
```

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- OpenAI API key
- Node.js 16+ (for frontend)

### Backend Setup
```bash
# Clone and setup
cd /Users/shaik/projects/marvin
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configuration
export OPENAI_API_KEY="your-api-key-here"
export CLARIFY_SCORE_GAP=0.05  # Optional: clarification sensitivity
export CLARIFY_MIN_CANDIDATES=2  # Optional: min candidates for clarification

# Run server
chmod +x server.sh
./server.sh
# OR: uvicorn agent.main:app --host=0.0.0.0 --port=8000 --reload
```

### Frontend Setup
```bash
cd app
npm install
npm start
# OR: npx expo start
```

### Testing
```bash
# Run all tests
chmod +x test.sh
./test.sh

# Run specific test suites
pytest tests/test_sanity.py -v        # Unit tests
pytest tests/test_clarify.py -v       # Clarification tests
pytest tests/e2e/ -v                  # E2E tests (requires OPENAI_API_KEY)
```

## 🔧 Configuration

### Environment Variables
- `OPENAI_API_KEY` - Required for embedding generation
- `DB_PATH` - SQLite database path (default: `agent/marvin_memory.db`)
- `CLARIFY_SCORE_GAP` - Similarity threshold for clarification (default: 0.05)
- `CLARIFY_MIN_CANDIDATES` - Minimum candidates needed for clarification (default: 2)
- `LOG_LEVEL` - Logging level (default: INFO)

### Clarification Settings
The clarification system can be fine-tuned via configuration:
- **Score Gap**: Lower values (0.01-0.03) = more sensitive, triggers clarification more often
- **Min Candidates**: Higher values require more results before considering clarification

## 🧪 Testing Strategy

### Test Suites
1. **Sanity Tests** (`test_sanity.py`): Unit tests with mocked OpenAI, isolated database
2. **Clarification Tests** (`test_clarify.py`): Clarification flow with deterministic embeddings
3. **E2E Tests** (`test_e2e_live_openai.py`): Live integration tests with real OpenAI API

### Test Isolation
- Temporary SQLite databases per test
- Mocked OpenAI for predictable results
- Deterministic embeddings for clarification scenarios

### Continuous Integration
The project includes automated CI/CD via GitHub Actions:
- **Automated Testing**: Runs on every push and pull request to `master`
- **Unit Tests**: Sanity and clarification tests with mocked dependencies
- **Python 3.11**: Tested on latest Ubuntu with pip caching
- **Optional E2E**: Commented workflow for live OpenAI integration tests

```bash
# CI runs equivalent to:
pytest -q  # Unit tests only (fast, no external dependencies)

# Optional E2E (requires OPENAI_API_KEY secret):
pytest -m e2e -q  # Live tests with real OpenAI API
```

## 🚢 Deployment

### Heroku Deployment
```bash
# Automated deployment
chmod +x deploy.sh
./deploy.sh

# Manual deployment
git push heroku master
heroku config:set OPENAI_API_KEY=$OPENAI_API_KEY
heroku run python -c "from agent.memory import init_db; init_db()"
```

### Local Production
```bash
# Production server
uvicorn agent.main:app --host=0.0.0.0 --port=5000 --workers=4
```

## 📊 Architecture

### Backend Architecture
- **FastAPI**: Modern Python web framework with automatic OpenAPI docs
- **SQLite**: Local-first database with embedding storage
- **OpenAI Embeddings**: text-embedding-ada-002 for semantic similarity
- **Pydantic**: Request/response validation and serialization
- **Structured Logging**: JSON logs for observability

### Frontend Architecture
- **React Native**: Cross-platform mobile development
- **Expo**: Development toolchain and build service
- **Voice Integration**: react-native-voice for speech-to-text
- **TTS Support**: expo-av for text-to-speech responses

## 🎯 Roadmap

### Completed ✅
- Core memory storage and retrieval
- Semantic search with OpenAI embeddings
- Intelligent clarification system
- Comprehensive test coverage
- React Native frontend scaffolding
- Deployment automation
- CI/CD pipeline with automated testing

### Next Steps 🔄
- Voice input integration
- Hebrew language optimization
- Mobile app refinement
- Performance optimization
- Advanced conversation flows

## 📝 Agent Configuration

The project includes a comprehensive Cursor agent configuration (`marvin.cursor.yaml`) that defines:
- System architecture and tool interfaces
- Memory operation specifications
- Clarification flow requirements
- Example interactions and edge cases
- Development constraints and best practices

## 🤝 Contributing

1. Follow the protected files policy (tests are immutable unless explicitly requested)
2. Maintain comprehensive test coverage
3. Use structured logging for observability
4. Follow the established architecture patterns
5. Update documentation for new features

---

**Marvin is ready for production use with full semantic memory capabilities and intelligent clarification! 🧠✨**