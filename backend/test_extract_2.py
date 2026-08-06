import fitz
import sys
import json

def test_extract(pdf_path):
    print(f"Opening {pdf_path}")
    doc = fitz.open(pdf_path)
    print(f"Page count: {doc.page_count}")
    
    total_text = ""
    image_count = 0
    
    for page_idx in range(min(doc.page_count, 3)):
        page = doc[page_idx]
        text = page.get_text("text").strip()
        print(f"Page {page_idx} text length: {len(text)}")
        total_text += text
        
        images = page.get_images(full=True)
        print(f"Page {page_idx} image count: {len(images)}")
        image_count += len(images)
        
        # Test dict extraction
        page_dict = page.get_text("dict")
        blocks = page_dict.get("blocks", [])
        text_blocks = [b for b in blocks if b.get("type") == 0]
        img_blocks = [b for b in blocks if b.get("type") == 1]
        print(f"Page {page_idx} dict text blocks: {len(text_blocks)}, image blocks: {len(img_blocks)}")

    print(f"Total extracted text first 3 pages: {len(total_text)} chars")
    
    # Run the _detect_scanned_pdf logic from our extractor
    avg_chars = len(total_text) / min(3, doc.page_count)
    if image_count > 0 and avg_chars < 50:
        print("Our heuristic would say: SCANNED")
    else:
        print("Our heuristic would say: NOT SCANNED")

if __name__ == "__main__":
    test_extract(sys.argv[1])
