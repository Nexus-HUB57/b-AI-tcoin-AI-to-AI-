import re

with open('baitcoin_explorer/docs.py', 'r') as f:
    content = f.read()

def fix_response_line(match):
    full = match.group(0)
    opens = full.count('{')
    closes = full.count('}')
    if closes < opens:
        extra = opens - closes
        insert_pos = full.rfind('}') + 1
        new_full = full[:insert_pos] + ('}' * extra) + full[insert_pos:]
        return new_full
    return full

fixed_content = re.sub(r'"type": "object"}}}', fix_response_line, content)

with open('baitcoin_explorer/docs.py', 'w') as f:
    f.write(fixed_content)

print('Fixed!')
