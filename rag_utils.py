import re
import logging
from typing import List, Dict
import pdfplumber

logger = logging.getLogger("rag-utils")

# --- SMART CHUNKING CONFIG ---
CHUNK_SIZE = 500   # target characters for sliding window chunks
CHUNK_OVERLAP = 100  # overlap between sliding window chunks

def extract_tables_as_chunks(pdf, source_name: str) -> List[Dict]:
    """Extract tables from PDF as complete chunks using pdfplumber's table detection.
    Keeps entire tables intact so fee data is never split across chunks."""
    table_chunks = []
    for i, page in enumerate(pdf.pages):
        tables = page.extract_tables()
        for t_idx, table in enumerate(tables):
            if not table or len(table) < 2:  # skip empty or header-only tables
                continue
            # Convert table rows to readable text
            rows = []
            for row in table:
                # Filter None values and join cells
                cells = [str(c).strip() if c else "" for c in row]
                rows.append(" | ".join(cells))
            table_text = "\n".join(rows)
            if len(table_text.strip()) < 20:  # skip trivially small tables
                continue
            table_chunks.append({
                "id": f"table_p{i+1}_{t_idx}",
                "text": f"[TABLE from page {i+1}]\n{table_text}",
                "metadata": {
                    "page": str(i + 1),
                    "source": source_name,
                    "chunk_type": "table",
                    "section": ""
                }
            })
    return table_chunks

def split_by_sections(full_text: str, page_map: Dict[int, str], source_name: str) -> List[Dict]:
    """Split text by § section headers. Each section becomes one chunk.
    Long sections get further split by sliding window."""
    # Pattern matches §followed by a number, with optional title text
    section_pattern = re.compile(r'(§\s*\d+[a-z]?(?:\s+[A-ZÄÖÜ][^§]*?)?)(?=§\s*\d|$)', re.DOTALL)
    
    matches = list(section_pattern.finditer(full_text))
    chunks = []
    
    if not matches:
        # No § sections found — return empty, let sliding window handle it
        return chunks
    
    # Handle text before the first § as a preamble chunk
    preamble = full_text[:matches[0].start()].strip()
    if len(preamble) > 50:
        chunks.append({
            "id": f"section_preamble",
            "text": preamble,
            "metadata": {
                "page": "1",
                "source": source_name,
                "chunk_type": "section",
                "section": "Preamble"
            }
        })
    
    for idx, match in enumerate(matches):
        section_text = match.group(0).strip()
        if len(section_text) < 20:
            continue
            
        # Extract section number for metadata
        sec_num_match = re.match(r'§\s*(\d+[a-z]?)', section_text)
        sec_label = f"§{sec_num_match.group(1)}" if sec_num_match else f"§_unknown_{idx}"
        
        # Find which page this section starts on
        sec_start_pos = match.start()
        page_num = _find_page_for_position(sec_start_pos, page_map)
        
        # If section is very long, split with sliding window
        if len(section_text) > CHUNK_SIZE * 4:  # roughly > 2000 chars
            sub_chunks = sliding_window_chunks(
                section_text, page_num, source_name,
                prefix_section=sec_label
            )
            chunks.extend(sub_chunks)
        else:
            chunks.append({
                "id": f"section_{sec_label}_{idx}",
                "text": section_text,
                "metadata": {
                    "page": str(page_num),
                    "source": source_name,
                    "chunk_type": "section",
                    "section": sec_label
                }
            })
    
    return chunks

def sliding_window_chunks(text: str, page_num: int, source_name: str,
                          chunk_size: int = CHUNK_SIZE * 4,
                          overlap: int = CHUNK_OVERLAP * 4,
                          prefix_section: str = "") -> List[Dict]:
    """Split text into overlapping chunks by character count.
    Used as fallback for text without clear § structure, or for long sections."""
    chunks = []
    start = 0
    chunk_idx = 0
    
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_text = text[start:end].strip()
        
        if len(chunk_text) < 30:  # skip very short trailing chunks
            break
            
        sec_label = prefix_section if prefix_section else ""
        chunks.append({
            "id": f"window_p{page_num}_{chunk_idx}{'_' + sec_label if sec_label else ''}",
            "text": chunk_text,
            "metadata": {
                "page": str(page_num),
                "source": source_name,
                "chunk_type": "text",
                "section": sec_label
            }
        })
        
        start = end - overlap
        chunk_idx += 1
        
        if end >= len(text):
            break
    
    return chunks

def _find_page_for_position(position: int, page_map: Dict[int, str]) -> int:
    """Given a character position in the full text, find which page it belongs to."""
    running_len = 0
    for page_num in sorted(page_map.keys()):
        running_len += len(page_map[page_num]) + 1  # +1 for newline
        if position < running_len:
            return page_num
    return max(page_map.keys()) if page_map else 1

def smart_chunk_pdf(pdf_path: str, source_name: str) -> List[Dict]:
    """Orchestrator: extract tables, split by sections, and apply sliding window.
    Returns a list of chunks with rich metadata."""
    all_chunks = []
    full_text = ""
    page_map = {}  # page_num -> page_text
    
    with pdfplumber.open(pdf_path) as pdf:
        # --- Pass 1: Extract tables ---
        table_chunks = extract_tables_as_chunks(pdf, source_name)
        all_chunks.extend(table_chunks)
        logger.info(f"Extracted {len(table_chunks)} table chunks")
        
        # --- Build full text and page map ---
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                page_map[i + 1] = text
                full_text += text + "\n"
    
    if not full_text.strip():
        return all_chunks  # only tables, or empty PDF
    
    # --- Pass 2: Split by § sections ---
    section_chunks = split_by_sections(full_text, page_map, source_name)
    
    if section_chunks:
        all_chunks.extend(section_chunks)
        logger.info(f"Extracted {len(section_chunks)} section-based chunks")
    else:
        # --- Fallback: No § structure found, use sliding window on full text ---
        logger.info("No § sections detected, falling back to sliding window chunking")
        window_chunks = sliding_window_chunks(full_text, 1, source_name)
        all_chunks.extend(window_chunks)
        logger.info(f"Created {len(window_chunks)} sliding window chunks")
    
    # --- Deduplicate: remove near-identical chunks ---
    seen_texts = set()
    unique_chunks = []
    for chunk in all_chunks:
        # Use first 100 chars as fingerprint for dedup
        fingerprint = chunk["text"][:100].strip()
        if fingerprint not in seen_texts:
            seen_texts.add(fingerprint)
            unique_chunks.append(chunk)
    
    logger.info(f"Total unique chunks: {len(unique_chunks)} "
                f"(tables: {sum(1 for c in unique_chunks if c['metadata']['chunk_type'] == 'table')}, "
                f"sections: {sum(1 for c in unique_chunks if c['metadata']['chunk_type'] == 'section')}, "
                f"text: {sum(1 for c in unique_chunks if c['metadata']['chunk_type'] == 'text')})")
    
    return unique_chunks
