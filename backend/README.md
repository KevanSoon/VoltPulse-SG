---
title: Ollama API Proxy
emoji: 🦙
colorFrom: purple
colorTo: blue
sdk: docker
pinned: false
---

# Ollama API Proxy

A FastAPI-based proxy for the Ollama API hosted on Hugging Face Spaces.

## Endpoints

### GET /
Health check endpoint returning service status.

### GET /health
Simple health check endpoint.

### POST /chat
Send a chat message to the Ollama API.

**Request Body:**
```json
{
  "message": "Your message here",
  "model": "gpt-oss:120b",
  "stream": true
}
```

**Response (non-streaming):**
```json
{
  "response": "The AI response"
}
```

## Environment Variables

- `OLLAMA_API_KEY`: Your Ollama API key (set as a secret in HF Spaces)

## Setup

1. Create a new Space on Hugging Face with Docker SDK
2. Add `OLLAMA_API_KEY` as a repository secret
3. Push this code to the Space repository
