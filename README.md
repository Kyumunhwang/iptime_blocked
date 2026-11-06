# 🚫 Blocked Internet - ipTIME AX3000M Access Control App

A mobile-friendly, smartphone-sized web application to directly monitor, block, and unblock internet access for student and staff devices connected to an **ipTIME AX3000M** router (Gen3 Flutter Web UI) without logging into the router web console.

<p align="center">
  <img src="logo.png" alt="Blocked Internet Logo" width="120" />
</p>

## ✨ Key Features

1. **Option B: Rule Toggle Mode (Non-destructive)**
   - Blocking creates or activates a firewall drop rule (`active: true`).
   - Unblocking deactivates the rule (`active: false`) instantly without deleting the configuration.
2. **Three Flexible Recovery Workflows**
   - **📱 [Devices] Tab:** Individual one-touch unblock per device.
   - **🚫 [Blocked] Tab:** Overview of all blocked devices + One-Click "Unblock All Devices".
   - **⚡ [Batch] Tab:** Multi-select checkboxes for batch unblocking and blocking.
3. **Smartphone-sized Mobile UI**
   - Designed with a 440px max-width centered container and touch-friendly controls.
4. **Device Metadata Management**
   - Easily assign friendly names (e.g. "John's iPad") and groups (e.g. "Class A", "Lab").

---

## 🚀 Quick Start (Local)

### Prerequisites
- Python 3.11+
- Direct network connectivity to router gateway (`192.168.4.1`)

### Installation
```bash
pip install -r requirements.txt
```

### Running the App
```bash
python -m streamlit run app.py --server.port 3088 --server.headless true
```
- Local URL: `http://localhost:3088`
- Smartphone URL: `http://<YOUR_PC_IP>:3088` (on same Wi-Fi)

---

## 🌐 Web Hosting & Remote Access

Since ipTIME AX3000M is located on a local private subnet (`192.168.4.1`), to access this app outside the local Wi-Fi:

1. **Cloudflare Tunnel (Recommended & Free):**
   Run Cloudflare Tunnel on the host PC to expose port `3088` securely to a public domain without port forwarding.
2. **DDNS & Port Forwarding:**
   Forward external port to the PC's port `3088` via ipTIME router NAT settings.
3. **Streamlit Community Cloud:**
   Connect your GitHub repository to [share.streamlit.io](https://share.streamlit.io). *(Note: Router remote management port or tunnel is required for cloud-to-local communication).*
