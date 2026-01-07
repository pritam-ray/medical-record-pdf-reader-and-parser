# 📊 Pharmaceutical BMR Table Extractor

Extract equipment calibration tables from pharmaceutical BMR/GMP PDF documents using Google's Gemini AI and generate SQL INSERT statements for database import.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Production-brightgreen.svg)

## 🎯 Features

- **AI-Powered Extraction**: Uses Google Gemini API to intelligently extract table data from scanned PDFs
- **Pharmaceutical Specific**: Designed for BMR/GMP equipment calibration checklists
- **Parent-Child Handling**: Automatically detects and prefixes equipment with parent categories (CVC, RMG, FBD, etc.)
- **Batch Processing**: Extract tables from multiple PDF pages in one run
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
# Path to your PDF file
PDF_PATH = 'content.pdf'

# Page numbers to extract tables from
PAGE_NUMBERS = [10, 160, 345, 348]

# SQL Configuration
EXP_ID = 46
EXP_BATCH_NO = 1

# Output file for SQL queries
OUTPUT_FILE = 'output_queries.sql'
```

## 💻 Usage

### Basic Usage

```bash
python pdf_table_extractor.py
```

### Expected Output

```
============================================================
Processing 4 pages from PDF
============================================================

--- Processing Page 10 ---
Extracting page 10 from PDF...
Analyzing image with Gemini API...
✓ Successfully generated SQL for page 10
  Table: Equipment Calibration Table

--- Processing Page 160 ---
...

============================================================
✓ Generated 4 SQL statements
✓ Saved to: output_queries.sql
============================================================
```

### Programmatic Usage

```python
from pdf_table_extractor import PDFTableExtractor
import os

# Initialize extractor
api_key = os.getenv('GEMINI_API_KEY')
extractor = PDFTableExtractor(
    api_key=api_key,
    pdf_path='content.pdf',
    page_numbers=[10, 160, 345, 348]
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

### "PDF file not found"
- Ensure `content.pdf` is in the project directory
- Or update `PDF_PATH` in `config.py`

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
├── pdf_table_extractor.py    # Main extraction script
├── config.py                  # Configuration settings
├── requirements.txt           # Python dependencies
├── prompt.txt                 # Extraction rules (reference)
├── README.md                  # This file
├── .env                       # API key (not committed)
├── .gitignore                 # Git exclusions
├── content.pdf               # Your PDF file (place here)
└── output_queries.sql        # Generated SQL (output)
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
5. **Historical Data**: Digitize legacy paper-based records

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
