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

1. First, identify the area/checklist name from the header "Line Clearance Checklist - [Area Name]"
   - Extract only the area name (e.g., "Dispensing Area", "Secondary Packing Area", "Compression Area")
   - This will be used as the table name

2. Start extraction only when the table header appears:
   Equipment Name/ Instrument name | ID no. | Due date of Calibration
   Ignore any content before this header.

3. If the table continues on the next page, treat it as one single table and merge all rows.

4. Ignore page breaks, footers, headers, document metadata, "TRUE COPY", signatures, and stamps.

5. Always output data as a JSON object with this structure:
   {
     "area_name": "extracted area name from header",
     "table_data": [array of arrays with equipment data]
   }

6. Table data must be an array of arrays:
   - First row must be the header exactly as shown.
   - Each following row must contain exactly 3 values.

7. If an equipment has multiple IDs or dates, create one row per ID.

8. Detect parent headings such as (but not limited to):
   - CVC
   - RMG
   - FBD
   - Blister packing / Blister Machine
   - RLAF

9. Parent handling rules:
   - Do NOT include parent rows as standalone data.
   - Prefix each child item with its parent using: Parent - Child
   - If a child belongs to multiple parents, use: Parent1 / Parent2 - Child

10. Preserve handwritten values exactly as written.

11. If ID or Due Date is missing, crossed out, or written as NA:
    - Use "N/A".

12. Do not rename equipment unless required to add parent context.

13. Output must be JSON-safe, clean, and suitable for direct database insertion.

14. Do not explain your reasoning. Return ONLY the JSON object.

Output Format (Example):
{
  "area_name": "Dispensing Area",
  "table_data": [
    ["Equipment Name/ Instrument name","ID no.","Due date of Calibration"],
    ["CVC - Counter Filler","PG-286","25/05/24"],
    ["RMG - Ammeter (Impeller)","AM-234","27/01/25"]
  ]
}
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
            
            # Parse JSON - expecting object with area_name and table_data
            result = json.loads(response_text)
            
            # Extract area name and table data
            area_name = result.get('area_name', 'Equipment Calibration')
            table_array = result.get('table_data', [])
            
            # Format table name: "[Area Name] Checklist"
            if area_name and area_name != 'Equipment Calibration':
                table_name = f"{area_name} Checklist"
            else:
                table_name = 'Equipment Calibration Table'
            
            # Return as structured format for compatibility
            if isinstance(table_array, list) and len(table_array) > 0:
                return {
                    'table_name': table_name,
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
    
    def merge_table_data(self, table_list):
        """
        Merge multiple table data from consecutive pages into one
        
        Args:
            table_list: List of table_data dictionaries
            
        Returns:
            Merged table_data dictionary
        """
        if not table_list:
            return None
        
        if len(table_list) == 1:
            return table_list[0]
        
        # Use first table's name and headers
        merged = {
            'table_name': table_list[0].get('table_name', 'Equipment Calibration Table'),
            'headers': table_list[0].get('headers', []),
            'rows': []
        }
        
        # Combine all rows from all tables
        for table_data in table_list:
            if table_data and 'rows' in table_data:
                merged['rows'].extend(table_data['rows'])
        
        return merged
    
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
        print(f"Processing {len(self.page_numbers)} page groups from PDF")
        print(f"{'='*60}\n")
        
        for page_item in self.page_numbers:
            try:
                # Check if it's a page group (list) or single page (int)
                if isinstance(page_item, list):
                    # Multiple pages - combine into single table
                    print(f"\n--- Processing Page Group {page_item} (Multi-page table) ---")
                    
                    table_list = []
                    for page_num in page_item:
                        print(f"  Extracting page {page_num}...")
                        image = self.extract_page_as_image(page_num)
                        
                        if not image:
                            print(f"  Failed to extract page {page_num}")
                            continue
                        
                        table_data = self.extract_table_from_image(image)
                        if table_data:
                            table_list.append(table_data)
                    
                    if not table_list:
                        print(f"  No tables found in page group {page_item}")
                        continue
                    
                    # Merge all tables into one
                    merged_table = self.merge_table_data(table_list)
                    page_reference = f"{page_item[0]}-{page_item[-1]}"
                    
                    # Generate SQL INSERT
                    sql = self.generate_sql_insert(merged_table, page_reference)
                else:
                    # Single page
                    page_num = page_item
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
                    
                    page_reference = page_num
                    
                    # Generate SQL INSERT
                    sql = self.generate_sql_insert(table_data, page_reference)
                
                if sql:
                    sql_statements.append(sql)
                    if isinstance(page_item, list):
                        print(f"✓ Successfully generated SQL for page group {page_item}")
                        print(f"  Table: {merged_table.get('table_name', 'Unknown')}")
                        print(f"  Combined {len(table_list)} pages into 1 table")
                    else:
                        print(f"✓ Successfully generated SQL for page {page_num}")
                        print(f"  Table: {table_data.get('table_name', 'Unknown')}")
                
            except Exception as e:
                page_ref = page_item if not isinstance(page_item, list) else f"group {page_item}"
                print(f"✗ Error processing page {page_ref}: {str(e)}")
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


def process_folder(content_folder, output_folder, api_key, exp_id=46, exp_batch_no=1):
    """
    Process all PDFs in a folder
    
    Args:
        content_folder: Folder containing PDFs and their .txt files with page numbers
        output_folder: Folder to save output SQL files
        api_key: Gemini API key
        exp_id: Experiment ID
        exp_batch_no: Experiment batch number
    """
    import glob
    
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Find all PDF files in content folder
    pdf_files = glob.glob(os.path.join(content_folder, '*.pdf'))
    
    if not pdf_files:
        print(f"No PDF files found in {content_folder}")
        return
    
    print(f"\n{'='*70}")
    print(f"Found {len(pdf_files)} PDF file(s) to process")
    print(f"{'='*70}\n")
    
    for pdf_path in pdf_files:
        try:
            # Get PDF filename without extension
            pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
            
            # Look for corresponding .txt file with page numbers
            txt_path = os.path.join(content_folder, f"{pdf_name}.txt")
            
            if not os.path.exists(txt_path):
                print(f"⚠ Skipping {pdf_name}.pdf - no corresponding .txt file found")
                continue
            
            # Read page numbers from txt file
            with open(txt_path, 'r') as f:
                content = f.read().strip()
                # Remove comments (lines starting with #)
                lines = [line for line in content.split('\n') if line.strip() and not line.strip().startswith('#')]
                page_numbers_str = ' '.join(lines)  # Join all non-comment lines
                
                # Parse page numbers with grouping support
                # Format: 10,(160,161),345,(348,349,350)
                # Single pages: integers
                # Page groups (multi-page tables): lists of integers
                page_numbers = []
                parts = page_numbers_str.split(',')
                i = 0
                while i < len(parts):
                    part = parts[i].strip()
                    
                    if '(' in part:
                        # Start of a group
                        group = []
                        # Remove opening parenthesis and get first page
                        first_page = part.replace('(', '').strip()
                        if first_page:
                            group.append(int(first_page))
                        
                        # Continue reading until closing parenthesis
                        i += 1
                        while i < len(parts) and ')' not in parts[i]:
                            group.append(int(parts[i].strip()))
                            i += 1
                        
                        # Add last page with closing parenthesis
                        if i < len(parts):
                            last_page = parts[i].replace(')', '').strip()
                            if last_page:
                                group.append(int(last_page))
                        
                        page_numbers.append(group)
                    else:
                        # Single page
                        if part:
                            page_numbers.append(int(part))
                    
                    i += 1
            
            print(f"\n{'='*70}")
            print(f"Processing: {pdf_name}.pdf")
            print(f"Pages: {page_numbers}")
            print(f"{'='*70}")
            
            # Create extractor for this PDF
            extractor = PDFTableExtractor(
                api_key=api_key,
                pdf_path=pdf_path,
                page_numbers=page_numbers
            )
            
            # Process and generate SQL
            output_file = os.path.join(output_folder, f"{pdf_name}.sql")
            sql_statements = extractor.process_all_pages(output_file)
            
            if sql_statements:
                print(f"✓ Successfully processed {pdf_name}.pdf")
                print(f"  Generated {len(sql_statements)} SQL statements")
                print(f"  Saved to: {output_file}\n")
            else:
                print(f"⚠ No tables extracted from {pdf_name}.pdf\n")
                
        except Exception as e:
            print(f"✗ Error processing {pdf_name}.pdf: {str(e)}\n")
            continue
    
    print(f"\n{'='*70}")
    print(f"✓ Batch processing complete!")
    print(f"  Output folder: {output_folder}")
    print(f"{'='*70}\n")


def main():
    """
    Main function to run the PDF table extraction
    """
    from dotenv import load_dotenv
    import config
    
    # Load environment variables
    load_dotenv()
    
    # Configuration
    API_KEY = os.getenv('GEMINI_API_KEY')
    
    # Check if API key is set
    if not API_KEY:
        print("Error: GEMINI_API_KEY environment variable not set")
        print("\nPlease set it in your .env file or using:")
        print("  PowerShell: $env:GEMINI_API_KEY='your-api-key-here'")
        return
    
    # Process all PDFs in the content folder
    process_folder(
        content_folder=config.CONTENT_FOLDER,
        output_folder=config.OUTPUT_FOLDER,
        api_key=API_KEY,
        exp_id=config.EXP_ID,
        exp_batch_no=config.EXP_BATCH_NO
    )


if __name__ == "__main__":
    main()
