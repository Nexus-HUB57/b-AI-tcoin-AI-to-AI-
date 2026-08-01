"""Fix docs.py api-keys section with proper multi-line formatting."""
with open('baitcoin_explorer/docs.py', 'r') as f:
    lines = f.readlines()

# Find line 179 (0-indexed 178)
# Replace from there through line 192
new_lines = lines[:178]

new_lines.append('        p["/api/v1/dev/api-keys"] = {\n')
new_lines.append('            "post": {\n')
new_lines.append('                "tags": ["Developer Tools"],\n')
new_lines.append('                "operationId": "createAPIKey",\n')
new_lines.append('                "summary": "Create API key",\n')
new_lines.append('                "security": [{"MoltbookAuth": []}],\n')
new_lines.append('                "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "properties": {\n')
new_lines.append('                    "tier": {"type": "string", "enum": ["free", "developer", "pro", "enterprise"], "default": "free"},\n')
new_lines.append('                    "ttl_days": {"type": "integer", "default": 365},\n')
new_lines.append('                }}}}}}},\n')
new_lines.append('                "responses": {"200": _response("APIKeyResponse", "API key created"), "401": _err_response("Unauthorized")}},\n')
new_lines.append('            },\n')
new_lines.append('            "get": {\n')
new_lines.append('                "tags": ["Developer Tools"],\n')
new_lines.append('                "operationId": "listAPIKeys",\n')
new_lines.append('                "summary": "List API keys",\n')
new_lines.append('                "security": [{"MoltbookAuth": []}],\n')
new_lines.append('                "responses": {"200": {"description": "API keys list", "content": {"application/json": {"schema": {"type": "array", "items": _ref("APIKeyInfo")}}}}}},\n')
new_lines.append('        }\n')

new_lines.extend(lines[192:])

with open('baitcoin_explorer/docs.py', 'w') as f:
    f.writelines(new_lines)

print('Fixed!')
