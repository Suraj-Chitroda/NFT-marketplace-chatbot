# NFT Marketplace Chatbot - Frontend

Minimal React + Vite frontend for testing the NFT chatbot API.

## Features

- 💬 Real-time chat interface
- 🎨 Displays both markdown text and HTML components
- 📱 Responsive design
- 🔄 Session management
- ⚡ Fast and lightweight

## Prerequisites

- Node.js (v22.x)
- Backend API running on http://localhost:8000
- NFT API running on http://localhost:4000

## Quick Start

### 1. Install Dependencies

```bash
npm install
```

### 2. Start Development Server

```bash
npm run dev
```

The app will be available at **http://localhost:5173**

## Usage

1. **Make sure both backend services are running:**
   
   Terminal 1 - NFT API:
   ```bash
   cd ../backend
   python api_backend.py
   ```
   
   Terminal 2 - Chatbot API:
   ```bash
   cd ..
   python agno-agent.py
   ```

2. **Open the frontend:**
   ```
   http://localhost:5173
   ```

3. **Try these queries:**
   - "Show me some NFTs"
   - "Find rare NFTs under 5 ETH"
   - "Show NFTs from Meta Legends collection"
   - "Tell me about NFT nft-042"

## API Configuration

The frontend connects to:
- **Chatbot API:** `http://localhost:8000`

To change this, edit `src/App.jsx`:
```javascript
const API_URL = 'http://localhost:8000';
```

## Building for Production

```bash
npm run build
```

The production build will be in the `dist/` directory.

## Project Structure

```
frontend/
├── src/
│   ├── App.jsx       # Main chat component
│   ├── App.css       # Styling
│   ├── main.jsx      # Entry point
│   └── index.css     # Global styles
├── index.html        # HTML template
├── package.json      # Dependencies
└── vite.config.js    # Vite configuration
```

## Tech Stack

- **React** - UI library
- **Vite** - Build tool
- **Fetch API** - HTTP requests
- **CSS** - Styling (no frameworks)

## Features Demonstrated

✅ Structured API responses (text + HTML blocks)
✅ Session persistence across messages
✅ Loading states
✅ Error handling
✅ Auto-scrolling
✅ Responsive design
✅ HTML component rendering

## Troubleshooting

**CORS errors?**
- Make sure the backend has `http://localhost:5173` in CORS origins
- Check `nft_chatbot/config.py`

**Can't connect to API?**
- Verify backend is running: `curl http://localhost:8000/health`
- Check browser console for errors

**Blank page?**
- Check browser console
- Verify all dependencies installed: `npm install`
- Try clearing cache and restarting: `npm run dev`
