import os
import email
import re
from email import policy
from email.parser import BytesParser
import html
from pathlib import Path
import base64
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

def extract_images_from_email(msg):
    """Extract inline images from email and return as a dictionary with CID as key."""
    images = {}
    
    for part in msg.walk():
        content_type = part.get_content_type()
        content_disposition = str(part.get("Content-Disposition", ""))
        content_id = part.get("Content-ID", "")
        
        # Check if this is an image
        if content_type.startswith("image/"):
            # Get the image data
            image_data = part.get_payload(decode=True)
            
            if image_data:
                # Convert to base64 data URI
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                data_uri = f"data:{content_type};base64,{image_base64}"
                
                # Store by Content-ID if available
                if content_id:
                    # Remove angle brackets from Content-ID
                    cid = content_id.strip('<>')
                    images[f"cid:{cid}"] = data_uri
                    images[cid] = data_uri  # Store both with and without 'cid:' prefix
                
                # Also store by filename if available
                filename = part.get_filename()
                if filename:
                    images[filename] = data_uri
    
    return images

def clean_image_dimensions(html_content):
    """Remove hardcoded width and height from img tags to preserve aspect ratio."""
    # Pattern to match img tags and remove width/height attributes
    # This preserves the original aspect ratio by letting CSS handle sizing
    
    # Remove width attributes
    html_content = re.sub(r'<img([^>]*?)(\s+width=["\']?\d+[%px]*["\']?)([^>]*?)>', r'<img\1\3>', html_content, flags=re.IGNORECASE)
    # Remove height attributes  
    html_content = re.sub(r'<img([^>]*?)(\s+height=["\']?\d+[%px]*["\']?)([^>]*?)>', r'<img\1\3>', html_content, flags=re.IGNORECASE)
    
    # Also remove style attributes that set width/height
    def clean_style(match):
        img_tag = match.group(0)
        style_match = re.search(r'style=["\']([^"\']*)["\']', img_tag, re.IGNORECASE)
        if style_match:
            style = style_match.group(1)
            # Remove width and height from style
            style = re.sub(r'width\s*:\s*[^;]+;?', '', style, flags=re.IGNORECASE)
            style = re.sub(r'height\s*:\s*[^;]+;?', '', style, flags=re.IGNORECASE)
            style = style.strip().rstrip(';')
            if style:
                img_tag = re.sub(r'style=["\'][^"\']*["\']', f'style="{style}"', img_tag)
            else:
                img_tag = re.sub(r'\s+style=["\'][^"\']*["\']', '', img_tag)
        return img_tag
    
    html_content = re.sub(r'<img[^>]+>', clean_style, html_content, flags=re.IGNORECASE)
    
    return html_content

def replace_cid_references(html_content, images, preserve_dimensions=False):
    """Replace CID references in HTML with base64 data URIs."""
    if not html_content or not images:
        return html_content
    
    # Pattern to match various forms of CID references
    # Matches: src="cid:xxxxx", src='cid:xxxxx', src=cid:xxxxx
    patterns = [
        (r'src=["\']?cid:([^"\'\s>]+)["\']?', r'src="{}"'),
        (r'href=["\']?cid:([^"\'\s>]+)["\']?', r'href="{}"'),
        (r'background=["\']?cid:([^"\'\s>]+)["\']?', r'background="{}"'),
    ]
    
    for pattern, replacement in patterns:
        def replace_match(match):
            cid = match.group(1)
            # Try to find the image with different CID formats
            for key in [f"cid:{cid}", cid]:
                if key in images:
                    return replacement.format(images[key])
            return match.group(0)  # Return original if no match found
        
        html_content = re.sub(pattern, replace_match, html_content, flags=re.IGNORECASE)
    
    # Clean image dimensions to preserve aspect ratio
    if not preserve_dimensions:
        html_content = clean_image_dimensions(html_content)
    
    return html_content

def extract_email_content(msg, preserve_dimensions=False):
    """Extract the email content, preferring HTML over plain text, and handle inline images.
    
    Args:
        msg: Email message object
        preserve_dimensions: If True, keeps original width/height attributes. 
                           If False (default), removes them to preserve aspect ratio.
    """
    body = ""
    images = extract_images_from_email(msg)
    
    if msg.is_multipart():
        html_body = ""
        plain_body = ""
        
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            
            # Skip explicit attachments (but not inline images)
            if "attachment" in content_disposition and not content_type.startswith("image/"):
                continue
            
            # Collect HTML content
            if content_type == "text/html":
                try:
                    html_body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                    # Replace CID references with embedded images
                    html_body = replace_cid_references(html_body, images, preserve_dimensions)
                    # Anonymize content
                    html_body = anonymize_content(html_body)
                except:
                    continue
            
            # Collect plain text as fallback
            elif content_type == "text/plain" and not plain_body:
                try:
                    plain_body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                    # Anonymize content
                    plain_body = anonymize_content(plain_body)
                except:
                    continue
        
        # Prefer HTML over plain text
        if html_body:
            body = html_body
        elif plain_body:
            # Convert plain text to basic HTML
            body = f"<pre>{html.escape(plain_body)}</pre>"
        else:
            body = "<p>No readable content found</p>"
    else:
        # Single part message
        content_type = msg.get_content_type()
        try:
            content = msg.get_payload(decode=True).decode('utf-8', errors='replace')
            if content_type == "text/html":
                # Replace CID references with embedded images
                content = replace_cid_references(content, images, preserve_dimensions)
            # Anonymize content
            content = anonymize_content(content)
            if content_type == "text/html":
                body = content
            else:
                body = f"<pre>{html.escape(content)}</pre>"
        except:
            body = "<p>Could not decode message content</p>"
    
    return body

def extract_attachments_info(msg):
    """Extract information about non-inline attachments."""
    attachments = []
    
    for part in msg.walk():
        content_disposition = str(part.get("Content-Disposition", ""))
        
        # Look for explicit attachments (not inline)
        if "attachment" in content_disposition:
            filename = part.get_filename()
            if filename:
                content_type = part.get_content_type()
                # Skip images that might be inline
                if not content_type.startswith("image/") or "inline" not in content_disposition:
                    attachments.append({
                        'filename': filename,
                        'type': content_type,
                        'size': len(part.get_payload(decode=True)) if part.get_payload(decode=True) else 0
                    })
    
    return attachments

def eml_to_html(eml_file_path, output_dir, preserve_dimensions=False):
    """Convert a single .eml file to .html format with embedded images.
    
    Args:
        eml_file_path: Path to the .eml file
        output_dir: Directory to save the HTML file
        preserve_dimensions: If True, keeps original width/height attributes.
                           If False (default), removes them to preserve aspect ratio.
    """
    try:
        # Read the .eml file
        with open(eml_file_path, 'rb') as f:
            msg = BytesParser(policy=policy.default).parse(f)
        
        # Extract email headers
        subject = msg.get('Subject', 'No Subject')
        from_addr = anonymize_content(msg.get('From', 'Unknown'))
        to_addr = anonymize_content(msg.get('To', 'Unknown'))
        date = msg.get('Date', 'Unknown')
        
        # Extract email body with embedded images
        body_content = extract_email_content(msg, preserve_dimensions)
        
        # Extract attachment information
        attachments = extract_attachments_info(msg)
        
        # Create attachments HTML section if there are attachments
        attachments_html = ""
        if attachments:
            attachments_html = """
        <div class="attachments">
            <h3>Attachments:</h3>
            <ul>
"""
            for att in attachments:
                size_kb = att['size'] / 1024
                attachments_html += f"""                <li>{html.escape(att['filename'])} ({att['type']}, {size_kb:.1f} KB)</li>
"""
            attachments_html += """            </ul>
        </div>"""
        
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
            max-width: 900px;
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
        .email-body img {{
            /* Allow images to display at natural size up to container width */
            max-width: 100%;
            height: auto;
            display: inline-block;
            margin: 10px auto;
        }}
        /* Ensure images in tables also respect aspect ratio */
        .email-body table {{
            max-width: 100%;
        }}
        .email-body table img {{
            max-width: 100%;
            height: auto;
        }}
        /* Center images that are smaller than container */
        .email-body p > img,
        .email-body div > img {{
            display: block;
            margin-left: auto;
            margin-right: auto;
        }}
        pre {{
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .attachments {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
        }}
        .attachments h3 {{
            color: #666;
            font-size: 14px;
            margin-bottom: 10px;
        }}
        .attachments ul {{
            list-style-type: none;
            padding-left: 0;
        }}
        .attachments li {{
            padding: 5px 0;
            color: #666;
            font-size: 13px;
        }}
        .attachments li:before {{
            content: "📎 ";
            margin-right: 5px;
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
        {attachments_html}
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

def convert_all_eml_files(input_dir, output_dir=None, preserve_dimensions=False):
    """Convert all .eml files in a directory to .html format.
    
    Args:
        input_dir: Directory containing .eml files
        output_dir: Directory to save HTML files (optional)
        preserve_dimensions: If True, keeps original width/height attributes.
                           If False (default), removes them to preserve aspect ratio.
    """
    
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
    print(f"Image dimension handling: {'Preserving original' if preserve_dimensions else 'Auto-adjusting for aspect ratio'}")
    
    # Convert each file
    success_count = 0
    failed_files = []
    
    for eml_file in eml_files:
        print(f"Converting: {os.path.basename(eml_file)}...", end=" ")
        success, result = eml_to_html(eml_file, output_dir, preserve_dimensions)
        
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
    
    # Configuration options
    preserve_dimensions = False  # Set to True to keep original image dimensions
                                # Set to False to auto-adjust for proper aspect ratio
    
    # Check if input directory exists
    if not os.path.exists(input_directory):
        print(f"Error: The directory '{input_directory}' does not exist.")
        print("Please update the 'input_directory' variable with the correct path.")
        return
    
    # Run the conversion
    convert_all_eml_files(input_directory, output_directory, preserve_dimensions)

if __name__ == "__main__":
    main()
