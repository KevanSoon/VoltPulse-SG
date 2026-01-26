# VoltPulse OCR Frontend

A Next.js frontend for uploading images and extracting text using PaddleOCR.

## Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Configure environment (optional):
Edit `.env.local` to point to your backend:
```
BACKEND_URL=http://localhost:7860
```

3. Run the development server:
```bash
npm run dev
```

The frontend will be available at http://localhost:3000

## Backend Setup

Make sure the FastAPI backend is running:

```bash
cd backend
pip install -r requirements.txt
python app.py
```

The backend will run on port 7860.

## Features

- Drag and drop image upload
- Supports PNG, JPG, JPEG, GIF, BMP, WebP formats
- Extracts text using PaddleOCR via Gradio
- Generates embeddings using SeaLion encoder
- Stores embeddings in Supabase vector database

## API Endpoints

### POST /api/ocr
Proxies to backend `/ocr/process` endpoint.

**Request:** FormData with `file` field

**Response:**
```json
{
  "ocr_results": {
    "0": { "text": "Hello", "box": [[x1,y1], [x2,y2], ...] },
    "1": { "text": "World", "box": [[x1,y1], [x2,y2], ...] }
  },
  "extracted_texts": ["Hello", "World"],
  "embedding_stored": true,
  "source_id": "ocr_abc123def456"
}
```
