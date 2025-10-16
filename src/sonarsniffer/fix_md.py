import re

# Read the file
with open('POST_PROCESSING_IMPROVEMENTS.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix heading spacing - add blank lines before headings
content = re.sub(r'([^\n])\n(#+ )', r'\1\n\n\2', content)

# Fix list spacing - add blank lines before lists
content = re.sub(r'([^\n])\n(- )', r'\1\n\n\2', content)

# Add language specifiers to code blocks
content = re.sub(r'```\n(//|\.\/)', r'```javascript\n\1', content)
content = re.sub(r'```\n(class|def|def create_web_dashboard)', r'```python\n\1', content)

# Write back
with open('POST_PROCESSING_IMPROVEMENTS.md', 'w', encoding='utf-8') as f:
    f.write(content)

print('Markdown formatting fixed')