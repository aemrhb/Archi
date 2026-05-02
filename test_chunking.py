from hoai_backend import smart_chunk_pdf
chunks = smart_chunk_pdf('test_hoai_ref.pdf', 'test_hoai_ref.pdf')
print(f"Total chunks: {len(chunks)}")
for c in chunks:
    print(f"  {c['id']}: type={c['metadata']['chunk_type']}, section={c['metadata']['section']}, len={len(c['text'])}")
