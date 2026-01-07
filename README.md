# 📊 Pharmaceutical BMR Table Extractor

Extract equipment calibration tables from pharmaceutical BMR/GMP PDF documents using Google's Gemini AI and generate SQL INSERT statements for database import.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Production-brightgreen.svg)

## 🎯 Features

- **AI-Powered Extraction**: Uses Google Gemini API to intelligently extract table data from scanned PDFs
- **Pharmaceutical Specific**: Designed for BMR/GMP equipment calibration checklists
- **Parent-Child Handling**: Automatically detects and prefixes equipment with parent categories (CVC, RMG, FBD, etc.)
- **Batch Processing**: Process multiple PDFs from a folder automatically
- **Multi-Page Table Support**: Combine data from tables spanning multiple pages into single INSERT statements
- **SQL Generation**: Automatically generates database-ready INSERT statements
- **Handwriting Support**: Preserves handwritten values exactly as written
- **Error Handling**: Robust N/A handling for missing or crossed-out values

## 📋 Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Extraction Rules](#extraction-rules)
- [Output Format](#output-format)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## 🚀 Installation

### Prerequisites

- Python 3.8 or higher
- Poppler (for PDF processing)
- Google Gemini API key (free)

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/pharmaceutical-bmr-extractor.git
cd pharmaceutical-bmr-extractor
```

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Dependencies:**
- `google-generativeai==0.8.3` - Gemini AI API
- `pdf2image>=1.16.0` - PDF to image conversion
- `Pillow>=10.0.0` - Image processing
- `python-dotenv>=1.0.0` - Environment variable management

### Step 3: Install Poppler (PDF Processing)

**Windows:**
1. Download Poppler from [GitHub Releases](https://github.com/oschwartz10612/poppler-windows/releases/)
2. Extract to `C:\Program Files\poppler-25.12.0\`
3. Add to PATH: `C:\Program Files\poppler-25.12.0\Library\bin`
4. Restart your terminal

**Linux:**
```bash
sudo apt-get install poppler-utils
```

**macOS:**
```bash
brew install poppler
```

### Step 4: Get Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key (free tier available)
3. Copy the API key

### Step 5: Configure Environment

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your-api-key-here
```

## ⚙️ Configuration

Edit `config.py` to customize extraction:

```python
# Folder containing PDFs and their page number files
CONTENT_FOLDER = 'content'

# Output folder for SQL files
OUTPUT_FOLDER = 'outputsql'

# SQL Configuration
EXP_ID = 46
EXP_BATCH_NO = 1
```

### Folder Structure

The tool now supports batch processing of multiple PDFs:

```
project/
├── content/                  # Input folder
│   ├── BSG4001.pdf          # PDF file
│   ├── BSG4001.txt          # Page numbers: 10,160,345,348
│   ├── BSG4002.pdf          # Another PDF
│   ├── BSG4002.txt          # Page numbers: 5,15,25
│   └── ...
├── outputsql/               # Output folder (created automatically)
│   ├── BSG4001.sql          # Generated SQL
│   ├── BSG4002.sql          # Generated SQL
│   └── ...
└── pdf_table_extractor.py   # Main script
```

**Page Number File Format (.txt):**

Each PDF must have a corresponding `.txt` file with the same name containing comma-separated page numbers:

**Simple format (each page = separate table):**
```
10,160,345,348
```

**Grouped format (combine multi-page tables):**
```
10,(160,161),345,348
```

Use parentheses to group pages when a single table continues across multiple pages. For example, `(160,161)` will combine pages 160 and 161 into a single INSERT statement.

See [MULTI_PAGE_TABLES.md](MULTI_PAGE_TABLES.md) for detailed documentation.

## 💻 Usage

### Basic Batch Processing

```bash
python pdf_table_extractor.py
```

This will:
1. Scan the `content/` folder for PDF files
2. For each PDF, read page numbers from the corresponding `.txt` file
3. Extract tables and generate SQL statements
4. Save output to `outputsql/` folder with matching filenames

### Expected Output

**For single-page tables:**
```
--- Processing Page 10 ---
Extracting page 10 from PDF...
Analyzing image with Gemini API...
✓ Successfully generated SQL for page 10
  Table: Dispensing Area Checklist
```

**For multi-page tables (grouped with parentheses):**
```
--- Processing Page Group [160, 161] (Multi-page table) ---
  Extracting page 160...
  Extracting page 161...
✓ Successfully generated SQL for page group [160, 161]
  Table: Compression Area Checklist
  Combined 2 pages into 1 table
```

**Complete batch output:**
```
======================================================================
Found 2 PDF file(s) to process
======================================================================

======================================================================
Processing: BSG4001.pdf
Pages: [10, [160, 161], 345, 348]
======================================================================

✓ Successfully processed BSG4001.pdf
  Generated 4 SQL statements
  Saved to: outputsql\BSG4001.sql

======================================================================
✓ Batch processing complete!
  Output folder: outputsql
======================================================================
```

### Programmatic Usage

```python
from pdf_table_extractor import PDFTableExtractor, process_folder
import os

# Batch process a folder
process_folder(
    content_folder='content',
    output_folder='outputsql',
    api_key=os.getenv('GEMINI_API_KEY'),
    exp_id=46,
    exp_batch_no=1
)

# Or process a single PDF
extractor = PDFTableExtractor(
    api_key=os.getenv('GEMINI_API_KEY'),
    pdf_path='content/BSG4001.pdf',
    page_numbers=[10, [160, 161], 345, 348]  # Note: [160,161] is a grouped page
)

# Process all pages
sql_statements = extractor.process_all_pages('output.sql')

# Access individual statements
for sql in sql_statements:
    print(sql)
```

## 📖 Extraction Rules

The extractor follows strict pharmaceutical BMR/GMP standards:

### Table Format
Extracts only tables with this exact header:
```
Equipment Name/ Instrument name | ID no. | Due date of Calibration
```

### Parent-Child Equipment
- **Detected Parents**: CVC, RMG, FBD, Blister packing, RLAF
- **Format**: `Parent - Child Equipment`
- **Example**: `CVC - Counter Filler`

### Data Quality Rules
✅ Preserves handwritten values exactly  
✅ Uses "N/A" for missing/crossed-out values  
✅ Ignores stamps, signatures, "TRUE COPY" marks  
✅ Merges multi-page tables automatically  
✅ Validates 3-column structure (Equipment, ID, Date)  

### What's Ignored
- Page breaks and footers
- Document metadata
- "TRUE COPY" stamps
- Signatures
- Non-table content

## 📤 Output Format

### Array Structure
```json
[
  ["Equipment Name/ Instrument name", "ID no.", "Due date of Calibration"],
  ["Digital Hygrometer", "DH-2108", "18/11/24"],
  ["CVC - Counter Filler", "PG-286", "25/05/24"],
  ["RMG - Ammeter (Impeller)", "AM-234", "27/01/25"]
]
```

### SQL INSERT Statement
```sql
INSERT INTO experimenttablerecord 
(exp_id, exp_batch_no, exp_step_name, table_name, data_source, 
 investigation_method, table_data, created_on, hash, isDeleted, table_type) 
VALUES (46, 1, 'Equipment-Calibration-Check', 'Equipment Calibration Table', 
 'BMR-PDF-Scan', NULL, 
 '[["Equipment Name/ Instrument name","ID no.","Due date of Calibration"],
   ["Digital Hygrometer","DH-2108","18/11/24"]]',
 '2026-01-07 10:30:00', 'BMR_B1_P10_ABC123', 0, 'Checklist');
```

### Database Schema

The generated SQL is compatible with this table structure:

```sql
CREATE TABLE experimenttablerecord (
    exp_id INT,
    exp_batch_no INT,
    exp_step_name VARCHAR(255),
    table_name VARCHAR(255),
    data_source VARCHAR(255),
    investigation_method VARCHAR(255),
    table_data TEXT,
    created_on DATETIME,
    hash VARCHAR(50),
    isDeleted TINYINT,
    table_type VARCHAR(50)
);
```

## 🔧 Troubleshooting

### "No PDF files found in content"
- Ensure PDFs are in the `content/` folder
- Verify folder name is exactly `content`

### "Skipping ... - no corresponding .txt file found"
- Create a `.txt` file with same name as the PDF
- Example: `BSG4001.pdf` needs `BSG4001.txt`

### "GEMINI_API_KEY not set"
- Create `.env` file with your API key
- Verify: `echo $env:GEMINI_API_KEY` (PowerShell) or `echo $GEMINI_API_KEY` (Linux/Mac)

### "pdf2image error" or "Unable to get page count"
- Poppler not installed or not in PATH
- Restart terminal after adding Poppler to PATH
- Verify: `pdfinfo -v`

### "429 Quota exceeded"
- Free tier limit reached (15 req/min, 1,500 req/day)
- Wait 24 hours or get a new API key
- Check usage: [Google AI Usage](https://ai.dev/usage?tab=rate-limit)

### Multi-page table not combining correctly
- Ensure parentheses are correct: `(10,11)` not `(10-11)`
- Check all pages in group exist in PDF
- See [MULTI_PAGE_TABLES.md](MULTI_PAGE_TABLES.md) for format guide

### Poor table extraction
- Increase DPI in `extract_page_as_image()` (default: 300)
- Ensure PDF pages are high-quality scans
- Verify tables are clearly visible

## 📊 API Limits

**Gemini Free Tier:**
- 15 requests per minute
- 1,500 requests per day
- 1 million tokens per minute

## 🏗️ Project Structure

```
pharmaceutical-bmr-extractor/
├── pdf_table_extractor.py     # Main extraction script
├── config.py                  # Configuration settings
├── requirements.txt           # Python dependencies
├── prompt.txt                 # Extraction rules (reference)
├── README.md                  # Documentation
├── QUICKSTART.md              # Quick start guide
├── MULTI_PAGE_TABLES.md       # Multi-page table documentation
├── .env                       # API key (not committed)
├── .gitignore                 # Git exclusions
├── content/                   # Input folder
│   ├── BSG4001.pdf           # PDF files
│   ├── BSG4001.txt           # Page numbers: 10,(160,161),345,348
│   └── EXAMPLE_PAGES.txt     # Format examples
└── outputsql/                 # Output folder
    ├── BSG4001.sql           # Generated SQL files
    └── ...
```

## 🎨 Customization

### Modify Table Detection

Edit `pdf_table_extractor.py` line 29 to change the model:

```python
self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
```

Available models:
- `gemini-2.5-flash-lite` - Faster, higher free tier limits
- `gemini-2.0-flash` - Balanced performance
- `gemini-2.5-flash` - Most accurate

### Custom SQL Format

Modify `generate_sql_insert()` in `pdf_table_extractor.py` to customize:
- Table type detection
- Hash generation
- Metadata fields

### Extraction Prompt

See `prompt.txt` for the full extraction rules. Modify the prompt in `extract_table_from_image()` for different table formats.

## 📝 Example Use Cases

1. **Pharmaceutical Manufacturing**: Extract equipment calibration data from BMR documents
2. **Quality Assurance**: Digitize GMP compliance checklists
3. **Audit Preparation**: Convert paper records to database format
4. **Batch Processing**: Extract data from multiple batch records automatically
5. **Multi-Page Tables**: Handle large equipment lists spanning multiple pages
6. **Historical Data**: Digitize legacy paper-based records

## 📚 Additional Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Step-by-step guide for beginners
- **[MULTI_PAGE_TABLES.md](MULTI_PAGE_TABLES.md)** - Complete guide on handling tables that span multiple pages
- **[BATCH_PROCESSING.md](BATCH_PROCESSING.md)** - Batch processing implementation details
- **[prompt.txt](prompt.txt)** - Full extraction rules reference

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Google Gemini API for AI-powered extraction
- Poppler for PDF processing
- pdf2image library

## 📞 Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check the [Troubleshooting](#troubleshooting) section
- Review `prompt.txt` for extraction rule details

## 🔗 Links

- [Google Gemini API](https://ai.google.dev/)
- [Poppler Windows Releases](https://github.com/oschwartz10612/poppler-windows/releases/)
- [pdf2image Documentation](https://pypi.org/project/pdf2image/)

---

**Built with ❤️ for pharmaceutical quality assurance**
