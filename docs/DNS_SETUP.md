# DNS Configuration — mybaitcoin.org

## Domain Overview

| Subdomain | Purpose | Target |
|-----------|---------|--------|
| `mybaitcoin.org` | Landing page | Netlify |
| `explorer.mybaitcoin.org` | Blockch'AI'in Explorer | Netlify |
| `api.mybaitcoin.org` | REST API (52 endpoints) | Backend server |
| `dev.mybaitcoin.org` | Developer Portal / OpenAPI | Netlify |

## Netlify DNS Setup

### Step 1: Add Custom Domain in Netlify

1. Go to **Netlify Dashboard** > **Site settings** > **Domain management**
2. Click **Add custom domain**
3. Enter `mybaitcoin.org`
4. Repeat for `explorer.mybaitcoin.org` and `dev.mybaitcoin.org`

### Step 2: Configure DNS Records

At your domain registrar (where `mybaitcoin.org` was purchased), add the following records:

#### Root Domain (mybaitcoin.org)

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | `@` | `75.2.70.75` | 3600 |
| CNAME | `www` | `your-site-name.netlify.app` | 3600 |

#### Subdomains

| Type | Name | Value | TTL |
|------|------|-------|-----|
| CNAME | `explorer` | `your-site-name.netlify.app` | 3600 |
| CNAME | `dev` | `your-site-name.netlify.app` | 3600 |
| A | `api` | `<backend-server-IP>` | 3600 |

### Step 3: Enable HTTPS

Netlify automatically provisions SSL/TLS certificates via Let's Encrypt for all custom domains. After DNS propagation (up to 48 hours, typically 1-4 hours):

1. Netlify will automatically issue an SSL certificate
2. Verify HTTPS is active: `curl -I https://mybaitcoin.org`

### Step 4: API Subdomain (api.mybaitcoin.org)

The API subdomain points to the backend server (not Netlify). Configure this separately:

- **A record**: `api` -> Backend server IP
- **SSL**: Use certbot (Let's Encrypt) or Cloudflare proxy

```bash
# Example: SSL with certbot on the backend server
sudo certbot --nginx -d api.mybaitcoin.org
```

## Verification Commands

```bash
# Check DNS propagation
dig mybaitcoin.org +short
dig explorer.mybaitcoin.org +short

# Check HTTPS
curl -I https://mybaitcoin.org

# Check API connectivity
curl https://api.mybaitcoin.org/v1/status
```

## Status

- [x] Domain `mybaitcoin.org` acquired
- [ ] DNS records configured at registrar
- [ ] Netlify custom domain added
- [ ] SSL certificate provisioned
- [ ] API subdomain pointing to backend
- [ ] Full DNS verification passed
