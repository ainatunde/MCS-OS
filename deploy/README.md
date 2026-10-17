# MCS-OS & MCS-ERP Deployment Guide

End-to-end automated deployment of **MCS-OS** (Corporate Control Plane) and **MCS-ERP** (ERPNext v15 Stack) to your Contabo VPS alongside **Pulzz** and **Coolify**, utilizing your existing Cloudflare Tunnel (`tvinsights-coolify`) and the domain `mcsolutions.stream`.

---

## 1. Architecture & Safeguards

```
                         Cloudflare Tunnel (cloudflared)
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           ▼                         ▼                         ▼
      Pulzz (Active)            MCS-OS (New)              MCS-ERP (New)
    pulzz.stream              os.mcsolutions.stream     erp.mcsolutions.stream
    Port: 8000                Port: 8090 (Host)         Port: 8080 (Host)
    (Docker: web)             (Docker: control-api)     (Docker: frontend)
                                     │                         │
                                     └──────── (API Sync) ─────┘
                                        (over coolify network)
```

* **RAM Protection**: Automatically allocates a 4 GB swapfile if missing, preventing the Contabo VPS OOM killer from firing.
* **Service Isolation**: Reuses Cloudflare Tunnel ingress rules to route `os.mcsolutions.stream` and `erp.mcsolutions.stream` directly to Traefik on port 80 without disrupting Pulzz.
* **Zero Port Collisions**: Binds MCS-OS to internal host port `8090` and ERPNext to `8080`, completely avoiding port `8000` (used by Coolify).
* **Automated Daily Backups**: Installs a daily cron job at `/opt/mcs/backup.sh` backing up both ERPNext (`bench backup --with-files`) and PostgreSQL (`pg_dump`) to `/opt/mcs/backups/`.

---

## 2. Prerequisites

1. Ensure `mcsolutions.stream` is active in your Cloudflare account.
2. In Cloudflare, create an API Token with permissions:
   * **Zone > DNS > Edit**
   * **Account > Cloudflare Tunnel > Edit**
3. Ensure your local machine has SSH access to the Contabo VPS.

---

## 3. Quickstart Deployment

### Step 1: Create your Secrets File
Copy the example secrets file:

```powershell
Copy-Item .\deploy\mcs-deploy.secrets.env.example .\deploy\mcs-deploy.secrets.env
```

Open `.\deploy\mcs-deploy.secrets.env` and fill in:
* `VPS_IP` — Your Contabo server IP
* `CF_API_TOKEN` — Cloudflare API token
* `CF_ACCOUNT_ID` — Cloudflare Account ID
* `GITHUB_TOKEN` — GitHub Personal Access Token (for adding read deploy keys)

*(Note: Passwords and tokens left blank will be **automatically generated and saved** into this file for your records).*

### Step 2: Execute Deployment

Run the PowerShell runner from your local machine:

```powershell
cd c:\Users\aina_\.gemini\antigravity\scratch\mcs-os
.\deploy\deploy-mcs.ps1
```

The script will:
1. Verify SSH connectivity to your Contabo VPS.
2. Ensure swap is active on the host.
3. Fetch your existing `tvinsights-coolify` Cloudflare Tunnel and append ingress rules for `os.mcsolutions.stream` and `erp.mcsolutions.stream`.
4. Upsert DNS CNAME records in `mcsolutions.stream`.
5. Connect to Coolify API, create the **MCS** project, and deploy `mcs-os` and `mcs-erp`.
6. Run the Day-1 ERPNext site initialization (`bench new-site erp.mcsolutions.stream`).
7. Install automated daily backup crons.
8. Validate public HTTPS health checks.

---

## 4. Post-Deployment: ERP Setup & Bootstrap

Once the deployment completes:

1. **Access ERPNext**: Open `https://erp.mcsolutions.stream` in your browser.
2. **Log In**: Use username `Administrator` and the `ADMIN_PASSWORD` stored in your `mcs-deploy.secrets.env`.
3. **Setup Wizard**: Complete the 1-minute wizard:
   * Country: **Nigeria**
   * Currency: **NGN**
   * Company: **Multimedia Cloud Solutions Ltd** (Abbr: **MCS**)
4. **Generate API Key for MCS-OS**:
   * Navigate to: **Settings > My Settings > API Access**.
   * Click **Generate Keys**.
   * Copy the `API Key` and `API Secret`.
5. **Run the Financial/Cost-Center Bootstrap**:
   From `MCS-ERP-review`:
   ```bash
   export ERPNEXT_URL=https://erp.mcsolutions.stream
   export ERPNEXT_API_KEY="<your-key>"
   export ERPNEXT_API_SECRET="<your-secret>"
   python bootstrap/bootstrap.py
   ```
6. **Save Keys to MCS-OS**:
   Update `ERPNEXT_API_KEY` and `ERPNEXT_API_SECRET` in Coolify under the `mcs-os` environment variables.
