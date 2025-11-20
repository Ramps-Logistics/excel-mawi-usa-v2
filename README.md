# LLMWhisperer Invoice Extractor

FastAPI server that extracts and structures invoice line items from Excel/PDF files using LLMWhisperer and OpenAI.

## Features

- Upload Excel/PDF invoice files
- Extract text using LLMWhisperer API
- Parse and structure invoice data using OpenAI GPT-4o
- Returns JSON with line items and invoice summary

## Local Development

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create `.env` file (copy from `.env.example`):
```bash
LLMWHISPERER_API_KEY=your_llmwhisperer_key
OPENAI_API_KEY=your_openai_key
CORS_ORIGINS=*
```

Or for specific origins:
```bash
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

3. Run the server:
```bash
uvicorn main:app --reload
```

### API Endpoints

- `POST /extract-invoice` - Upload file and extract invoice data
- `POST /test-openai` - Test OpenAI API connectivity
- `GET /health` - Health check

### Usage Example

```bash
curl -X POST "http://localhost:8000/extract-invoice" \
  -F "file=@invoice.xlsx"
```

## Railway Deployment

### Environment Variables

Configure these in Railway dashboard:
- `LLMWHISPERER_API_KEY` - Your LLMWhisperer API key
- `OPENAI_API_KEY` - Your OpenAI API key
- `CORS_ORIGINS` - Allowed CORS origins (comma-separated) or `*` for all

### Deploy Steps

1. Connect your GitHub repository to Railway
2. Railway will auto-detect Python and use the Procfile
3. Add environment variables in Railway dashboard
4. Deploy

Railway will automatically:
- Install dependencies from `requirements.txt`
- Use Python version from `runtime.txt`
- Run the command from `Procfile`
- Expose the service on the assigned port

## API Response Format

```json
{
  "success": true,
  "data": {
    "line_items": [
      {
        "description": "Item description",
        "quantity": 1,
        "unit": "Ea",
        "unit_price": 10.00,
        "total_price": 10.00,
        "country": "US"
      }
    ],
    "invoice_summary": {
      "subtotal": 100.00,
      "freight_charges": 0,
      "total": 100.00,
      "currency": "USD"
    }
  }
}
```

## Technologies

- FastAPI - Web framework
- LLMWhisperer - Document text extraction
- OpenAI GPT-4o - Structured data parsing
- Uvicorn - ASGI server

