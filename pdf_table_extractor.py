import os
import json
from datetime import datetime
from pdf2image import convert_from_path
import google.generativeai as genai
from PIL import Image
import hashlib
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class PDFTableExtractor:
    def __init__(self, api_key, pdf_path, page_numbers):
        """
        Initialize the PDF Table Extractor
        
        Args:
            api_key: Gemini API key
            pdf_path: Path to the PDF file
            page_numbers: List of page numbers to extract tables from
        """
        self.api_key = api_key
        self.pdf_path = pdf_path
        self.page_numbers = page_numbers
        
        # Configure Gemini API
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
        
    def extract_page_as_image(self, page_number):
        """
        Extract a specific page from PDF as an image
        
        Args:
            page_number: Page number to extract (1-indexed)
            
        Returns:
            PIL Image object
        """
        print(f"Extracting page {page_number} from PDF...")
        
        # Convert specific page to image
        images = convert_from_path(
            self.pdf_path,
            first_page=page_number,
            last_page=page_number,
            dpi=300
        )
        
        return images[0] if images else None
    
    def extract_table_from_image(self, image):
        """
        Use Gemini API to extract pharmaceutical BMR/GMP table data from image
        
        Args:
            image: PIL Image object
            
        Returns:
            Extracted table data as array of arrays
        """
        prompt = """You are extracting tabular data from scanned pharmaceutical BMR / GMP documents.

Extraction Rules (STRICT):

1. Start extraction only when the table header appears:
   Equipment Name/ Instrument name | ID no. | Due date of Calibration
   Ignore any content before this header.

2. If the table continues on the next page, treat it as one single table and merge all rows.

3. Ignore page breaks, footers, headers, document metadata, "TRUE COPY", signatures, and stamps.

4. Always output data as an array of arrays:
   - First row must be the header exactly as shown.
   - Each following row must contain exactly 3 values.

5. If an equipment has multiple IDs or dates, create one row per ID.

6. Detect parent headings such as (but not limited to):
   - CVC
   - RMG
   - FBD
   - Blister packing / Blister Machine
   - RLAF

7. Parent handling rules:
   - Do NOT include parent rows as standalone data.
   - Prefix each child item with its parent using: Parent - Child
   - If a child belongs to multiple parents, use: Parent1 / Parent2 - Child

8. Preserve handwritten values exactly as written.

9. If ID or Due Date is missing, crossed out, or written as NA:
   - Use "N/A".

10. Do not rename equipment unless required to add parent context.

11. Output must be JSON-safe, clean, and suitable for direct database insertion.

12. Do not explain your reasoning. Return ONLY the extracted array of arrays.

Output Format (Example):
[
  ["Equipment Name/ Instrument name","ID no.","Due date of Calibration"],
  ["CVC - Counter Filler","PG-286","25/05/24"],
  ["RMG - Ammeter (Impeller)","AM-234","27/01/25"]
]
"""
        
        print("Analyzing image with Gemini API...")
        
        try:
            response = self.model.generate_content([prompt, image])
            
            # Extract the response text
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # Parse JSON - expecting array of arrays
            table_array = json.loads(response_text)
            
            # Return as structured format for compatibility
            if isinstance(table_array, list) and len(table_array) > 0:
                return {
                    'table_name': 'Equipment Calibration Table',
                    'headers': table_array[0] if len(table_array) > 0 else [],
                    'rows': table_array[1:] if len(table_array) > 1 else []
                }
            
            return None
            
        except Exception as e:
            print(f"Error extracting table: {str(e)}")
            return None
    
    def format_table_data(self, table_data):
        """
        Format table data into the structure needed for SQL INSERT
        
        Args:
            table_data: Dictionary with table_name, headers, and rows
            
        Returns:
            Formatted list of lists with headers as first row
        """
        if not table_data:
            return []
        
        # Combine headers and rows
        result = []
        
        if 'headers' in table_data:
            result.append(table_data['headers'])
        
        if 'rows' in table_data:
            result.extend(table_data['rows'])
        
        return result
    
    def generate_hash(self, table_name, page_number):
        """
        Generate a unique hash for the table record
        
        Args:
            table_name: Name of the table
            page_number: Page number
            
        Returns:
            Hash string
        """
        hash_input = f"{table_name}_{page_number}_{datetime.now().timestamp()}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:20].upper()
    
    def generate_sql_insert(self, table_data, page_number, exp_id=46, exp_batch_no=1):
        """
        Generate SQL INSERT statement
        
        Args:
            table_data: Dictionary with table information
            page_number: Page number where table was found
            exp_id: Experiment ID (default: 46)
            exp_batch_no: Experiment batch number (default: 1)
            
        Returns:
            SQL INSERT statement as string
        """
        if not table_data:
            return None
        
        # Extract table name - for pharmaceutical BMR/GMP, use specific naming
        table_name = table_data.get('table_name', 'Dispensing Area Checklist')
        
        # Format the table data array
        formatted_data = self.format_table_data(table_data)
        
        # Escape single quotes in JSON for SQL
        table_data_json = json.dumps(formatted_data).replace("'", "''")
        
        # Generate timestamp
        created_on = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Generate hash in format: BMR_BATCH_PAGE
        hash_value = f"BMR_B{exp_batch_no}_P{page_number}_{hashlib.md5(str(page_number).encode()).hexdigest()[:8].upper()}"
        
        # Table type for pharmaceutical equipment calibration data
        table_type = 'Checklist'
        
        # Step name for pharmaceutical context
        step_name = 'Equipment-Calibration-Check'
        
        # Create SQL INSERT statement
        sql = f"""INSERT INTO experimenttablerecord 
(exp_id, exp_batch_no, exp_step_name, table_name, data_source, investigation_method, table_data, created_on, hash, isDeleted, table_type) 
VALUES ({exp_id}, {exp_batch_no}, '{step_name}', '{table_name}', 'BMR-PDF-Scan', NULL,
 '{table_data_json}',
 '{created_on}', '{hash_value}', 0, '{table_type}');"""
        
        return sql
    
    def process_all_pages(self, output_file='output_queries.sql'):
        """
        Process all specified pages and generate SQL statements
        
        Args:
            output_file: Output file path for SQL statements
            
        Returns:
            List of SQL INSERT statements
        """
        sql_statements = []
        
        print(f"\n{'='*60}")
        print(f"Processing {len(self.page_numbers)} pages from PDF")
        print(f"{'='*60}\n")
        
        for page_num in self.page_numbers:
            try:
                print(f"\n--- Processing Page {page_num} ---")
                
                # Extract page as image
                image = self.extract_page_as_image(page_num)
                
                if not image:
                    print(f"Failed to extract page {page_num}")
                    continue
                
                # Extract table from image
                table_data = self.extract_table_from_image(image)
                
                if not table_data:
                    print(f"No table found on page {page_num}")
                    continue
                
                # Generate SQL INSERT
                sql = self.generate_sql_insert(table_data, page_num)
                
                if sql:
                    sql_statements.append(sql)
                    print(f"✓ Successfully generated SQL for page {page_num}")
                    print(f"  Table: {table_data.get('table_name', 'Unknown')}")
                
            except Exception as e:
                print(f"✗ Error processing page {page_num}: {str(e)}")
                continue
        
        # Save to file
        if sql_statements:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n\n'.join(sql_statements))
            
            print(f"\n{'='*60}")
            print(f"✓ Generated {len(sql_statements)} SQL statements")
            print(f"✓ Saved to: {output_file}")
            print(f"{'='*60}\n")
        
        return sql_statements


def main():
    """
    Main function to run the PDF table extraction
    """
    # Configuration
    API_KEY = os.getenv('GEMINI_API_KEY')  # Set your API key as environment variable
    PDF_PATH = 'content.pdf'  # Your PDF file path
    PAGE_NUMBERS = [10, 160, 345, 348]  # Pages to extract from
    
    # Check if API key is set
    if not API_KEY:
        print("Error: GEMINI_API_KEY environment variable not set")
        print("\nPlease set it using:")
        print("  PowerShell: $env:GEMINI_API_KEY='your-api-key-here'")
        print("  CMD: set GEMINI_API_KEY=your-api-key-here")
        return
    
    # Check if PDF exists
    if not os.path.exists(PDF_PATH):
        print(f"Error: PDF file not found: {PDF_PATH}")
        return
    
    # Create extractor
    extractor = PDFTableExtractor(API_KEY, PDF_PATH, PAGE_NUMBERS)
    
    # Process pages
    sql_statements = extractor.process_all_pages()
    
    # Print summary
    if sql_statements:
        print("\nFirst SQL statement preview:")
        print("-" * 60)
        print(sql_statements[0][:500] + "..." if len(sql_statements[0]) > 500 else sql_statements[0])


if __name__ == "__main__":
    main()
