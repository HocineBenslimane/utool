# ULP Sorter - Credential Processing Tool

A modern, beautiful GUI application for processing and organizing leaked credential dumps for breach monitoring SaaS services.

## 🎨 Features

### Modern Apple-Inspired GUI
- **Dark Theme**: Sleek black/dark gray color scheme
- **Smooth Animations**: Progress bars and hover effects
- **Intuitive Layout**: Clean, organized interface sections
- **Responsive Design**: Scrollable interface that adapts to content

### Core Functionality
- **Multi-Format Parsing**: Supports `:`, `|`, `;`, `,`, tab, and space separators
- **Smart Domain Extraction**: Intelligent domain parsing with tldextract
- **Credential Filtering**: Email, phone, numeric ID, or all username types
- **SQLite Deduplication**: Automatic duplicate removal with statistics
- **Batch Processing**: Efficient handling of large files
- **Domain Filtering**: Process only specific domains of interest

## 🚀 Usage

### Running the GUI

```bash
python3 ulptool_gui.py
```

Or simply:
```bash
./ulptool_gui.py
```

### Dependencies

**Required:**
- Python 3.6+
- tkinter (usually included with Python)

**Optional (for better domain extraction):**
```bash
pip install tldextract
```

### Using the Interface

1. **📁 File Selection**
   - Click "Browse Files" to select your credential dump file
   - File size will be displayed after selection

2. **🎯 Sorting Mode**
   - **Email Only**: Filter only email:password pairs
   - **Phone/Number**: Filter only phone numbers or numeric IDs
   - **All Types**: Include email, phone, or numeric IDs
   - **Any Username**: Process all usernames without filtering

3. **🌐 Domain Filter**
   - Enter domains you want to extract (one per line)
   - Leave empty to process all domains
   - Click "Load Saved" to load previously saved domains
   - Click "💾 Save Domains" to save current list for future use

4. **▶ Start Processing**
   - Click "▶ Start Processing" to begin
   - Watch the progress bar and status updates
   - Results will appear in the bottom panel when complete

### Output

The tool creates a timestamped directory: `ULP_Output_YYYYMMDD_HHMMSS/`

Contains:
- `work.db` - SQLite database with all processed credentials
- `{domain}.txt` - Separate file for each domain (format: `username:password`)
- `invalid_lines.txt` - Lines that couldn't be parsed
- `domains_used.json` - Copy of domain filter used (if applicable)

### Results Display

The results panel shows:
- 📁 Output directory path
- 📊 Processing statistics (total processed, unique entries, duplicates removed)
- 🌐 Domain breakdown with entry counts per domain

## 🔒 Security & Privacy

### Legitimate Use Cases
This tool is designed for:
- Breach monitoring SaaS services
- Security research and analysis
- Helping customers detect if their credentials appear in data breaches
- Defensive security operations

### Important Notes
- Always handle credential data securely
- Implement encryption at rest for production use
- Follow GDPR and privacy regulations
- Only process data you're authorized to handle
- Consider hashing credentials instead of storing plaintext

## 📝 Command-Line Version

The original command-line version is available in `ulptoolui.py` for batch processing and automation.

## 🎯 For SaaS Integration

To integrate this into a breach monitoring SaaS:

1. **Customer Matching**: Add customer database lookup
2. **API Layer**: Build REST endpoints for notifications
3. **Alerting**: Implement email/webhook notifications
4. **Automation**: Set up scheduled breach feed processing
5. **Privacy**: Use hash-based credential comparison
6. **Metadata**: Track breach sources, dates, severity

## 🐛 Troubleshooting

**GUI doesn't open:**
- Ensure tkinter is installed: `sudo apt-get install python3-tk` (Linux)
- Check Python version: `python3 --version` (requires 3.6+)

**Domain extraction issues:**
- Install tldextract: `pip install tldextract`
- Check domain format in input file

**Performance with large files:**
- The tool uses streaming processing and batch inserts
- SQLite WAL mode is enabled for better performance
- Processing happens in a background thread to keep UI responsive

## 📄 License

For educational and authorized security research purposes.

## 👤 Credits

Original tool by @Timo_Ben
GUI version with modern Apple-inspired design

---

**⚠️ Disclaimer**: This tool should only be used for legitimate security purposes with proper authorization. Processing stolen credentials without authorization may violate laws and regulations.
