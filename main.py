import os
import sys
import asyncio
import json
import time
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import httpx
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="LLMWhisperer Invoice Extractor")

LLMWHISPERER_API_KEY = os.getenv("LLMWHISPERER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLMWHISPERER_BASE_URL = "https://llmwhisperer-api.us-central.unstract.com/api/v2"

if not LLMWHISPERER_API_KEY:
    raise ValueError("LLMWHISPERER_API_KEY environment variable is required")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")

openai_client = AsyncOpenAI(
    api_key=OPENAI_API_KEY,
    timeout=180.0,
    max_retries=0
)


async def submit_document(file_content: bytes) -> str:
    """Submit document to LLMWhisperer for processing"""
    print(f"[LLMWhisperer] Submitting document ({len(file_content)} bytes)...")
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{LLMWHISPERER_BASE_URL}/whisper",
            params={
                "mode": "form",
                "output_mode": "layout_preserving"
            },
            headers={
                "unstract-key": LLMWHISPERER_API_KEY,
                "Content-Type": "application/octet-stream"
            },
            content=file_content
        )
        
        if response.status_code != 202:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to submit document: {response.text}"
            )
        
        whisper_hash = response.json()["whisper_hash"]
        print(f"[LLMWhisperer] Document submitted successfully. Hash: {whisper_hash}")
        return whisper_hash


async def check_status(whisper_hash: str) -> dict:
    """Check processing status of submitted document"""
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.get(
            f"{LLMWHISPERER_BASE_URL}/whisper-status",
            params={"whisper_hash": whisper_hash},
            headers={"unstract-key": LLMWHISPERER_API_KEY}
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to check status: {response.text}"
            )
        
        return response.json()


async def retrieve_text(whisper_hash: str) -> str:
    """Retrieve extracted text from LLMWhisperer"""
    print(f"[LLMWhisperer] Retrieving extracted text...")
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.get(
            f"{LLMWHISPERER_BASE_URL}/whisper-retrieve",
            params={"whisper_hash": whisper_hash},
            headers={"unstract-key": LLMWHISPERER_API_KEY}
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to retrieve text: {response.text}"
            )
        
        extracted_text = response.text
        print(f"[LLMWhisperer] Text retrieved successfully ({len(extracted_text)} characters)")
        return extracted_text


async def parse_invoice_items(extracted_text: str) -> dict:
    """Parse extracted text using LLM to identify structured invoice line items"""
    print(f"[OpenAI] Starting LLM parsing (text length: {len(extracted_text)} chars)...")
    
    system_prompt = """You are an invoice data extraction specialist. Extract all line items from the invoice text and return them in valid JSON format.

For each line item, extract:
- description: item description
- quantity: numeric quantity
- unit: unit of measure (Ea, lbs, etc)
- unit_price: price per unit as a number
- total_price: total price as a number
- country: country code if present

Also extract invoice-level data:
- subtotal
- freight_charges
- total
- currency

Return ONLY valid JSON, no markdown or explanations."""

    user_prompt = f"""Extract all line items and totals from this invoice:

{extracted_text}

Return as JSON with this structure:
{{
  "line_items": [
    {{"description": "...", "quantity": 1, "unit": "Ea", "unit_price": 1.25, "total_price": 1.25, "country": "US"}}
  ],
  "invoice_summary": {{
    "subtotal": 21677.74,
    "freight_charges": 0,
    "total": 21677.74,
    "currency": "USD"
  }}
}}"""

    print(f"[OpenAI] Sending request to OpenAI API (model: gpt-4o)...")
    sys.stdout.flush()
    print(f"[OpenAI] Message size - System: {len(system_prompt)} chars, User: {len(user_prompt)} chars")
    sys.stdout.flush()
    
    start_time = time.time()
    
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0,
            response_format={"type": "json_object"},
            timeout=180.0
        )
        elapsed = time.time() - start_time
        print(f"[OpenAI] ✓ Received response from OpenAI API (took {elapsed:.2f}s)")
    except TimeoutError as e:
        elapsed = time.time() - start_time
        print(f"[OpenAI] ✗ TIMEOUT after {elapsed:.2f}s: {str(e)}")
        raise HTTPException(
            status_code=504,
            detail=f"OpenAI API timeout after {elapsed:.2f}s"
        )
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[OpenAI] ✗ ERROR after {elapsed:.2f}s: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"OpenAI API error: {str(e)}"
        )
    
    print(f"[OpenAI] LLM parsing complete")
    structured_data = json.loads(response.choices[0].message.content)
    print(f"[OpenAI] Parsed {len(structured_data.get('line_items', []))} line items")
    
    return {
        "success": True,
        "data": structured_data
    }


@app.post("/extract-invoice")
async def extract_invoice(file: UploadFile = File(...)):
    """
    Upload a file and extract invoice line items
    """
    print(f"\n{'='*60}")
    print(f"[API] New request received: {file.filename}")
    print(f"{'='*60}")
    
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    # Read file content
    file_content = await file.read()
    print(f"[API] File read successfully ({len(file_content)} bytes)")
    
    # Submit to LLMWhisperer
    whisper_hash = await submit_document(file_content)
    
    # Poll for completion
    max_attempts = 150
    attempt = 0
    
    print(f"[API] Polling for completion (max {max_attempts} attempts)...")
    while attempt < max_attempts:
        status_response = await check_status(whisper_hash)
        status = status_response.get("status")
        
        if status == "processed":
            print(f"[API] ✓ Document processed successfully (attempt {attempt + 1})")
            break
        elif status in ["processing", "accepted"]:
            if attempt % 10 == 0:
                print(f"[API] Still {status}... (attempt {attempt + 1}/{max_attempts})")
            attempt += 1
            await asyncio.sleep(2)
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected status: {status}"
            )
    
    if attempt >= max_attempts:
        print(f"[API] ✗ Processing timeout after {max_attempts} attempts")
        raise HTTPException(
            status_code=408,
            detail="Processing timeout"
        )
    
    # Retrieve extracted text
    extracted_text = await retrieve_text(whisper_hash)
    
    # Parse invoice items
    result = await parse_invoice_items(extracted_text)
    
    print(f"[API] ✓ Request completed successfully")
    print(f"{'='*60}\n")
    
    return JSONResponse(content=result)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "llmwhisperer_key_set": bool(LLMWHISPERER_API_KEY),
        "openai_key_set": bool(OPENAI_API_KEY)
    }


@app.post("/test-openai")
async def test_openai():
    """Test OpenAI API connectivity with a simple request"""
    print(f"[TEST] Testing OpenAI API connection...")
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": "Say 'OK' if you can hear me"}
            ],
            max_tokens=10,
            timeout=30.0
        )
        result = response.choices[0].message.content
        print(f"[TEST] ✓ OpenAI API working: {result}")
        return {"status": "success", "response": result}
    except Exception as e:
        print(f"[TEST] ✗ OpenAI API failed: {type(e).__name__}: {str(e)}")
        return {"status": "error", "error": str(e)}


@app.on_event("startup")
async def startup_event():
    print("\n" + "="*60)
    print("LLMWhisperer Invoice Extractor - Starting Up")
    print("="*60)
    print(f"LLMWhisperer API Key: {'✓ Set' if LLMWHISPERER_API_KEY else '✗ Missing'}")
    if LLMWHISPERER_API_KEY:
        print(f"  → {LLMWHISPERER_API_KEY[:8]}...{LLMWHISPERER_API_KEY[-4:]}")
    print(f"OpenAI API Key: {'✓ Set' if OPENAI_API_KEY else '✗ Missing'}")
    if OPENAI_API_KEY:
        print(f"  → {OPENAI_API_KEY[:8]}...{OPENAI_API_KEY[-4:]}")
    print(f"Model: gpt-4o")
    print(f"Timeout: 180s")
    print("="*60 + "\n")

