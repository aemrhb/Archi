# PDF Rule Book + Local LLM Integration Guide

## Overview

The IFC Element Viewer now supports **automatic rule extraction from PDF rule books** using a local LLM (Large Language Model). Instead of manually configuring building code rules, you can upload the full PDF of the building code (e.g., NBauO) and let AI extract the actual requirements.

## Features

✅ **PDF Upload**: Upload the complete building code rule book as PDF  
✅ **AI Extraction**: Local LLM analyzes the PDF and extracts dimensional requirements  
✅ **Automatic Rule Configuration**: Rules are automatically configured from extracted data  
✅ **Manual Override**: Still supports manual rule configuration as fallback  
✅ **Privacy**: All processing happens locally - no data sent to external servers

## Prerequisites

### 1. Install Ollama

Ollama is a tool for running LLMs locally. Install it from:
- **Website**: https://ollama.ai
- **Windows**: Download installer from the website
- **Mac/Linux**: Follow installation instructions on the website

### 2. Pull a Model

After installing Ollama, pull a model (recommended: llama3 or llama3.1):

```bash
ollama pull llama3
```

Or for a smaller, faster model:
```bash
ollama pull llama3.1:8b
```

### 3. Start Ollama

Ollama should start automatically, but if not:
- **Windows**: Run Ollama from Start Menu
- **Mac/Linux**: Run `ollama serve` in terminal

Ollama runs on `http://localhost:11434` by default.

### 4. Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `pdfplumber` - for PDF text extraction
- `ollama` - for LLM integration (or uses requests as fallback)
- `requests` - for HTTP API calls

## How to Use

### Step 1: Choose Rule Source

In the sidebar, select:
- **"Upload PDF Rule Book (AI Extraction)"** - for automatic extraction
- **"Manual Configuration"** - for manual rule entry

### Step 2: Upload PDF (if using AI extraction)

1. Click "Upload NBauO Rule Book PDF"
2. Select your building code PDF file
3. Wait for text extraction (shows progress)

### Step 3: Configure LLM

1. **Select Model**: Choose from available Ollama models (llama3, llama3.1, mistral, etc.)
2. **Ollama URL**: Default is `http://localhost:11434` (change if needed)

### Step 4: Extract Rules

1. Click **"🤖 Extract Rules with AI"** button
2. Wait while AI analyzes the PDF (may take 30-60 seconds)
3. Review extracted rules displayed in the sidebar
4. Rules are automatically saved and used for compliance checking

### Step 5: Upload IFC File

1. Upload your IFC model as usual
2. Compliance checking will use the extracted rules automatically

## Extracted Rules

The AI extracts the following dimensional requirements:

- **Min Door Width** (mm) - for barrier-free access
- **Min Door Height** (mm)
- **Min Window Width** (mm) - if specified
- **Min Window Height** (mm) - if specified
- **Min Room Area** (m²) - if specified
- **Min Room Height** (m) - if specified
- **Min Wall Thickness** (mm) - if specified

## How It Works

### 1. PDF Text Extraction
- Uses `pdfplumber` to extract text from all pages
- Handles various PDF formats and layouts

### 2. LLM Analysis
- Sends PDF text to local Ollama LLM
- LLM analyzes the building code document
- Extracts specific dimensional requirements

### 3. Rule Parsing
- LLM returns JSON with extracted rules
- System parses and validates the JSON
- Rules are stored in session state

### 4. Compliance Checking
- Extracted rules are used automatically
- Same compliance checking as manual configuration
- Violations are flagged based on extracted rules

## LLM Prompt

The system uses a carefully crafted prompt to extract rules:

```
You are an expert in building codes and regulations. 
Analyze the following building code document (Niedersächsische Bauordnung - NBauO) 
and extract specific dimensional requirements.

Extract the following information and return it as a JSON object:
1. Minimum door width for barrier-free access (in mm)
2. Minimum door height (in mm)
3. Minimum window width (in mm, or 0 if not specified)
...
```

## Troubleshooting

### "Ollama is not available"
- **Solution**: Install Ollama from https://ollama.ai
- Make sure Ollama is running (check system tray or run `ollama serve`)

### "Cannot connect to Ollama"
- **Solution**: Check if Ollama is running on `http://localhost:11434`
- Try: `ollama list` in terminal to verify Ollama is working
- If using custom URL, update the "Ollama URL" field

### "Model not found"
- **Solution**: Pull the model first: `ollama pull llama3`
- Check available models: `ollama list`

### "PDF processing not available"
- **Solution**: Install pdfplumber: `pip install pdfplumber`

### "Could not parse LLM response as JSON"
- **Solution**: The LLM might have returned text instead of JSON
- Check the displayed response
- Try a different model (llama3.1, mistral, etc.)
- The response is shown in an error box - you can manually extract values

### Slow Processing
- **Solution**: Use a smaller model (llama3.1:8b instead of llama3)
- Or use manual configuration for faster setup

## Model Recommendations

### Best Accuracy
- **llama3** - Best for complex rule extraction
- **llama3.1** - Improved version of llama3

### Faster Processing
- **llama3.1:8b** - Smaller, faster model
- **mistral** - Fast and efficient

### Code-Specific
- **codellama** - Good for technical documents

## Privacy & Security

✅ **100% Local Processing**
- PDF text extraction: local
- LLM processing: local (Ollama)
- No data sent to external servers
- Your building code PDF stays on your machine

## Limitations

1. **PDF Quality**: Works best with text-based PDFs (not scanned images)
2. **Language**: Optimized for German building codes (NBauO)
3. **Model Size**: Larger models are more accurate but slower
4. **Token Limits**: Very large PDFs may be truncated (first 15,000 chars)

## Future Enhancements

Possible improvements:
- OCR for scanned PDFs
- Multi-language support
- More rule types (ratios, percentages, etc.)
- Rule validation and confidence scores
- Batch processing multiple rule books
- Rule versioning and comparison

## Example Workflow

1. **Download NBauO PDF** from official source
2. **Install Ollama** and pull llama3 model
3. **Start Streamlit app**: `streamlit run app.py`
4. **Select "Upload PDF Rule Book"** in sidebar
5. **Upload NBauO PDF**
6. **Click "Extract Rules with AI"**
7. **Review extracted rules** (e.g., "Min Door Width: 900 mm")
8. **Upload IFC file** for compliance checking
9. **View violations** based on extracted rules

## Manual Override

Even after extracting rules from PDF, you can:
- Switch to "Manual Configuration" to override specific values
- Manually adjust extracted values if needed
- Combine both methods (extract from PDF, then fine-tune manually)



