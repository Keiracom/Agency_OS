# WireGuard Reverse Tunnel: Residential IP Proxy

Route VPS traffic through Dave's home residential IP to bypass YouTube/Reddit geo-blocks.

## Architecture

```
Dave's Home Router/PC (WireGuard Server)
  - Has residential IP (appears as normal user)
  - Acts as exit node for VPS traffic
  - Port forward UDP 51820
         ↑
         │ WireGuard encrypted tunnel
         ↓
Vultr VPS (WireGuard Client)
  - Connects outbound to home server
  - Routes YouTube/Reddit traffic through tunnel
  - Other traffic stays direct (low latency)
```

---

## 1. Home Server Setup (Dave's PC or Router)

### Option A: Linux PC / Raspberry Pi

```bash
# Install WireGuard
sudo apt update && sudo apt install wireguard

# Generate keys
cd /etc/wireguard
umask 077
wg genkey | tee privatekey | wg pubkey > publickey

# View keys (you'll need these)
cat privatekey  # Keep secret!
cat publickey   # Share with VPS
```

Create config `/etc/wireguard/wg0.conf`:

```ini
[Interface]
PrivateKey = <home_private_key>
Address = 10.200.200.1/24
ListenPort = 51820

# NAT for outbound traffic (change eth0 to your interface)
PostUp = iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT
PostUp = iptables -A FORWARD -o wg0 -j ACCEPT
PostDown = iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT
PostDown = iptables -D FORWARD -o wg0 -j ACCEPT

[Peer]
# VPS public key (generate on VPS first)
PublicKey = <vps_public_key>
AllowedIPs = 10.200.200.2/32
```

Enable IP forwarding:

```bash
# Enable immediately
sudo sysctl -w net.ipv4.ip_forward=1

# Persist across reboots
echo "net.ipv4.ip_forward=1" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

Start WireGuard:

```bash
# Start now
sudo wg-quick up wg0

# Enable on boot
sudo systemctl enable wg-quick@wg0

# Check status
sudo wg show
```

### Option B: OpenWRT Router

1. **Install packages:**
   ```bash
   opkg update
   opkg install wireguard-tools luci-proto-wireguard
   ```

2. **Create interface via LuCI:**
   - Network → Interfaces → Add new interface
   - Protocol: WireGuard VPN
   - Name: `wg0`
   - Generate keys or paste existing
   - Listen Port: 51820
   - IP Address: 10.200.200.1/24

3. **Add peer (VPS):**
   - Public Key: `<vps_public_key>`
   - Allowed IPs: `10.200.200.2/32`

4. **Firewall:**
   - Add `wg0` to WAN zone (or create dedicated zone)
   - Allow forwarding from wg0 to WAN

### Option C: pfSense

1. **System → Package Manager → Install `wireguard`**

2. **VPN → WireGuard → Tunnels → Add:**
   - Enable: ✓
   - Listen Port: 51820
   - Generate keys
   - Interface Address: 10.200.200.1/24

3. **VPN → WireGuard → Peers → Add:**
   - Public Key: `<vps_public_key>`
   - Allowed IPs: `10.200.200.2/32`

4. **Firewall → NAT → Outbound:**
   - Add rule for WireGuard subnet to masquerade

### Option D: Ubiquiti EdgeRouter / UniFi

```bash
# SSH to router
configure

# Create WireGuard interface
set interfaces wireguard wg0 address 10.200.200.1/24
set interfaces wireguard wg0 listen-port 51820
set interfaces wireguard wg0 private-key <home_private_key>

# Add VPS peer
set interfaces wireguard wg0 peer <vps_public_key> allowed-ips 10.200.200.2/32

# NAT masquerade
set nat source rule 100 outbound-interface eth0
set nat source rule 100 source address 10.200.200.0/24
set nat source rule 100 translation address masquerade

commit
save
```

---

## 2. Port Forwarding

### If Home Server is Behind Router

Forward UDP port 51820 to your WireGuard server's local IP:

| Setting | Value |
|---------|-------|
| External Port | 51820 |
| Internal IP | (Your server's LAN IP, e.g., 192.168.1.100) |
| Internal Port | 51820 |
| Protocol | UDP |

### Dynamic DNS (if home IP changes)

If Dave's home IP is dynamic, set up DDNS:

```bash
# Using ddclient (Cloudflare example)
sudo apt install ddclient

# /etc/ddclient.conf
protocol=cloudflare
zone=example.com
login=token
password=<cloudflare_api_token>
home.example.com
```

Or use a free DDNS service:
- **DuckDNS:** `dave-home.duckdns.org`
- **No-IP:** `dave-home.ddns.net`

Update VPS config to use hostname instead of IP.

---

## 3. VPS Client Setup

```bash
# Install WireGuard
sudo apt update && sudo apt install wireguard

# Generate keys
cd /etc/wireguard
umask 077
wg genkey | tee privatekey | wg pubkey > publickey

# View keys
cat privatekey  # Keep secret!
cat publickey   # Send to home server config
```

### Option A: Route ALL Traffic Through Home

Create `/etc/wireguard/wg0.conf`:

```ini
[Interface]
PrivateKey = <vps_private_key>
Address = 10.200.200.2/24
# Optional: Use home's DNS
DNS = 8.8.8.8

[Peer]
PublicKey = <home_public_key>
Endpoint = <dave_home_ip_or_ddns>:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
```

⚠️ **Warning:** This routes ALL VPS traffic through home. High latency for everything.

### Option B: Selective Routing (Recommended)

Create `/etc/wireguard/wg0.conf`:

```ini
[Interface]
PrivateKey = <vps_private_key>
Address = 10.200.200.2/24
# Custom routing table
Table = 51820
PostUp = ip rule add fwmark 51820 table 51820
PostDown = ip rule del fwmark 51820 table 51820

[Peer]
PublicKey = <home_public_key>
Endpoint = <dave_home_ip_or_ddns>:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
```

Start WireGuard:

```bash
sudo wg-quick up wg0
sudo systemctl enable wg-quick@wg0
```

---

## 4. Selective Routing (YouTube/Reddit Only)

### Method 1: AllowedIPs (Simple but Static)

Only route specific IP ranges through tunnel:

```ini
[Peer]
PublicKey = <home_public_key>
Endpoint = <dave_home_ip>:51820
# Google/YouTube + Reddit IP ranges
AllowedIPs = 142.250.0.0/15, 172.217.0.0/16, 216.58.192.0/19, 151.101.0.0/16, 199.232.0.0/16
PersistentKeepalive = 25
```

**Known IP Ranges:**
| Service | CIDR Blocks |
|---------|-------------|
| YouTube/Google | `142.250.0.0/15`, `172.217.0.0/16`, `216.58.192.0/19`, `74.125.0.0/16` |
| Reddit | `151.101.0.0/16`, `199.232.0.0/16` |

### Method 2: Policy Routing with iptables (Flexible)

Mark specific traffic to route through WireGuard:

```bash
# Create routing table
echo "200 wgtunnel" | sudo tee -a /etc/iproute2/rt_tables

# Route marked packets through WireGuard
sudo ip route add default via 10.200.200.1 table wgtunnel

# Mark YouTube/Google traffic
sudo iptables -t mangle -A OUTPUT -d 142.250.0.0/15 -j MARK --set-mark 200
sudo iptables -t mangle -A OUTPUT -d 172.217.0.0/16 -j MARK --set-mark 200
sudo iptables -t mangle -A OUTPUT -d 216.58.192.0/19 -j MARK --set-mark 200

# Mark Reddit traffic
sudo iptables -t mangle -A OUTPUT -d 151.101.0.0/16 -j MARK --set-mark 200

# Apply routing rule
sudo ip rule add fwmark 200 table wgtunnel
```

### Method 3: Domain-Based Routing with dnsmasq + ipset

```bash
# Install
sudo apt install dnsmasq ipset

# Create ipset
sudo ipset create youtube hash:ip
sudo ipset create reddit hash:ip

# Configure dnsmasq to populate ipsets
# /etc/dnsmasq.d/wg-routing.conf
ipset=/youtube.com/googlevideo.com/ytimg.com/youtube
ipset=/reddit.com/redd.it/redditmedia.com/reddit

# Route ipset through WireGuard
sudo iptables -t mangle -A OUTPUT -m set --match-set youtube dst -j MARK --set-mark 200
sudo iptables -t mangle -A OUTPUT -m set --match-set reddit dst -j MARK --set-mark 200
```

### Persist iptables Rules

```bash
sudo apt install iptables-persistent
sudo netfilter-persistent save
```

---

## 5. Testing

### Check Tunnel Status

```bash
# On both ends
sudo wg show

# Expected output:
# interface: wg0
#   public key: ...
#   private key: (hidden)
#   listening port: 51820
#
# peer: ...
#   endpoint: x.x.x.x:51820
#   allowed ips: 10.200.200.0/24
#   latest handshake: X seconds ago  ← This means it's working!
#   transfer: X KiB received, X KiB sent
```

### Test Connectivity

```bash
# From VPS, ping home server
ping 10.200.200.1

# Check which IP YouTube sees
curl -s --interface wg0 ifconfig.me
# Should show Dave's home IP

# Without tunnel (direct)
curl -s ifconfig.me
# Should show VPS IP
```

### Test YouTube Transcript API

```bash
# Force through WireGuard interface
curl -s --interface wg0 https://www.youtube.com

# Test transcript API
python3 << 'EOF'
import socket

# Force socket to use WireGuard interface
original_getaddrinfo = socket.getaddrinfo
def patched_getaddrinfo(*args, **kwargs):
    return original_getaddrinfo(*args, **kwargs)

from youtube_transcript_api import YouTubeTranscriptApi
try:
    transcript = YouTubeTranscriptApi.get_transcript('dQw4w9WgXcQ')
    print(f"✅ Success! Got {len(transcript)} transcript segments")
    print(f"First line: {transcript[0]['text']}")
except Exception as e:
    print(f"❌ Failed: {e}")
EOF
```

### Verify Selective Routing

```bash
# YouTube IP should go through tunnel
ip route get 142.250.80.46
# Expected: via 10.200.200.1 dev wg0

# Random IP should go direct
ip route get 1.1.1.1
# Expected: via <vps_gateway> dev eth0
```

---

## 6. Troubleshooting

### Connection Refused / No Handshake

```bash
# Check home server is listening
sudo ss -ulnp | grep 51820

# Check firewall on home server
sudo iptables -L -n | grep 51820

# Test port is reachable from VPS
nc -vzu <home_ip> 51820
```

**Fixes:**
- Ensure port forwarding is configured on home router
- Check home firewall allows UDP 51820
- Verify endpoint IP/hostname is correct

### Handshake Timeout

```bash
# Check keys match
# Home server's publickey == VPS config's [Peer] PublicKey
# VPS's publickey == Home config's [Peer] PublicKey
```

**Fixes:**
- Regenerate and re-exchange keys
- Check for typos in public keys
- Ensure endpoint is reachable (try from phone hotspot)

### No Internet After Connecting

```bash
# Check MASQUERADE rule on home server
sudo iptables -t nat -L POSTROUTING -n -v

# Check IP forwarding
cat /proc/sys/net/ipv4/ip_forward  # Should be 1

# Check routing on VPS
ip route show table all | grep wg
```

**Fixes:**
- Verify PostUp iptables commands ran
- Check correct interface name in MASQUERADE rule (`eth0`, `enp0s3`, etc.)
- Enable IP forwarding: `sudo sysctl -w net.ipv4.ip_forward=1`

### DNS Issues

```bash
# Test DNS through tunnel
dig @8.8.8.8 youtube.com

# If DNS fails, add to wg0.conf [Interface]:
DNS = 8.8.8.8, 1.1.1.1
```

### High Latency

Expected: VPS→Home adds ~100-300ms depending on location.

**Mitigations:**
- Use selective routing (only route blocked services)
- Consider home server closer to VPS region

---

## 7. Security Notes

### Key Management

```bash
# Keys should be readable only by root
sudo chmod 600 /etc/wireguard/privatekey
sudo chmod 600 /etc/wireguard/wg0.conf

# Never commit keys to git
echo "privatekey" >> .gitignore
```

### Restrict Peer Access

```ini
# Only allow VPS IP to connect (home server config)
[Peer]
PublicKey = <vps_public_key>
AllowedIPs = 10.200.200.2/32
# Optional: Restrict source IP
# (WireGuard doesn't support this natively, use firewall)
```

### Firewall Hardening

```bash
# On home server - only allow WireGuard from known IPs
sudo iptables -A INPUT -p udp --dport 51820 -s <vps_ip> -j ACCEPT
sudo iptables -A INPUT -p udp --dport 51820 -j DROP
```

### fail2ban for WireGuard

WireGuard doesn't log failed auth attempts (by design), but you can monitor for port scanning:

```bash
# /etc/fail2ban/jail.local
[wireguard]
enabled = true
filter = wireguard
action = iptables-allports[name=wireguard]
logpath = /var/log/syslog
maxretry = 3
findtime = 3600
bantime = 86400
```

### Regular Key Rotation

Rotate keys periodically (monthly/quarterly):

```bash
# Generate new keys
wg genkey | tee newprivatekey | wg pubkey > newpublickey

# Update configs on both ends
# Restart WireGuard
sudo wg-quick down wg0 && sudo wg-quick up wg0
```

---

## Quick Reference

### Key Exchange Summary

| Location | Config File | Needs |
|----------|-------------|-------|
| Home Server | `/etc/wireguard/wg0.conf` | Own private key, VPS public key |
| VPS | `/etc/wireguard/wg0.conf` | Own private key, Home public key, Home endpoint |

### Commands Cheat Sheet

```bash
# Start/Stop
sudo wg-quick up wg0
sudo wg-quick down wg0

# Status
sudo wg show

# Enable on boot
sudo systemctl enable wg-quick@wg0

# View logs
sudo journalctl -u wg-quick@wg0

# Reload config without disconnect
sudo wg syncconf wg0 <(wg-quick strip wg0)
```

---

## Appendix: Full Example Configs

### Home Server (`/etc/wireguard/wg0.conf`)

```ini
[Interface]
PrivateKey = YHoMvkGzKKHOnfXzFcRj2iqWgYSMOLkNJ8x0N3k3W0E=
Address = 10.200.200.1/24
ListenPort = 51820
PostUp = iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

[Peer]
# VPS
PublicKey = aBcDeFgHiJkLmNoPqRsTuVwXyZ1234567890ABCDEFG=
AllowedIPs = 10.200.200.2/32
```

### VPS (`/etc/wireguard/wg0.conf`)

```ini
[Interface]
PrivateKey = kLmNoPqRsTuVwXyZ1234567890ABCDEFGhIjKlMnOpQ=
Address = 10.200.200.2/24

[Peer]
# Dave's Home
PublicKey = XyZ1234567890ABCDEFGhIjKlMnOpQrStUvWxYz12345=
Endpoint = dave-home.duckdns.org:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
```

*(Keys shown are examples - generate your own!)*
