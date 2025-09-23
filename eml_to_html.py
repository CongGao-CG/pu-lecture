import os
import email
import re
from email import policy
from email.parser import BytesParser
import html
from pathlib import Path
from patterns import patterns
def anonymize_content(text):
    """Remove or replace specific email addresses for privacy."""
    if not text:
        return text
    
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Clean up any double spaces or brackets left behind
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with single space
    text = re.sub(r'<\s*>', '', text)  # Remove empty angle brackets
    text = re.sub(r'\(\s*\)', '', text)  # Remove empty parentheses
    
    return text.strip()

def extract_email_content(msg):
    """Extract the email content, preferring HTML over plain text."""
    body = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            
            # Skip attachments
            if "attachment" in content_disposition:
                continue
            
            # Prefer HTML content
            if content_type == "text/html":
                try:
                    body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                    # Anonymize content
                    body = anonymize_content(body)
                    return body, True
                except:
                    continue
            
            # Fall back to plain text if no HTML
            elif content_type == "text/plain" and not body:
                try:
                    text_content = part.get_payload(decode=True).decode('utf-8', errors='replace')
                    # Anonymize content
                    text_content = anonymize_content(text_content)
                    # Convert plain text to basic HTML
                    body = f"<pre>{html.escape(text_content)}</pre>"
                except:
                    continue
    else:
        # Single part message
        content_type = msg.get_content_type()
        try:
            content = msg.get_payload(decode=True).decode('utf-8', errors='replace')
            # Anonymize content
            content = anonymize_content(content)
            if content_type == "text/html":
                body = content
            else:
                body = f"<pre>{html.escape(content)}</pre>"
        except:
            body = "<p>Could not decode message content</p>"
    
    return body, False

def eml_to_html(eml_file_path, output_dir):
    """Convert a single .eml file to .html format."""
    try:
        # Read the .eml file
        with open(eml_file_path, 'rb') as f:
            msg = BytesParser(policy=policy.default).parse(f)
        
        # Extract email headers
        subject = msg.get('Subject', 'No Subject')
        from_addr = anonymize_content(msg.get('From', 'Unknown'))
        to_addr = anonymize_content(msg.get('To', 'Unknown'))
        date = msg.get('Date', 'Unknown')
        
        # Extract email body
        body_content, is_html = extract_email_content(msg)
        
        # Create HTML structure
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(subject)}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .email-container {{
            background-color: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .email-header {{
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        .header-field {{
            margin: 8px 0;
            color: #333;
        }}
        .header-label {{
            font-weight: bold;
            color: #666;
            display: inline-block;
            width: 80px;
        }}
        .email-body {{
            line-height: 1.6;
            color: #333;
        }}
        pre {{
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="email-header">
            <div class="header-field">
                <span class="header-label">Subject:</span> {html.escape(subject)}
            </div>
            <div class="header-field">
                <span class="header-label">From:</span> {html.escape(from_addr)}
            </div>
            <div class="header-field">
                <span class="header-label">To:</span> {html.escape(to_addr)}
            </div>
            <div class="header-field">
                <span class="header-label">Date:</span> {html.escape(date)}
            </div>
        </div>
        <div class="email-body">
            {body_content}
        </div>
    </div>
</body>
</html>"""
        
        # Generate output filename
        base_name = Path(eml_file_path).stem
        output_file = os.path.join(output_dir, f"{base_name}.html")
        
        # Write HTML file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return True, output_file
    
    except Exception as e:
        return False, str(e)

def convert_all_eml_files(input_dir, output_dir=None):
    """Convert all .eml files in a directory to .html format."""
    
    # Set output directory
    if output_dir is None:
        output_dir = os.path.join(input_dir, "html_output")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all .eml files
    eml_files = []
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.lower().endswith('.eml'):
                eml_files.append(os.path.join(root, file))
    
    if not eml_files:
        print(f"No .eml files found in {input_dir}")
        return
    
    print(f"Found {len(eml_files)} .eml file(s) to convert")
    
    # Convert each file
    success_count = 0
    failed_files = []
    
    for eml_file in eml_files:
        print(f"Converting: {os.path.basename(eml_file)}...", end=" ")
        success, result = eml_to_html(eml_file, output_dir)
        
        if success:
            print("✓")
            success_count += 1
        else:
            print(f"✗ ({result})")
            failed_files.append((eml_file, result))
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"Conversion complete!")
    print(f"Successfully converted: {success_count}/{len(eml_files)} files")
    print(f"Output directory: {output_dir}")
    
    if failed_files:
        print(f"\nFailed conversions:")
        for file, error in failed_files:
            print(f"  - {os.path.basename(file)}: {error}")

def main():
    # Configure these paths
    input_directory = "email"  # Change this to your email folder path
    output_directory = "html"  # Set to None to create "html_output" in the input directory
    
    # Check if input directory exists
    if not os.path.exists(input_directory):
        print(f"Error: The directory '{input_directory}' does not exist.")
        print("Please update the 'input_directory' variable with the correct path.")
        return
    
    # Run the conversion
    convert_all_eml_files(input_directory, output_directory)

if __name__ == "__main__":
    main()
