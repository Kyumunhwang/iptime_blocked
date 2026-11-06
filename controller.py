"""
Network Controller Engine for ipTIME AX3000M (Toggle / Deactivation Mode).

Supports dual SSID classification:
- 'School wifi' (Guest / Student devices): bss ending with .2
- 'edu' (Main / Staff devices): bss ending with .1
- 'Wired' (LAN devices)
Provides one-touch bulk blocking/unblocking specifically for 'School wifi' students.
"""

from typing import Any, Dict, List, Optional, Set
import json
import logging
import os
import re
from auth import IpTimeAuthManager

logger = logging.getLogger(__name__)


class IpTimeController:
    """High-level controller interface for device management and network access control."""

    def __init__(self, auth_manager: Optional[IpTimeAuthManager] = None, devices_file: str = "devices.json") -> None:
        """
        Initialize the controller with authentication manager and metadata storage.

        Args:
            auth_manager: IpTimeAuthManager instance. If None, a new one is created.
            devices_file: Path to local JSON file for device aliases and group metadata.
        """
        self.auth = auth_manager or IpTimeAuthManager()
        self.devices_file = devices_file
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> Dict[str, Any]:
        """Load local metadata from JSON file."""
        if not os.path.exists(self.devices_file):
            return {"aliases": {}, "groups": {}, "notes": {}}
        try:
            with open(self.devices_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading {self.devices_file}: {e}")
            return {"aliases": {}, "groups": {}, "notes": {}}

    def _save_metadata(self) -> None:
        """Save device metadata to local JSON file."""
        try:
            with open(self.devices_file, "w", encoding="utf-8") as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error writing to {self.devices_file}: {e}")

    def get_system_status(self) -> Dict[str, Any]:
        """
        Retrieve router system information including uptime, DHCP range, and EasyMesh status.

        Returns:
            Dict[str, Any]: Formatted system status.
        """
        resp = self.auth.post("system/info")
        res = resp.get("result") or {}
        return {
            "version": res.get("version", "Unknown"),
            "uptime_seconds": res.get("uptime", 0),
            "connected_period": res.get("connected_period", 0),
            "wan_link": res.get("wan_link", "N/A"),
            "dhcp_range": f"{res.get('dhcpd', {}).get('startip', '')} - {res.get('dhcpd', {}).get('endip', '')}",
            "easymesh_role": res.get("easymesh", {}).get("role", "N/A")
        }

    def get_firewall_rules(self) -> List[Dict[str, Any]]:
        """
        Fetch all firewall rules from the router.

        Returns:
            List[Dict[str, Any]]: List of configured firewall rules.
        """
        resp = self.auth.post("firewall/get")
        rules = resp.get("result")
        if isinstance(rules, list):
            return rules
        return []

    def get_connected_devices(self) -> List[Dict[str, Any]]:
        """
        Fetch all connected devices from LAN station telemetry, DHCP leases, and active QoS device list,
        merging with SSID detection ('School wifi' vs 'edu'), firewall block status, and local alias metadata.

        Returns:
            List[Dict[str, Any]]: List of enriched device records.
        """
        # 1. Fetch real-time LAN station info (includes exact BSS mapping for SSID detection)
        station_resp = self.auth.post("network/interface/lan/stations")
        stations = station_resp.get("result") if isinstance(station_resp.get("result"), list) else []

        # 2. Fetch DHCP leases
        lease_resp = self.auth.post("dhcpd/lease/show")
        leases = lease_resp.get("result") if isinstance(lease_resp.get("result"), list) else []

        # 3. Fetch active QoS device IPs
        qos_resp = self.auth.post("qos/device/list")
        qos_ips = set(qos_resp.get("result")) if isinstance(qos_resp.get("result"), list) else set()

        # 4. Fetch firewall rules to evaluate active block state
        fw_rules = self.get_firewall_rules()
        mac_to_rule: Dict[str, Dict[str, Any]] = {}
        ip_to_rule: Dict[str, Dict[str, Any]] = {}

        for rule in fw_rules:
            if rule.get("policy") == "drop":
                internal = rule.get("filter", {}).get("internal", {})
                mac = internal.get("mac")
                if mac:
                    mac_to_rule[mac.upper()] = rule
                ip_info = internal.get("ip", {})
                start_ip = ip_info.get("start")
                if start_ip:
                    ip_to_rule[start_ip] = rule

        # Build station lookup map by MAC
        station_map: Dict[str, Dict[str, Any]] = {}
        for s in stations:
            s_mac = s.get("mac", "").upper()
            if s_mac:
                station_map[s_mac] = s

        # Build lease lookup map by MAC
        lease_map: Dict[str, Dict[str, Any]] = {}
        for l in leases:
            l_mac = l.get("mac", "").upper()
            if l_mac:
                lease_map[l_mac] = l

        all_macs: Set[str] = set(station_map.keys()) | set(lease_map.keys())
        devices: List[Dict[str, Any]] = []

        aliases = self.metadata.get("aliases", {})
        groups = self.metadata.get("groups", {})
        notes = self.metadata.get("notes", {})

        for mac in all_macs:
            s_data = station_map.get(mac, {})
            l_data = lease_map.get(mac, {})

            # Determine IP
            ip = s_data.get("info", {}).get("ip") or l_data.get("ip", "")

            # Determine Hostname
            hostname = (
                s_data.get("info", {}).get("name")
                or l_data.get("desc")
                or "Unknown Device"
            )

            # Determine SSID / Network Role
            conn = s_data.get("connection", {})
            conn_type = conn.get("type", "")
            bss = conn.get("wireless", {}).get("bss", "")

            if bss.endswith(".2"):
                ssid = "School wifi"
                network_role = "Student"
            elif bss.endswith(".1"):
                ssid = "edu"
                network_role = "Staff"
            elif conn_type == "wired":
                ssid = "Wired"
                network_role = "Wired"
            else:
                ssid = "Wireless" if conn_type == "wireless" else "LAN"
                network_role = "General"

            # Check rule existence and active state
            rule_info = mac_to_rule.get(mac) or (ip_to_rule.get(ip) if ip else None)
            has_rule = rule_info is not None
            rule_name = rule_info.get("name", "") if rule_info else ""
            rule_active = rule_info.get("active", False) if rule_info else False
            is_blocked = has_rule and rule_active

            # Aliases & Groups
            default_group = "Students" if network_role == "Student" else ("Staff" if network_role == "Staff" else "General")
            alias = aliases.get(mac) or (aliases.get(ip) if ip else None) or hostname
            group = groups.get(mac) or (groups.get(ip) if ip else None) or default_group
            note = notes.get(mac) or (notes.get(ip) if ip else None) or ""

            remaining = l_data.get("remaining", 0)
            is_active = (ip in qos_ips) or bool(s_data)

            devices.append({
                "mac": mac,
                "ip": ip,
                "hostname": hostname,
                "alias": alias,
                "group": group,
                "note": note,
                "ssid": ssid,
                "network_role": network_role,
                "remaining_lease": remaining,
                "is_active": is_active,
                "is_blocked": is_blocked,
                "has_rule": has_rule,
                "block_rule_name": rule_name
            })

        # Process any active IP from QoS list that didn't appear in MAC lists
        for q_ip in qos_ips:
            if not any(d["ip"] == q_ip for d in devices):
                rule_info = ip_to_rule.get(q_ip)
                has_rule = rule_info is not None
                rule_name = rule_info.get("name", "") if rule_info else ""
                rule_active = rule_info.get("active", False) if rule_info else False
                is_blocked = has_rule and rule_active

                alias = aliases.get(q_ip, f"Host-{q_ip.split('.')[-1]}")
                group = groups.get(q_ip, "General")
                note = notes.get(q_ip, "")

                devices.append({
                    "mac": "N/A",
                    "ip": q_ip,
                    "hostname": alias,
                    "alias": alias,
                    "group": group,
                    "note": note,
                    "ssid": "Wired",
                    "network_role": "General",
                    "remaining_lease": 0,
                    "is_active": True,
                    "is_blocked": is_blocked,
                    "has_rule": has_rule,
                    "block_rule_name": rule_name
                })

        # Sort: Blocked devices first, then Students, then active devices, then IP
        def sort_key(d: Dict[str, Any]):
            ip_parts = [int(p) for p in d["ip"].split(".")] if "." in d.get("ip", "") else [0, 0, 0, 0]
            role_prio = 0 if d.get("network_role") == "Student" else (1 if d.get("network_role") == "Staff" else 2)
            return (not d["is_blocked"], role_prio, not d["is_active"], ip_parts)

        devices.sort(key=sort_key)
        return devices

    def block_device(self, identifier: str, target_type: str = "mac", rule_alias: str = "") -> Dict[str, Any]:
        """
        Block internet access.
        If a rule already exists, toggles it to 'active: true'.
        If not, creates a new drop rule with 'active: true'.

        Args:
            identifier: MAC address or IP address.
            target_type: 'mac' or 'ip'.
            rule_alias: Human-readable label for rule identification.

        Returns:
            Dict[str, Any]: Router response dictionary.
        """
        clean_id = re.sub(r"[^A-Za-z0-9]", "", identifier)
        expected_rule_name = f"BLK_{clean_id[-8:]}"

        existing_rules = self.get_firewall_rules()
        existing_rule = next((r for r in existing_rules if r.get("name") == expected_rule_name), None)

        if existing_rule:
            logger.info(f"Toggling existing rule {expected_rule_name} to ACTIVE (BLOCKED)")
            return self.auth.post("firewall/set", {"current": expected_rule_name, "active": True})

        if target_type == "mac" or ":" in identifier or "-" in identifier:
            formatted_mac = identifier.upper().replace("-", ":")
            internal_filter = {"mac": formatted_mac}
        else:
            internal_filter = {
                "ip": {
                    "start": identifier,
                    "end": identifier
                }
            }

        rule_payload = {
            "name": expected_rule_name,
            "type": "net",
            "active": True,
            "priority": 1,
            "policy": "drop",
            "direction": {
                "inbound": False,
                "outbound": True
            },
            "filter": {
                "internal": internal_filter
            }
        }

        logger.info(f"Creating new block rule: {expected_rule_name} for {identifier}")
        return self.auth.post("firewall/add", rule_payload)

    def unblock_device(self, rule_name: str) -> Dict[str, Any]:
        """
        Unblock internet access by setting rule to 'active: false' (Option B: Deactivation).

        Args:
            rule_name: Name of the firewall rule to deactivate.

        Returns:
            Dict[str, Any]: Router response dictionary.
        """
        logger.info(f"Deactivating rule: {rule_name} (UNBLOCKED)")
        return self.auth.post("firewall/set", {"current": rule_name, "active": False})

    def delete_rule(self, rule_name: str) -> Dict[str, Any]:
        """
        Permanently delete a firewall rule from the router.

        Args:
            rule_name: Name of the rule to delete.

        Returns:
            Dict[str, Any]: Router response dictionary.
        """
        logger.info(f"Permanently deleting rule: {rule_name}")
        return self.auth.post("firewall/del", [rule_name])

    def block_all_school_wifi(self) -> Dict[str, int]:
        """
        Block internet access for ALL devices currently connected to 'School wifi' (Students).

        Returns:
            Dict[str, int]: Summary count of success and failure.
        """
        devices = self.get_connected_devices()
        student_targets = [
            {"identifier": d["mac"], "target_type": "mac"}
            for d in devices
            if d.get("ssid") == "School wifi" and d.get("mac") != "N/A"
        ]
        logger.info(f"Executing bulk block for {len(student_targets)} 'School wifi' devices.")
        return self.batch_block(student_targets)

    def unblock_all_school_wifi(self) -> Dict[str, int]:
        """
        Unblock internet access for ALL blocked devices belonging to 'School wifi' (Students).

        Returns:
            Dict[str, int]: Summary count of success and failure.
        """
        devices = self.get_connected_devices()
        rule_names = [
            d["block_rule_name"]
            for d in devices
            if d.get("ssid") == "School wifi" and d.get("block_rule_name")
        ]
        logger.info(f"Executing bulk unblock for {len(rule_names)} 'School wifi' rules.")
        return self.batch_unblock(rule_names)

    def batch_block(self, targets: List[Dict[str, str]]) -> Dict[str, int]:
        """
        Block multiple devices in a batch operation by activating/adding rules.

        Args:
            targets: List of dicts, each with 'identifier' and 'target_type'.

        Returns:
            Dict[str, int]: Summary count of success and failure.
        """
        success_count = 0
        fail_count = 0
        for item in targets:
            ident = item.get("identifier", "")
            t_type = item.get("target_type", "mac")
            res = self.block_device(ident, target_type=t_type)
            if res.get("result") is not None and not res.get("error"):
                success_count += 1
            else:
                fail_count += 1
        return {"success": success_count, "failed": fail_count}

    def batch_unblock(self, rule_names: List[str]) -> Dict[str, int]:
        """
        Unblock multiple devices by deactivating their rules ('active: false').

        Args:
            rule_names: List of rule names to deactivate.

        Returns:
            Dict[str, int]: Summary count of success and failure.
        """
        success_count = 0
        fail_count = 0
        for r_name in rule_names:
            if not r_name:
                continue
            res = self.unblock_device(r_name)
            if res.get("result") is not None and not res.get("error"):
                success_count += 1
            else:
                fail_count += 1
        return {"success": success_count, "failed": fail_count}

    def set_device_metadata(self, key: str, alias: Optional[str] = None, group: Optional[str] = None, note: Optional[str] = None) -> None:
        """
        Update local metadata for a device (alias, group tag, or note).

        Args:
            key: MAC address or IP address.
            alias: Optional alias display name.
            group: Optional group name (e.g. 'Class 1', 'Staff').
            note: Optional note text.
        """
        norm_key = key.upper() if ":" in key else key
        if alias is not None:
            self.metadata.setdefault("aliases", {})[norm_key] = alias
        if group is not None:
            self.metadata.setdefault("groups", {})[norm_key] = group
        if note is not None:
            self.metadata.setdefault("notes", {})[norm_key] = note
        self._save_metadata()


if __name__ == "__main__":
    ctl = IpTimeController()
    devs = ctl.get_connected_devices()
    student_count = sum(1 for d in devs if d.get("ssid") == "School wifi")
    staff_count = sum(1 for d in devs if d.get("ssid") == "edu")
    print(f"Total: {len(devs)} | Students (School wifi): {student_count} | Staff (edu): {staff_count}")
