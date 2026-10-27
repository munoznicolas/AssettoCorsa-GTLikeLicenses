# Assetto Corsa GT Licenses - Telemetry PR Gateway

Lightweight, 100% free serverless Cloudflare Worker gateway that accepts AI telemetry submissions with verified Google OAuth logins and automatically opens autoformatted Pull Requests on the Assetto Corsa GT-Like Licenses GitHub repository.

---

## ⚡ Deployment in 2 Minutes

### 1. Prerequisites
* A free [Cloudflare](https://dash.cloudflare.com/) account.
* Node.js 18+ installed on your machine.

### 2. Configure & Deploy
```bash
cd serverless/telemetry_pr_gateway

# 1. Login to Cloudflare
npx wrangler login

# 2. Set your GitHub Token (Requires repository write permissions: contents & pull-requests)
npx wrangler secret put GITHUB_TOKEN
# (Paste your GitHub Fine-Grained Personal Access Token when prompted)

# 3. Deploy worker globally
npx wrangler deploy
```

Your worker will be live at `https://ac-telemetry-pr-gateway.<your-subdomain>.workers.dev`.

### 3. Update Web UI (Optional)
The Web UI automatically connects to this gateway. You can also configure a custom gateway URL directly in the Web UI's Telemetry Submission modal or via `localStorage.setItem("gt_pr_gateway_url", "https://your-worker.workers.dev/submit")`.
