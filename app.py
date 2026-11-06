"""
Mobile Internet Access Control App for ipTIME AX3000M.

Option B Implementation:
Rule deactivation (active: false) and reactivation (active: true) toggle mode.
Provides 3 distinct unblocking workflows:
1) Individual One-Touch Unblock in [Devices] tab
2) Blocked Devices overview and One-Click "Unblock All" in [Blocked] tab
3) Multi-select Batch Unblock in [Batch] tab
"""

from typing import Dict, List, Any
import base64
import os
import streamlit as st
import time
from auth import IpTimeAuthManager
from controller import IpTimeController

# 1. Page Configuration (Smartphone Centered Layout)
logo_path = "logo.png" if os.path.exists("logo.png") else "🛡️"
st.set_page_config(
    page_title="Blocked Internet",
    page_icon=logo_path,
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 2. Smartphone Mobile Frame Custom CSS
st.markdown("""
<style>
    /* 1. Hide default Streamlit header bar to prevent top clipping */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    #MainMenu {
        visibility: hidden !important;
    }
    footer {
        visibility: hidden !important;
    }

    /* 2. Mobile Container Layout with Safe Top Margin */
    .block-container {
        max-width: 440px !important;
        padding-top: 1.2rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
        margin: 0 auto !important;
    }

    /* 3. Force Horizontal Alignment on Mobile Columns (NO vertical stacking) */
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 8px !important;
        align-items: center !important;
    }
    div[data-testid="column"] {
        width: 100% !important;
        min-width: 0 !important;
        flex: 1 1 0px !important;
    }

    /* 4. Action Buttons & Popover unified row alignment */
    .stButton, .stPopover {
        width: 100% !important;
    }
    .stButton > button {
        width: 100% !important;
        height: 38px !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
        padding: 0 0.4rem !important;
        white-space: nowrap !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    .stPopover > button {
        width: 100% !important;
        height: 38px !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
        padding: 0 0.4rem !important;
        white-space: nowrap !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        background-color: #f1f5f9 !important;
        border: 1px solid #cbd5e1 !important;
        color: #334155 !important;
    }
    .stPopover > button:hover {
        background-color: #e2e8f0 !important;
        border-color: #94a3b8 !important;
    }

    /* Smartphone Frame Header */
    .mobile-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: white;
        padding: 14px 16px;
        border-radius: 18px;
        margin-bottom: 12px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .mobile-header-title {
        font-size: 1.25rem;
        font-weight: 700;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 4px;
    }
    .mobile-header-sub {
        font-size: 0.76rem;
        color: #94a3b8;
    }
    .status-badge-online {
        background-color: #10b981;
        color: white;
        font-size: 0.7rem;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 12px;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }

    /* Device Card UI */
    .device-card {
        background: white;
        border-radius: 14px;
        padding: 12px 14px;
        margin-bottom: 8px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.04);
    }
    .device-card-blocked {
        border-left: 5px solid #ef4444 !important;
        background-color: #fffaf0;
    }
    .device-card-active {
        border-left: 5px solid #10b981 !important;
    }
    .device-card-idle {
        border-left: 5px solid #cbd5e1 !important;
    }

    .device-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: #0f172a;
        margin-bottom: 2px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .device-meta {
        font-size: 0.74rem;
        color: #64748b;
        font-family: monospace;
        margin-bottom: 6px;
    }
    .badge-blocked {
        background-color: #fee2e2;
        color: #b91c1c;
        font-size: 0.68rem;
        font-weight: 700;
        padding: 2px 6px;
        border-radius: 6px;
    }
    .badge-active {
        background-color: #d1fae5;
        color: #065f46;
        font-size: 0.68rem;
        font-weight: 600;
        padding: 2px 6px;
        border-radius: 6px;
    }
    .badge-saved-rule {
        background-color: #e0f2fe;
        color: #0369a1;
        font-size: 0.65rem;
        font-weight: 600;
        padding: 1px 5px;
        border-radius: 4px;
    }

    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        justify-content: space-around;
    }
    .stTabs [data-baseweb="tab"] {
        padding-left: 6px;
        padding-right: 6px;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)


# 3. Controller Instance
if "controller" not in st.session_state:
    st.session_state.controller = IpTimeController()

controller = st.session_state.controller

# 4. Data Fetching
with st.spinner("Syncing router rules..."):
    try:
        devices = controller.get_connected_devices()
        system_status = controller.get_system_status()
        is_router_online = True
    except Exception as e:
        devices = []
        system_status = {"version": "Offline", "uptime_seconds": 0}
        is_router_online = False

total_count = len(devices)
blocked_count = sum(1 for d in devices if d.get("is_blocked", False))
active_count = sum(1 for d in devices if d.get("is_active", False))

# 5. Mobile App Header
status_color = "#10b981" if is_router_online else "#ef4444"
status_text = "ONLINE" if is_router_online else "OFFLINE"

# Read logo image as base64 for inline display
logo_b64 = ""
if os.path.exists("logo.png"):
    try:
        with open("logo.png", "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        logo_b64 = ""

logo_img_tag = f'<img src="data:image/png;base64,{logo_b64}" style="width:28px;height:28px;border-radius:50%;object-fit:cover;vertical-align:middle;margin-right:8px;border:1px solid rgba(255,255,255,0.4);"/>' if logo_b64 else '🛡️ '

st.markdown(f"""
<div class="mobile-header">
    <div class="mobile-header-title">
        <span style="display:flex;align-items:center;">
            {logo_img_tag}Blocked Internet
        </span>
        <span class="status-badge-online" style="background-color: {status_color};">● {status_text}</span>
    </div>
    <div class="mobile-header-sub">
        Total: <b>{total_count}</b> &nbsp;|&nbsp; 
        Active: <b style="color:#10b981;">{active_count}</b> &nbsp;|&nbsp; 
        Blocked: <b style="color:#ef4444;">{blocked_count}</b>
    </div>
</div>
""", unsafe_allow_html=True)

# 6. Tab Navigation: 3 Distinct Recovery Workflows
tab_devices, tab_blocked, tab_batch, tab_settings = st.tabs([
    f"📱 Devices ({total_count})",
    f"🚫 Blocked ({blocked_count})",
    "⚡ Batch",
    "⚙️ Status"
])


# ==========================================
# WORKFLOW ①: [Devices] TAB - INDIVIDUAL ONE-TOUCH UNBLOCK
# ==========================================
with tab_devices:
    col_search, col_refresh = st.columns([4, 1], gap="small")
    with col_search:
        search = st.text_input(
            "Search device",
            placeholder="Search Name, IP, or MAC...",
            label_visibility="collapsed"
        )
    with col_refresh:
        if st.button("🔄", help="Refresh list"):
            st.rerun()

    filter_choice = st.radio(
        "Filter Mode",
        options=["All", "Active", "Blocked"],
        horizontal=True,
        label_visibility="collapsed"
    )

    filtered_devices = devices
    if filter_choice == "Active":
        filtered_devices = [d for d in filtered_devices if d.get("is_active", False)]
    elif filter_choice == "Blocked":
        filtered_devices = [d for d in filtered_devices if d.get("is_blocked", False)]

    if search.strip():
        q = search.strip().lower()
        filtered_devices = [
            d for d in filtered_devices
            if q in d.get("alias", "").lower()
            or q in d.get("ip", "").lower()
            or q in d.get("mac", "").lower()
            or q in d.get("hostname", "").lower()
        ]

    st.caption(f"Showing {len(filtered_devices)} devices (Option B: Rule Toggle Mode)")

    for dev in filtered_devices:
        ip = dev.get("ip", "")
        mac = dev.get("mac", "")
        alias = dev.get("alias", dev.get("hostname", "Device"))
        is_blocked = dev.get("is_blocked", False)
        is_active = dev.get("is_active", False)
        has_rule = dev.get("has_rule", False)
        rule_name = dev.get("block_rule_name", "")
        group = dev.get("group", "General")

        # Card status styling
        card_class = "device-card-blocked" if is_blocked else ("device-card-active" if is_active else "device-card-idle")
        if is_blocked:
            badge_html = "<span class='badge-blocked'>BLOCKED</span>"
        else:
            saved_tag = "<span class='badge-saved-rule'>SAVED</span> " if has_rule else ""
            active_tag = "<span class='badge-active'>ACTIVE</span>" if is_active else "<span style='font-size:0.68rem;color:#94a3b8;'>IDLE</span>"
            badge_html = f"{saved_tag}{active_tag}"

        st.markdown(f"""
        <div class="device-card {card_class}">
            <div class="device-title">
                <span>{alias}</span>
                {badge_html}
            </div>
            <div class="device-meta">
                IP: {ip} &nbsp;|&nbsp; MAC: {mac}<br>
                Host: {dev['hostname']} &nbsp;|&nbsp; Group: {group}
            </div>
        </div>
        """, unsafe_allow_html=True)

        btn_col1, btn_col2 = st.columns([1, 1], gap="small")

        # ① One-touch Individual Block / Unblock Toggle Button
        with btn_col1:
            if is_blocked:
                # UNBLOCK ACTION: Deactivate rule to active: false
                if st.button("🔓 Unblock", key=f"unblk_{ip}_{mac}"):
                    with st.spinner(f"Unblocking {alias}..."):
                        target_rule = rule_name if rule_name else f"BLK_{(mac if mac!='N/A' else ip).replace(':','').replace('.','')[-8:]}"
                        controller.unblock_device(target_rule)
                        st.toast(f"Unblocked: {alias} (Rule Deactivated)", icon="🔓")
                        time.sleep(0.4)
                        st.rerun()
            else:
                # BLOCK ACTION: Activate rule to active: true
                if st.button("🚫 Block Internet", key=f"blk_{ip}_{mac}", type="primary"):
                    with st.spinner(f"Blocking {alias}..."):
                        target_id = mac if mac != "N/A" else ip
                        target_type = "mac" if mac != "N/A" else "ip"
                        controller.block_device(target_id, target_type=target_type, rule_alias=alias)
                        st.toast(f"Blocked: {alias} (Rule Activated)", icon="🚫")
                        time.sleep(0.4)
                        st.rerun()

        with btn_col2:
            with st.popover("✏️ Label"):
                st.markdown(f"**Edit Device Metadata**")
                new_alias = st.text_input("Name/Alias", value=alias, key=f"alias_input_{ip}_{mac}")
                new_group = st.text_input("Group (e.g. Class 1, Staff)", value=group, key=f"group_input_{ip}_{mac}")
                if st.button("Save", key=f"save_btn_{ip}_{mac}"):
                    save_key = mac if mac != "N/A" else ip
                    controller.set_device_metadata(save_key, alias=new_alias, group=new_group)
                    st.success("Saved!")
                    time.sleep(0.3)
                    st.rerun()

        st.markdown("<div style='margin-bottom: 6px;'></div>", unsafe_allow_html=True)


# ==========================================
# WORKFLOW ②: [Blocked] TAB - OVERVIEW & ONE-CLICK "UNBLOCK ALL"
# ==========================================
with tab_blocked:
    st.subheader("Currently Blocked Devices")
    blocked_devices = [d for d in devices if d.get("is_blocked", False)]

    if not blocked_devices:
        st.info("No devices are currently blocked from internet access.")
    else:
        # ② One-Click "Unblock All Devices" Button
        if st.button("🔓 Unblock All Devices (One-Click)", type="primary"):
            with st.spinner("Deactivating all block rules..."):
                rule_names = [d.get("block_rule_name", "") for d in blocked_devices if d.get("block_rule_name")]
                res = controller.batch_unblock(rule_names)
                st.success(f"Successfully unblocked {res['success']} devices!")
                time.sleep(0.5)
                st.rerun()

        st.divider()
        for b_dev in blocked_devices:
            b_alias = b_dev.get("alias", "Device")
            b_ip = b_dev.get("ip", "")
            b_mac = b_dev.get("mac", "")
            b_rule = b_dev.get("block_rule_name", "")
            b_group = b_dev.get("group", "General")

            col_b_info, col_b_btn1, col_b_btn2 = st.columns([3, 1.2, 1], gap="small")
            with col_b_info:
                st.markdown(f"**{b_alias}** ({b_ip})")
                st.caption(f"Rule: `{b_rule}` | Group: {b_group}")
            with col_b_btn1:
                # Individual unblock in Blocked tab
                if st.button("🔓 Unblock", key=f"tab_unblk_{b_ip}_{b_mac}"):
                    with st.spinner("Unblocking..."):
                        controller.unblock_device(b_rule)
                        st.toast(f"Unblocked: {b_alias}")
                        time.sleep(0.4)
                        st.rerun()
            with col_b_btn2:
                # Optional permanent purge of rule
                if st.button("🗑️", key=f"tab_purge_{b_ip}_{b_mac}", help="Permanently delete rule"):
                    with st.spinner("Deleting rule..."):
                        controller.delete_rule(b_rule)
                        st.toast(f"Rule deleted: {b_alias}")
                        time.sleep(0.4)
                        st.rerun()


# ==========================================
# WORKFLOW ③: [Batch] TAB - MULTI-SELECT BATCH UNBLOCK & BLOCK
# ==========================================
with tab_batch:
    st.subheader("Multi-Select Batch Access Control")
    st.caption("Select multiple student/staff devices to apply bulk toggle operations.")

    select_all = st.checkbox("Select All Devices")

    selected_targets: List[Dict[str, str]] = []
    selected_rules_for_unblock: List[str] = []

    for dev in devices:
        d_alias = dev.get("alias", "Device")
        d_ip = dev.get("ip", "")
        d_mac = dev.get("mac", "")
        d_blocked = dev.get("is_blocked", False)
        d_rule = dev.get("block_rule_name", "")

        status_text = "🚫 BLOCKED" if d_blocked else "ONLINE"
        label = f"{d_alias} ({d_ip}) - [{status_text}]"
        is_checked = st.checkbox(label, value=select_all, key=f"batch_chk_{d_ip}_{d_mac}")
        if is_checked:
            target_id = d_mac if d_mac != "N/A" else d_ip
            target_type = "mac" if d_mac != "N/A" else "ip"
            selected_targets.append({"identifier": target_id, "target_type": target_type})
            if d_rule:
                selected_rules_for_unblock.append(d_rule)

    st.markdown("---")
    st.write(f"Selected: **{len(selected_targets)}** devices")

    col_batch_block, col_batch_unblock = st.columns(2, gap="small")
    with col_batch_block:
        if st.button("🚫 Batch Block", type="primary", disabled=len(selected_targets) == 0):
            with st.spinner("Applying batch block..."):
                res = controller.batch_block(selected_targets)
                st.success(f"Blocked {res['success']} devices (Rules Activated).")
                time.sleep(0.5)
                st.rerun()

    # ③ Multi-Select Batch Unblock Button
    with col_batch_unblock:
        if st.button("🔓 Batch Unblock", disabled=len(selected_rules_for_unblock) == 0):
            with st.spinner("Applying batch unblock..."):
                res = controller.batch_unblock(selected_rules_for_unblock)
                st.success(f"Unblocked {res['success']} devices (Rules Deactivated).")
                time.sleep(0.5)
                st.rerun()


# ==========================================
# TAB 4: ROUTER STATUS & TOGGLE CONFIG
# ==========================================
with tab_settings:
    st.subheader("Router Status & Mode")

    st.markdown(f"""
    - **Control Mode:** `Option B (Rule Toggle / Deactivation)`
    - **Target Router:** `ipTIME AX3000M (Gen3 Web UI)`
    - **Firmware Version:** `{system_status.get('version', 'N/A')}`
    - **Uptime:** `{system_status.get('uptime_seconds', 0) // 3600}h {(system_status.get('uptime_seconds', 0) % 3600) // 60}m`
    - **Subnet Range:** `{system_status.get('dhcp_range', '192.168.4.2 - 192.168.4.199')}`
    - **EasyMesh Role:** `{system_status.get('easymesh_role', 'Controller')}`
    """)

    st.divider()
    if st.button("🔄 Sync & Re-authenticate Session"):
        with st.spinner("Re-authenticating with router..."):
            login_ok = controller.auth.login()
            if login_ok:
                st.success("Session refreshed successfully!")
            else:
                st.error("Failed to connect to router. Check admin credentials.")
        time.sleep(0.5)
        st.rerun()
