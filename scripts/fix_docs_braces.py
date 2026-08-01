"""Fix extra closing braces in docs.py."""
import re

with open('baitcoin_explorer/docs.py', 'r') as f:
    content = f.read()

# Pattern: ...Response'}}}}  should be ...Response'}}}
# The content dict structure is:
#   "content": {"application/json": {"schema": {"$ref": "..."}}}
# That's 3 opens, 3 closes.
# But some lines have 4 closes.

# Replace all occurrences of Response'}}}} (4 closes) with Response'}}}' (3 closes)
old = "Response'}}}}"
new = "Response'}}}'"
count = content.count(old)
content = content.replace(old, new)

# Also fix 'type': "object"}}}} and 'type': "string"}}}}
for pattern, replacement in [
    ('"type": "object"}}}}', '"type": "object"}}}'),
    ('"type": "string"}}}}', '"type": "string"}}}'),
    ('"type": "array"}}}}', '"type": "array"}}}'),
]:
    c = content.count(pattern)
    if c > 0:
        content = content.replace(pattern, replacement)
        print(f'Fixed {c} occurrences of {pattern!r}')

with open('baitcoin_explorer/docs.py', 'w') as f:
    f.write(content)

print(f'Fixed {count} Response brace issues')
