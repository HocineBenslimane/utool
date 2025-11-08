#!/usr/bin/env python3
"""
ULP Sorter - Modern GUI
Beautiful Apple-inspired dark theme interface for credential sorting tool
"""

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import json
import os
import sqlite3
import re
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple

# Try to import optional dependencies
try:
    import tldextract
    HAS_TLDEXTRACT = True
except ImportError:
    HAS_TLDEXTRACT = False


# ============================================================================
# CONFIGURATION
# ============================================================================

APP_NAME = "ULP Sorter"
APP_VERSION = "2.0 GUI"
OUTPUT_DIR_PREFIX = "ULP_Output"
DB_NAME = "work.db"
INVALID_LOG = "invalid_lines.txt"
BATCH_SIZE = 5000

# Apple-inspired Dark Theme Colors
COLORS = {
    'bg_primary': '#1c1c1e',      # Main background
    'bg_secondary': '#2c2c2e',    # Panel background
    'bg_tertiary': '#3a3a3c',     # Hover/active
    'accent_blue': '#0a84ff',     # Primary actions
    'accent_green': '#30d158',    # Success/save
    'accent_yellow': '#ffd60a',   # Warning
    'accent_red': '#ff453a',      # Danger
    'text_primary': '#ffffff',    # Main text
    'text_secondary': '#8e8e93',  # Subtle text
    'border': '#48484a',          # Borders
}

# Domain storage path
DOMAIN_STORAGE_PATH = Path.home() / ".ulp_sorter" / "domains.json"


# ============================================================================
# UTILITY FUNCTIONS FROM ORIGINAL TOOL
# ============================================================================

def extract_domain(raw_domain: str) -> str:
    """Extract and normalize domain from various formats."""
    if not raw_domain:
        return ""

    domain = raw_domain.strip().lower()

    # Remove common prefixes
    domain = re.sub(r'^(https?://)?(www\.)?', '', domain)
    domain = re.sub(r'^(m\.)?', '', domain)

    # Handle package names (com.facebook.katana -> facebook.com)
    if '.' in domain and not domain.startswith('http'):
        parts = domain.split('.')
        if len(parts) >= 2 and parts[0] in ['com', 'org', 'net', 'co']:
            return f"{parts[1]}.{parts[0]}"

    # Extract using tldextract if available
    if HAS_TLDEXTRACT:
        try:
            ext = tldextract.extract(domain)
            if ext.domain and ext.suffix:
                return f"{ext.domain}.{ext.suffix}"
        except:
            pass

    # Fallback: simple domain extraction
    domain = domain.split('/')[0].split(':')[0]
    return domain


def is_email(username: str) -> bool:
    """Check if username is an email."""
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', username))


def is_phone_or_number(username: str) -> bool:
    """Check if username is a phone number or numeric ID."""
    # Remove common phone formatting
    cleaned = re.sub(r'[\s\-\(\)\+]', '', username)
    # Check if it's all digits (at least 5 digits for phone numbers)
    return bool(re.match(r'^\d{5,}$', cleaned))


def parse_line(line: str, mode: str) -> Optional[Tuple[str, str, str]]:
    """
    Parse a line and extract domain, username, password.
    Returns (domain, username, password) or None if invalid.
    """
    line = line.strip()
    if not line or line.startswith('#'):
        return None

    # Clean up line
    line = re.sub(r'^[\d\s\-\>]+', '', line)  # Remove line numbers, arrows
    line = re.sub(r'^(https?://)?(www\.)?', '', line)  # Remove URL prefixes

    # Try different separator patterns
    separators = [':', '|', ';', ',', '\t', ' ']

    for sep in separators:
        if sep in line:
            parts = line.split(sep)

            # Try to extract domain, username, password
            if len(parts) >= 3:
                # Format: domain:user:pass or service:user:pass
                domain_candidate = parts[0].strip()
                username = parts[1].strip()
                password = sep.join(parts[2:]).strip()  # Password might contain separator

                if username and password:
                    domain = extract_domain(domain_candidate)
                    if domain and filter_username(username, mode):
                        return (domain, username, password)

            if len(parts) == 2:
                # Format: user:pass (extract domain from email)
                username = parts[0].strip()
                password = parts[1].strip()

                if username and password:
                    if '@' in username:
                        domain = username.split('@')[1]
                        domain = extract_domain(domain)
                        if domain and filter_username(username, mode):
                            return (domain, username, password)

    return None


def filter_username(username: str, mode: str) -> bool:
    """Filter username based on selected mode."""
    if mode == 'any':
        return True
    elif mode == 'email':
        return is_email(username)
    elif mode == 'phone':
        return is_phone_or_number(username)
    elif mode == 'all':
        return is_email(username) or is_phone_or_number(username)
    return False


def load_domains() -> List[str]:
    """Load saved domains from storage."""
    try:
        if DOMAIN_STORAGE_PATH.exists():
            with open(DOMAIN_STORAGE_PATH, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
    except:
        pass
    return []


def save_domains(domains: List[str]):
    """Save domains to storage."""
    try:
        DOMAIN_STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(DOMAIN_STORAGE_PATH, 'w') as f:
            json.dump(domains, f, indent=2)
    except Exception as e:
        raise Exception(f"Failed to save domains: {e}")


# ============================================================================
# MAIN GUI APPLICATION
# ============================================================================

class ULPSorterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry("900x800")
        self.root.configure(bg=COLORS['bg_primary'])

        # State variables
        self.selected_file = tk.StringVar(value="")
        self.file_size = tk.StringVar(value="")
        self.sort_mode = tk.StringVar(value="email")
        self.progress_var = tk.DoubleVar(value=0)
        self.status_text = tk.StringVar(value="Ready to process")
        self.is_processing = False

        # Create UI
        self.create_ui()

    def create_ui(self):
        """Create the main UI layout."""
        # Main container with padding
        main_container = tk.Frame(self.root, bg=COLORS['bg_primary'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Create scrollable canvas
        canvas = tk.Canvas(main_container, bg=COLORS['bg_primary'], highlightthickness=0)
        scrollbar = tk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=COLORS['bg_primary'])

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Build sections
        self.create_header(scrollable_frame)
        self.create_file_selection(scrollable_frame)
        self.create_sorting_mode(scrollable_frame)
        self.create_domain_management(scrollable_frame)
        self.create_action_panel(scrollable_frame)
        self.create_results_display(scrollable_frame)

    # ------------------------------------------------------------------------
    # HEADER SECTION
    # ------------------------------------------------------------------------

    def create_header(self, parent):
        """Create the header with app title and description."""
        header = tk.Frame(parent, bg=COLORS['bg_secondary'], pady=20)
        header.pack(fill=tk.X, pady=(0, 20))

        # Title with icon
        title_frame = tk.Frame(header, bg=COLORS['bg_secondary'])
        title_frame.pack()

        title = tk.Label(
            title_frame,
            text=f"⚡ {APP_NAME}",
            font=("SF Pro Display", 32, "bold"),
            fg=COLORS['text_primary'],
            bg=COLORS['bg_secondary']
        )
        title.pack()

        subtitle = tk.Label(
            header,
            text="Parse • Deduplicate • Organize Credentials",
            font=("SF Pro Text", 12),
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_secondary']
        )
        subtitle.pack(pady=(5, 0))

    # ------------------------------------------------------------------------
    # FILE SELECTION SECTION
    # ------------------------------------------------------------------------

    def create_file_selection(self, parent):
        """Create file selection panel."""
        panel = self.create_panel(parent, "📁 File Selection")

        # Browse button
        browse_btn = self.create_button(
            panel,
            text="Browse Files",
            command=self.browse_file,
            bg=COLORS['accent_blue'],
            width=30
        )
        browse_btn.pack(pady=10)

        # File info display
        file_info_frame = tk.Frame(panel, bg=COLORS['bg_secondary'])
        file_info_frame.pack(fill=tk.X, pady=10)

        self.file_label = tk.Label(
            file_info_frame,
            textvariable=self.selected_file,
            font=("SF Mono", 10),
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_secondary'],
            wraplength=800
        )
        self.file_label.pack()

        self.size_label = tk.Label(
            file_info_frame,
            textvariable=self.file_size,
            font=("SF Mono", 9),
            fg=COLORS['accent_blue'],
            bg=COLORS['bg_secondary']
        )
        self.size_label.pack()

    # ------------------------------------------------------------------------
    # SORTING MODE SECTION
    # ------------------------------------------------------------------------

    def create_sorting_mode(self, parent):
        """Create sorting mode selection panel."""
        panel = self.create_panel(parent, "🎯 Sorting Mode")

        modes = [
            ("email", "Email Only", "Only email:password pairs"),
            ("phone", "Phone/Number", "Only phone numbers or numeric IDs"),
            ("all", "All Types", "Email, phone, or numeric IDs"),
            ("any", "Any Username", "All usernames without filtering")
        ]

        for value, label, desc in modes:
            mode_frame = tk.Frame(panel, bg=COLORS['bg_secondary'])
            mode_frame.pack(fill=tk.X, pady=5, padx=10)

            rb = tk.Radiobutton(
                mode_frame,
                text=label,
                variable=self.sort_mode,
                value=value,
                font=("SF Pro Text", 11, "bold"),
                fg=COLORS['text_primary'],
                bg=COLORS['bg_secondary'],
                selectcolor=COLORS['bg_tertiary'],
                activebackground=COLORS['bg_secondary'],
                activeforeground=COLORS['accent_blue'],
                borderwidth=0,
                highlightthickness=0
            )
            rb.pack(anchor=tk.W)

            desc_label = tk.Label(
                mode_frame,
                text=f"  └─ {desc}",
                font=("SF Pro Text", 9),
                fg=COLORS['text_secondary'],
                bg=COLORS['bg_secondary']
            )
            desc_label.pack(anchor=tk.W, padx=(20, 0))

    # ------------------------------------------------------------------------
    # DOMAIN MANAGEMENT SECTION
    # ------------------------------------------------------------------------

    def create_domain_management(self, parent):
        """Create domain management panel."""
        panel = self.create_panel(parent, "🌐 Domain Filter")

        # Instructions
        instruction = tk.Label(
            panel,
            text="Enter domains to filter (one per line, leave empty for all domains)",
            font=("SF Pro Text", 10),
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_secondary']
        )
        instruction.pack(pady=(0, 10))

        # Text input area
        text_frame = tk.Frame(panel, bg=COLORS['border'], padx=1, pady=1)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        inner_frame = tk.Frame(text_frame, bg=COLORS['bg_tertiary'])
        inner_frame.pack(fill=tk.BOTH, expand=True)

        self.domain_text = scrolledtext.ScrolledText(
            inner_frame,
            height=8,
            font=("SF Mono", 10),
            bg=COLORS['bg_tertiary'],
            fg=COLORS['text_primary'],
            insertbackground=COLORS['accent_blue'],
            selectbackground=COLORS['accent_blue'],
            selectforeground=COLORS['text_primary'],
            borderwidth=0,
            highlightthickness=0,
            relief=tk.FLAT
        )
        self.domain_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Buttons
        btn_frame = tk.Frame(panel, bg=COLORS['bg_secondary'])
        btn_frame.pack(fill=tk.X, pady=10)

        load_btn = self.create_button(
            btn_frame,
            text="Load Saved",
            command=self.load_saved_domains,
            bg=COLORS['bg_tertiary'],
            width=15
        )
        load_btn.pack(side=tk.LEFT, padx=5)

        save_btn = self.create_button(
            btn_frame,
            text="💾 Save Domains",
            command=self.save_current_domains,
            bg=COLORS['accent_green'],
            width=15
        )
        save_btn.pack(side=tk.LEFT, padx=5)

    # ------------------------------------------------------------------------
    # ACTION PANEL SECTION
    # ------------------------------------------------------------------------

    def create_action_panel(self, parent):
        """Create action panel with start button and progress."""
        panel = self.create_panel(parent, "▶ Actions")

        # Start button
        self.start_btn = self.create_button(
            panel,
            text="▶ Start Processing",
            command=self.start_processing,
            bg=COLORS['accent_blue'],
            width=30,
            height=2
        )
        self.start_btn.pack(pady=15)

        # Progress bar
        progress_frame = tk.Frame(panel, bg=COLORS['bg_secondary'])
        progress_frame.pack(fill=tk.X, pady=10, padx=20)

        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate',
            length=400
        )
        self.progress_bar.pack(fill=tk.X)

        # Style the progress bar
        style = ttk.Style()
        style.theme_use('default')
        style.configure(
            "TProgressbar",
            troughcolor=COLORS['bg_tertiary'],
            background=COLORS['accent_green'],
            borderwidth=0,
            thickness=8
        )

        # Status label
        self.status_label = tk.Label(
            panel,
            textvariable=self.status_text,
            font=("SF Pro Text", 11),
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_secondary']
        )
        self.status_label.pack(pady=10)

    # ------------------------------------------------------------------------
    # RESULTS DISPLAY SECTION
    # ------------------------------------------------------------------------

    def create_results_display(self, parent):
        """Create results display panel."""
        panel = self.create_panel(parent, "📊 Results")

        # Results text area
        text_frame = tk.Frame(panel, bg=COLORS['border'], padx=1, pady=1)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        inner_frame = tk.Frame(text_frame, bg=COLORS['bg_primary'])
        inner_frame.pack(fill=tk.BOTH, expand=True)

        self.results_text = scrolledtext.ScrolledText(
            inner_frame,
            height=12,
            font=("SF Mono", 9),
            bg=COLORS['bg_primary'],
            fg=COLORS['text_primary'],
            borderwidth=0,
            highlightthickness=0,
            relief=tk.FLAT,
            state=tk.DISABLED
        )
        self.results_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    # ------------------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------------------

    def create_panel(self, parent, title):
        """Create a rounded panel with title."""
        # Container for rounded effect
        container = tk.Frame(parent, bg=COLORS['bg_primary'])
        container.pack(fill=tk.BOTH, expand=True, pady=10)

        # Title
        title_label = tk.Label(
            container,
            text=title,
            font=("SF Pro Display", 16, "bold"),
            fg=COLORS['text_primary'],
            bg=COLORS['bg_primary']
        )
        title_label.pack(anchor=tk.W, pady=(0, 8))

        # Panel frame
        panel = tk.Frame(container, bg=COLORS['bg_secondary'], padx=20, pady=15)
        panel.pack(fill=tk.BOTH, expand=True)

        return panel

    def create_button(self, parent, text, command, bg, width=20, height=1):
        """Create a styled button."""
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=("SF Pro Text", 12, "bold"),
            fg=COLORS['text_primary'],
            bg=bg,
            activebackground=self.adjust_brightness(bg, 1.2),
            activeforeground=COLORS['text_primary'],
            borderwidth=0,
            highlightthickness=0,
            relief=tk.FLAT,
            cursor="hand2",
            width=width,
            height=height
        )

        # Hover effects
        btn.bind("<Enter>", lambda e: btn.configure(bg=self.adjust_brightness(bg, 1.2)))
        btn.bind("<Leave>", lambda e: btn.configure(bg=bg))

        return btn

    def adjust_brightness(self, hex_color, factor):
        """Adjust color brightness for hover effects."""
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r = min(255, int(r * factor))
        g = min(255, int(g * factor))
        b = min(255, int(b * factor))
        return f'#{r:02x}{g:02x}{b:02x}'

    # ------------------------------------------------------------------------
    # ACTION HANDLERS
    # ------------------------------------------------------------------------

    def browse_file(self):
        """Open file dialog to select input file."""
        filename = filedialog.askopenfilename(
            title="Select Credential File",
            filetypes=[
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ]
        )

        if filename:
            self.selected_file.set(f"Selected: {filename}")
            # Get file size
            size = os.path.getsize(filename)
            size_mb = size / (1024 * 1024)
            self.file_size.set(f"Size: {size_mb:.2f} MB")

    def load_saved_domains(self):
        """Load saved domains into text area."""
        domains = load_domains()
        if domains:
            self.domain_text.delete(1.0, tk.END)
            self.domain_text.insert(1.0, '\n'.join(domains))
            self.update_status(f"Loaded {len(domains)} domains", COLORS['accent_green'])
        else:
            self.update_status("No saved domains found", COLORS['accent_yellow'])

    def save_current_domains(self):
        """Save current domains from text area."""
        text = self.domain_text.get(1.0, tk.END).strip()
        if text:
            domains = [d.strip() for d in text.split('\n') if d.strip()]
            try:
                save_domains(domains)
                self.update_status(f"Saved {len(domains)} domains", COLORS['accent_green'])
            except Exception as e:
                self.update_status(f"Error saving: {e}", COLORS['accent_red'])
        else:
            self.update_status("No domains to save", COLORS['accent_yellow'])

    def start_processing(self):
        """Start processing the selected file."""
        if self.is_processing:
            self.update_status("Already processing...", COLORS['accent_yellow'])
            return

        # Validate file selection
        file_path = self.selected_file.get().replace("Selected: ", "")
        if not file_path or not os.path.exists(file_path):
            self.update_status("Please select a valid file", COLORS['accent_red'])
            return

        # Get domains filter
        domain_text = self.domain_text.get(1.0, tk.END).strip()
        domain_filter = [d.strip() for d in domain_text.split('\n') if d.strip()] if domain_text else None

        # Disable button
        self.is_processing = True
        self.start_btn.configure(state=tk.DISABLED, text="Processing...")

        # Run processing in thread
        thread = threading.Thread(
            target=self.process_file,
            args=(file_path, self.sort_mode.get(), domain_filter),
            daemon=True
        )
        thread.start()

    def process_file(self, file_path, mode, domain_filter):
        """Process the credential file (runs in separate thread)."""
        try:
            # Create output directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path(f"{OUTPUT_DIR_PREFIX}_{timestamp}")
            output_dir.mkdir(exist_ok=True)

            # Initialize database
            db_path = output_dir / DB_NAME
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Create table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entries (
                    domain TEXT NOT NULL,
                    username TEXT NOT NULL,
                    password TEXT NOT NULL,
                    cnt INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (domain, username, password)
                )
            """)

            # Performance settings
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")

            conn.commit()

            # Process file
            total_lines = 0
            processed = 0
            invalid = 0
            batch = []

            self.update_status("Reading file...", COLORS['accent_blue'])

            # Count total lines for progress
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                total_lines = sum(1 for _ in f)

            # Process lines
            invalid_lines = []

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f):
                    result = parse_line(line, mode)

                    if result:
                        domain, username, password = result

                        # Apply domain filter if specified
                        if domain_filter and domain not in domain_filter:
                            continue

                        batch.append((domain, username, password))
                        processed += 1

                        # Batch insert
                        if len(batch) >= BATCH_SIZE:
                            cursor.executemany(
                                """INSERT INTO entries (domain, username, password, cnt)
                                   VALUES (?, ?, ?, 1)
                                   ON CONFLICT(domain, username, password)
                                   DO UPDATE SET cnt = cnt + 1""",
                                batch
                            )
                            conn.commit()
                            batch.clear()
                    else:
                        invalid += 1
                        invalid_lines.append(line)

                    # Update progress
                    if i % 1000 == 0:
                        progress = (i / total_lines) * 100
                        self.progress_var.set(progress)
                        self.update_status(
                            f"Processing: {i}/{total_lines} lines ({processed} valid, {invalid} invalid)",
                            COLORS['accent_blue']
                        )

            # Insert remaining batch
            if batch:
                cursor.executemany(
                    """INSERT INTO entries (domain, username, password, cnt)
                       VALUES (?, ?, ?, 1)
                       ON CONFLICT(domain, username, password)
                       DO UPDATE SET cnt = cnt + 1""",
                    batch
                )
                conn.commit()

            # Write invalid lines
            if invalid_lines:
                with open(output_dir / INVALID_LOG, 'w', encoding='utf-8') as f:
                    f.writelines(invalid_lines)

            # Export by domain
            self.update_status("Exporting by domain...", COLORS['accent_blue'])

            cursor.execute("SELECT DISTINCT domain FROM entries ORDER BY domain")
            domains = [row[0] for row in cursor.fetchall()]

            stats = []

            for domain in domains:
                cursor.execute(
                    "SELECT username, password FROM entries WHERE domain = ? ORDER BY username",
                    (domain,)
                )
                entries = cursor.fetchall()

                # Write domain file
                domain_file = output_dir / f"{domain}.txt"
                with open(domain_file, 'w', encoding='utf-8') as f:
                    for username, password in entries:
                        f.write(f"{username}:{password}\n")

                stats.append((domain, len(entries)))

            # Get total unique entries
            cursor.execute("SELECT COUNT(*) FROM entries")
            total_unique = cursor.fetchone()[0]

            cursor.execute("SELECT SUM(cnt) FROM entries")
            total_with_dupes = cursor.fetchone()[0]

            duplicates = total_with_dupes - total_unique

            conn.close()

            # Save domain filter used
            if domain_filter:
                with open(output_dir / "domains_used.json", 'w') as f:
                    json.dump(domain_filter, f, indent=2)

            # Update UI with results
            self.progress_var.set(100)
            self.update_status("Processing complete!", COLORS['accent_green'])
            self.display_results(output_dir, stats, total_unique, duplicates, processed, invalid)

        except Exception as e:
            self.update_status(f"Error: {e}", COLORS['accent_red'])

        finally:
            self.is_processing = False
            self.root.after(0, lambda: self.start_btn.configure(state=tk.NORMAL, text="▶ Start Processing"))

    def update_status(self, message, color=None):
        """Update status message."""
        self.status_text.set(message)
        if color:
            self.root.after(0, lambda: self.status_label.configure(fg=color))

    def display_results(self, output_dir, stats, total_unique, duplicates, processed, invalid):
        """Display processing results."""
        self.results_text.configure(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)

        # Header
        self.results_text.insert(tk.END, "═" * 80 + "\n")
        self.results_text.insert(tk.END, "PROCESSING COMPLETE\n", "header")
        self.results_text.insert(tk.END, "═" * 80 + "\n\n")

        # Summary
        self.results_text.insert(tk.END, f"📁 Output Directory: {output_dir}\n\n")
        self.results_text.insert(tk.END, f"📊 Statistics:\n")
        self.results_text.insert(tk.END, f"   • Total Processed: {processed:,}\n")
        self.results_text.insert(tk.END, f"   • Unique Entries: {total_unique:,}\n")
        self.results_text.insert(tk.END, f"   • Duplicates Removed: {duplicates:,}\n")
        self.results_text.insert(tk.END, f"   • Invalid Lines: {invalid:,}\n")
        self.results_text.insert(tk.END, f"   • Domains Found: {len(stats)}\n\n")

        # Domain breakdown
        self.results_text.insert(tk.END, "🌐 Domain Breakdown:\n")
        self.results_text.insert(tk.END, "─" * 80 + "\n")

        for domain, count in sorted(stats, key=lambda x: x[1], reverse=True):
            self.results_text.insert(tk.END, f"   {domain:40} {count:>10,} entries\n")

        self.results_text.insert(tk.END, "─" * 80 + "\n")

        self.results_text.configure(state=tk.DISABLED)

        # Configure tag
        self.results_text.tag_configure("header", font=("SF Mono", 11, "bold"))


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point for the GUI application."""
    root = tk.Tk()
    app = ULPSorterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
