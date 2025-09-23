import os
import re
from datetime import datetime
from pathlib import Path

def extract_email_info(html_file_path):
    """Extract subject, from, and date from HTML email file."""
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Initialize variables
        subject = "Unknown"
        from_addr = "Unknown"
        date_str = "Unknown"
        
        # Try to extract from HTML structure using simple string matching
        # Look for patterns in the HTML content
        
        # Extract Subject
        subject_patterns = [
            r'<title>(.*?)</title>',
            r'Subject:</span>\s*(.*?)\s*</div>',
            r'Subject:</span>\s*(.*?)\s*<',
            r'<span class="header-label">Subject:</span>\s*(.*?)\s*</div>',
            r'Subject:\s*(.*?)\s*<',  # Plain text Subject: 
        ]
        for pattern in subject_patterns:
            match = re.search(pattern, content[:5000], re.IGNORECASE | re.DOTALL)
            if match:
                subject = match.group(1).strip()
                # Clean up any HTML entities
                subject = subject.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
                subject = subject.replace('&quot;', '"').replace('&#39;', "'")
                if subject and subject != "Unknown":
                    break
        
        # Extract From
        from_patterns = [
            r'From:</span>\s*(.*?)\s*</div>',
            r'From:</span>\s*(.*?)\s*<',
            r'<span class="header-label">From:</span>\s*(.*?)\s*</div>',
            r'From:\s*(.*?)\s*<',  # Plain text From:
        ]
        for pattern in from_patterns:
            match = re.search(pattern, content[:5000], re.IGNORECASE | re.DOTALL)
            if match:
                from_addr = match.group(1).strip()
                # Clean up any HTML entities
                from_addr = from_addr.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
                from_addr = from_addr.replace('&quot;', '"').replace('&#39;', "'")
                if from_addr and from_addr != "Unknown":
                    break
        
        # Extract Date
        date_patterns = [
            r'Date:</span>\s*(.*?)\s*</div>',
            r'Date:</span>\s*(.*?)\s*<',
            r'<span class="header-label">Date:</span>\s*(.*?)\s*</div>',
            r'Date:\s*(.*?)\s*<',  # Plain text Date:
        ]
        for pattern in date_patterns:
            match = re.search(pattern, content[:5000], re.IGNORECASE | re.DOTALL)
            if match:
                date_str = match.group(1).strip()
                # Clean up any HTML entities
                date_str = date_str.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
                if date_str and date_str != "Unknown":
                    break
        
        # Fallback: Use filename for subject if extraction failed
        filename = os.path.basename(html_file_path)
        if subject == "Unknown" or subject == "No Subject" or not subject or len(subject) < 3:
            # Remove .html extension and use filename as subject
            subject = filename.replace('.html', '')
            # Clean up common email prefixes but preserve content
            subject = re.sub(r'^\[(.*?)\]\s*', r'[\1] ', subject)  # Keep [list-name] but clean spacing
        
        # Get file info
        file_stats = os.stat(html_file_path)
        file_size = file_stats.st_size
        
        return {
            'filename': filename,
            'subject': subject[:150],  # Limit subject length
            'from': from_addr[:100],  # Limit from length
            'date': date_str[:50],  # Limit date length
            'size': file_size,
            'modified': datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M')
        }
    except Exception as e:
        print(f"Error processing {html_file_path}: {e}")
        # Return basic info even if parsing fails
        filename = os.path.basename(html_file_path)
        try:
            file_stats = os.stat(html_file_path)
            return {
                'filename': filename,
                'subject': filename.replace('.html', ''),
                'from': 'Unknown',
                'date': 'Unknown',
                'size': file_stats.st_size,
                'modified': datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M')
            }
        except:
            return None

def format_file_size(size):
    """Convert file size to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

def generate_index_html(html_folder, debug=False):
    """Generate index.html for all HTML files in the folder."""
    
    print(f"Scanning folder: {html_folder}")
    
    # Get all HTML files (excluding index.html itself)
    html_files = []
    for file in os.listdir(html_folder):
        if file.endswith('.html') and file != 'index.html':
            file_path = os.path.join(html_folder, file)
            if debug:
                print(f"\nProcessing: {file}")
            email_info = extract_email_info(file_path)
            if email_info:
                email_info['size_formatted'] = format_file_size(email_info['size'])
                if debug:
                    print(f"  Subject: {email_info['subject'][:50]}...")
                    print(f"  From: {email_info['from'][:50]}...")
                    print(f"  Date: {email_info['date'][:50]}...")
                html_files.append(email_info)
    
    print(f"\nFound {len(html_files)} email files")
    
    # Sort by subject (you can change to sort by date or filename if preferred)
    html_files.sort(key=lambda x: x['subject'].lower())
    
    # Get the folder name for the HTML links
    folder_name = os.path.basename(html_folder) if html_folder != "." else "html"
    
    # Generate email rows for the table
    email_rows = ""
    for idx, email in enumerate(html_files, 1):
        # Update the href to include the folder path
        email_link = f"{folder_name}/{email['filename']}"
        email_rows += f"""
        <tr>
            <td class="index">{idx}</td>
            <td class="subject"><a href="{email_link}">{email['subject']}</a></td>
            <td class="from">{email['from']}</td>
            <td class="date">{email['date']}</td>
            <td class="size">{email['size_formatted']}</td>
        </tr>"""
    
    # Generate HTML content with modern design
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Email Archive - {len(html_files)} Messages</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .header {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        }}
        
        h1 {{
            color: #333;
            font-size: 2rem;
            margin-bottom: 10px;
        }}
        
        .stats {{
            color: #666;
            font-size: 1rem;
        }}
        
        .search-container {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        }}
        
        #searchInput {{
            width: 100%;
            padding: 12px 20px;
            font-size: 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            transition: border-color 0.3s;
        }}
        
        #searchInput:focus {{
            outline: none;
            border-color: #667eea;
        }}
        
        .table-container {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            overflow-x: auto;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        th {{
            background: #f8f9fa;
            padding: 15px 10px;
            text-align: left;
            font-weight: 600;
            color: #333;
            border-bottom: 2px solid #e0e0e0;
            cursor: pointer;
            user-select: none;
            transition: background-color 0.2s;
        }}
        
        th:hover {{
            background: #e9ecef;
        }}
        
        th.sorted-asc::after {{
            content: ' ↑';
            color: #667eea;
        }}
        
        th.sorted-desc::after {{
            content: ' ↓';
            color: #667eea;
        }}
        
        td {{
            padding: 12px 10px;
            border-bottom: 1px solid #f0f0f0;
        }}
        
        tr:hover {{
            background: #f8f9fa;
        }}
        
        .index {{
            color: #999;
            font-size: 0.9rem;
            width: 50px;
        }}
        
        .subject a {{
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
            transition: color 0.2s;
        }}
        
        .subject a:hover {{
            color: #764ba2;
            text-decoration: underline;
        }}
        
        .from {{
            color: #555;
        }}
        
        .date {{
            color: #666;
            font-size: 0.9rem;
        }}
        
        .size {{
            color: #999;
            font-size: 0.9rem;
            text-align: right;
        }}
        
        .no-results {{
            text-align: center;
            padding: 40px;
            color: #999;
            font-size: 1.1rem;
        }}
        
        @media (max-width: 768px) {{
            .header {{
                padding: 20px;
            }}
            
            h1 {{
                font-size: 1.5rem;
            }}
            
            table {{
                font-size: 0.9rem;
            }}
            
            th, td {{
                padding: 8px 5px;
            }}
            
            .size, .index {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📧 Email Archive</h1>
            <div class="stats">Total: {len(html_files)} messages</div>
        </div>
        
        <div class="search-container">
            <input type="text" id="searchInput" placeholder="Search emails by subject, sender, or date...">
        </div>
        
        <div class="table-container">
            <table id="emailTable">
                <thead>
                    <tr>
                        <th onclick="sortTable(0)" class="index">#</th>
                        <th onclick="sortTable(1)" class="subject">Subject</th>
                        <th onclick="sortTable(2)" class="from">From</th>
                        <th onclick="sortTable(3)" class="date">Date</th>
                        <th onclick="sortTable(4)" class="size">Size</th>
                    </tr>
                </thead>
                <tbody id="emailTableBody">
                    {email_rows}
                </tbody>
            </table>
            <div id="noResults" class="no-results" style="display: none;">
                No emails found matching your search.
            </div>
        </div>
    </div>
    
    <script>
        // Search functionality
        document.getElementById('searchInput').addEventListener('keyup', function() {{
            const searchValue = this.value.toLowerCase();
            const tableBody = document.getElementById('emailTableBody');
            const rows = tableBody.getElementsByTagName('tr');
            let visibleCount = 0;
            
            for (let i = 0; i < rows.length; i++) {{
                const row = rows[i];
                const text = row.textContent.toLowerCase();
                
                if (text.includes(searchValue)) {{
                    row.style.display = '';
                    visibleCount++;
                }} else {{
                    row.style.display = 'none';
                }}
            }}
            
            // Show/hide "no results" message
            const noResults = document.getElementById('noResults');
            if (visibleCount === 0) {{
                noResults.style.display = 'block';
                tableBody.style.display = 'none';
            }} else {{
                noResults.style.display = 'none';
                tableBody.style.display = '';
            }}
        }});
        
        // Sort functionality
        let sortOrder = {{}};
        
        function sortTable(columnIndex) {{
            const table = document.getElementById('emailTable');
            const tbody = table.getElementsByTagName('tbody')[0];
            const rows = Array.from(tbody.getElementsByTagName('tr'));
            const headers = table.getElementsByTagName('th');
            
            // Toggle sort order
            if (!sortOrder[columnIndex]) {{
                sortOrder[columnIndex] = 'asc';
            }} else {{
                sortOrder[columnIndex] = sortOrder[columnIndex] === 'asc' ? 'desc' : 'asc';
            }}
            
            // Remove sort indicators from all headers
            for (let h of headers) {{
                h.classList.remove('sorted-asc', 'sorted-desc');
            }}
            
            // Add sort indicator to current header
            headers[columnIndex].classList.add('sorted-' + sortOrder[columnIndex]);
            
            // Sort rows
            rows.sort((a, b) => {{
                const aValue = a.getElementsByTagName('td')[columnIndex].textContent.trim();
                const bValue = b.getElementsByTagName('td')[columnIndex].textContent.trim();
                
                let comparison = 0;
                if (columnIndex === 0 || columnIndex === 4) {{
                    // Numeric sort for index and size
                    comparison = parseFloat(aValue) - parseFloat(bValue);
                }} else {{
                    // String sort for other columns
                    comparison = aValue.localeCompare(bValue);
                }}
                
                return sortOrder[columnIndex] === 'asc' ? comparison : -comparison;
            }});
            
            // Reattach sorted rows
            rows.forEach(row => tbody.appendChild(row));
        }}
    </script>
</body>
</html>"""
    
    # Write the index.html file at the same level as the html folder
    # Get the parent directory of the html folder
    parent_dir = os.path.dirname(html_folder) if os.path.dirname(html_folder) else "."
    output_path = os.path.join(parent_dir, 'index.html')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n{'='*50}")
    print(f"✓ Index file created successfully!")
    print(f"✓ Location: {output_path}")
    print(f"✓ Total emails indexed: {len(html_files)}")
    print(f"\nReady to deploy to Netlify!")
    print(f"Your folder structure:")
    print(f"  📁 {parent_dir}/")
    print(f"    📄 index.html")
    print(f"    📁 {folder_name}/")
    print(f"      📄 {len(html_files)} email files")
    print(f"\nJust drag and drop the parent folder to Netlify.")
    print(f"\nTip: If subjects show 'Unknown', set debug_mode = True in the script to diagnose.")

def main():
    # Path to your html folder
    html_folder = "html"  # Change this to your actual html folder path (e.g., "html", "html_output", "email_html")
    
    # Set to True to see detailed processing info
    debug_mode = False
    
    # Check if the folder exists
    if not os.path.exists(html_folder):
        # Try alternative common folder names
        alternatives = ["html_output", "html", "emails", "email_html"]
        found = False
        for alt in alternatives:
            if os.path.exists(alt):
                html_folder = alt
                found = True
                print(f"Found folder: {alt}")
                break
        
        if not found:
            print(f"Error: The folder '{html_folder}' does not exist.")
            print("Please update the 'html_folder' variable with the correct path.")
            print("Looking for a folder containing your converted HTML email files.")
            return
    
    # Generate the index file
    generate_index_html(html_folder, debug=debug_mode)

if __name__ == "__main__":
    main()