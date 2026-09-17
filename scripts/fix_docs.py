"""Fix docs.py line 179-192."""
with open('baitcoin_explorer/docs.py', 'r') as f:
    lines = f.readlines()

# Replace lines 179-192 (0-indexed: 178-191)
new_section = '''        p[\"/api/v1/dev/api-keys\"] = {
            \"post\": {\"tags\": [\"Developer Tools\"], \"operationId\": \"createAPIKey\", \"summary\": \"Create API key\", \"security\": [{\"MoltbookAuth\": []}], \"requestBody\": {\"required\": True, \"content\": {\"application/json\": {\"schema\": {\"type\": \"object\", \"properties\": {\"tier\": {\"type\": \"string\", \"enum\": [\"free\", \"developer\", \"pro\", \"enterprise\"], \"default\": \"free\"}, \"ttl_days\": {\"type\": \"integer\", \"default\": 365}}}}}}}}, \"responses\": {\"200\": _response(\"APIKeyResponse\", \"API key created\"), \"401\": _err_response(\"Unauthorized\")}},
            \"get\": {\"tags\": [\"Developer Tools\"], \"operationId\": \"listAPIKeys\", \"summary\": \"List API keys\", \"security\": [{\"MoltbookAuth\": []}], \"responses\": {\"200\": {\"description\": \"API keys list\", \"content\": {\"application/json\": {\"schema\": {\"type\": \"array\", \"items\": _ref(\"APIKeyInfo\")}}}}}}},
        }
'''

lines[178:192] = [new_section]

with open('baitcoin_explorer/docs.py', 'w') as f:
    f.writelines(lines)

print('Fixed!')
