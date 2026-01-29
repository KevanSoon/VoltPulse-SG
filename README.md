# VoltPulse SG ⚡

<p align="center">
  <img src="frontend/public/volt.png" alt="VoltPulse Logo" width="120" />
</p>

<p align="center">
  <strong>AI-Powered Utility Bill Analysis for Singapore Households</strong>
</p>

---

## Project Description

**VoltPulse SG** addresses the challenge of helping Singapore households understand and reduce their energy consumption while maximizing government savings through Climate Vouchers.

### The Problem
- Singapore households often struggle to interpret complex utility bills
- Many residents are unaware of how their consumption compares to national averages
- Climate Voucher benefits ($300 worth) remain underutilized due to lack of awareness
- Finding authorized retailers for energy-efficient appliances is time-consuming

### Our Solution
VoltPulse SG is an AI-powered platform that:
- **Extracts bill data automatically** using OCR and Vision AI from uploaded SP utility bills
- **Analyzes consumption patterns** with interactive charts and national benchmarking
- **Provides AI-powered diagnosis** identifying inefficiencies and savings opportunities
- **Calculates ROI** for energy-efficient appliance upgrades
- **Locates authorized Climate Voucher retailers** near the user's address
- **Offers an intelligent chatbot** for personalized energy-saving advice

### Tech Stack
| Component | Technology |
|-----------|------------|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.11+ |
| AI/ML | LangGraph, LangChain, Ollama (GPT-OSS 120B) |
| Database | Supabase (PostgreSQL + pgvector) |
| OCR | OpenAI Vision |
| Embeddings | SeaLion Encoder |
| Maps | Leaflet / React-Leaflet |

---

## Setup Instructions

### Prerequisites
- **Node.js** 18+ and npm
- **Python** 3.11+
- **Git**

### 1. Clone the Repository
```bash
git clone https://github.com/your-org/VoltPulse-SG.git
cd VoltPulse-SG
```

### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Backend Environment Variables
Create a `.env` file in the `backend/` directory:
```env
# Ollama API
OLLAMA_API_KEY=your_ollama_api_key
OLLAMA_BASE_URL=https://your-ollama-endpoint

# Supabase Database
SUPABASE_DB_HOST=your-supabase-host
SUPABASE_DB_PORT=6543
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=your-db-user
SUPABASE_DB_PASSWORD=your-db-password
SUPABASE_DB_SSLMODE=require

# SeaLion Encoder
SEALION_ENDPOINT=your-sealion-endpoint

# Tavily API (for web search)
TAVILY_API_KEY=your_tavily_api_key

# OpenAI 
OPENAI_API_KEY=your_openai_api_key
```

### 4. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install
```

### 5. Frontend Environment Variables
Create a `.env.local` file in the `frontend/` directory:
```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:7860
```

### 6. Run the Application

**Terminal 1 - Backend:**
```bash
cd backend
uvicorn app:app --reload --port 7860
# Backend runs on http://localhost:7860
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
# Frontend runs on http://localhost:3000
```

---

## Usage Guide

### 1. Upload Your Utility Bill
1. Navigate to http://localhost:3000
2. Click **"Upload Bill"** in the navigation
3. Drag & drop or select your SP utility bill image (PNG, JPG, PDF)
4. Wait for OCR processing to complete

### 2. View Analytics Dashboard
After upload, you'll be redirected to the **Analytics Dashboard** where you can:
- View your **electricity, gas, and water consumption**
- Compare against **national and neighborhood averages**
- See a **Singapore heatmap** of consumption by district
- Review **AI-generated diagnosis** of your usage patterns

### 3. Calculate ROI for Appliance Upgrades
1. Navigate to the **ROI Calculator** tab
2. Select an appliance type (e.g., Air Conditioner, Refrigerator)
3. Enter your current appliance's energy rating
4. See estimated **yearly savings** and **payback period**
5. Click **"Find Retailers"** to locate authorized Climate Voucher merchants

### 4. Chat with AI Assistant
- Click the **chat bubble** in the bottom-right corner
- Ask questions like:
  - *"How can I reduce my electricity bill?"*
  - *"Find air conditioner retailers near Tampines"*
  - *"What appliances are eligible for Climate Vouchers?"*


### Cloud Deployment Options

| Platform | Component | Notes |
|----------|-----------|-------|
| **Vercel** | Frontend | Recommended for Next.js |
| **Hugging Face Spaces** | Backend | Docker SDK support |
| **Railway** | Backend + DB | Easy PostgreSQL setup |
| **Supabase** | Database | Managed PostgreSQL + pgvector |

### Production Environment Variables
Ensure all environment variables are set as secrets in your deployment platform.

---

## Contributors

| Name | Role |
|------|------|
| **Zulfaqar Hafez** | AI Developer |
| **Kevan Soon** | Full-Stack Developer |
| **Rahul Mitra** | Full-Stack Developer |
| **Kwa Guang Hao** | Full-Stack Developer |
---

## Additional Notes

### Known Limitations
- OCR accuracy may vary with image quality; clear, high-resolution scans work best
- Climate Voucher retailer data is sourced from NEA and may not reflect real-time availability
- The AI chatbot requires an active Ollama API connection

### Privacy & Data Security

| Feature | Implementation |
|---------|----------------|
| **Session Anonymization** | Random UUID session IDs (no user tracking) |
| **NRIC Masking** | Only last 4 characters shown (`S****567A`) |
| **Account Number Masking** | Only last 4 digits displayed |
| **Coordinate Precision** | Reduced to 3 decimals (~100m accuracy) |
| **Data Minimization** | Sessions auto-expire, no long-term PII storage |
| **Local Processing** | Bill OCR processed server-side, not sent to third parties |

**Data Retention:**
- Chat sessions: Cleared on browser close (localStorage)
- Bill data: Not persisted after analysis session
- No cookies or user tracking implemented

### Assumptions
- Users have access to their SP Group utility bills
- Singapore-based households with HDB or private residential addresses
- Internet connection required for AI features

### Future Improvements
- [ ] Mobile app (React Native)
- [ ] PDF bill upload support with multi-page extraction
- [ ] Integration with SP Group API for automatic bill fetching
- [ ] Push notifications for unusual consumption spikes
- [ ] Multi-language support (Chinese, Malay, Tamil)
- [ ] Historical bill tracking and trend analysis
- [ ] Solar panel ROI calculator
- [ ] Community benchmarking by estate/block

### License
This project is developed for the SMU Hack For Cities 2026.

---

<p align="center">
  Made with ❤️ in Singapore
</p>
