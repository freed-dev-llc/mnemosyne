# UniFi network security and segmentation

> **About this file:** a self-authored primer for this repo: original prose on UniFi networking
> practices. It is illustrative guidance, not official Ubiquiti documentation; verify specifics
> against current UniFi docs before acting.

## Why segment a network

Splitting a flat network into VLAN-backed segments limits the blast radius of a compromise, keeps
trust levels apart (corporate, IoT, guest), and can be a regulatory requirement (PCI-DSS, HIPAA).
Segmentation also improves performance by shrinking broadcast domains. In UniFi you create each
segment as a Network with its own VLAN ID under Settings > Networks, give it a DHCP range, then
bind it to the switch ports and WLANs that should carry it.

## A reference VLAN layout

A workable starting structure separates infrastructure from users and untrusted devices:

| VLAN ID | Name | Purpose |
|---------|------|---------|
| 1 | Management | Network infrastructure only (controller, switches, APs) |
| 10 | Corporate | Trusted workstations and servers |
| 20 | IoT | Smart devices and cameras |
| 30 | Guest | Visitor access |
| 40 | VoIP | Voice and video systems |
| 50 | Security | Cameras and access control |

The IDs are a convention, not a rule; what matters is that each trust level gets its own segment
so firewall policy can be written between segments rather than between individual hosts.

## Firewall: start from default-deny

The defensible posture is default-deny: block traffic between segments, then allow only the flows
you need. A typical rule order on a UniFi gateway is:

1. Allow established and related connections (UniFi handles this implicitly).
2. Allow the specific inter-VLAN flows you intend (for example Corporate to IoT for management).
3. Drop IoT to Corporate.
4. Drop Guest to all internal RFC1918 ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16).
5. Allow internet access.

Rules are evaluated in order, so the deny rules that protect a trusted segment must sit above any
broad allow. Firewall rules live under Settings > Firewall & Security > Firewall Rules.

## Traffic rules versus firewall rules

UniFi exposes two filtering surfaces. Firewall rules do traditional Layer 3/4 filtering:
inter-VLAN access control and port-based rules. Traffic rules act higher up: application-layer
filtering, per-client rate limiting, and QoS marking. Reach for firewall rules to decide who may
talk to whom, and traffic rules to shape or cap what an allowed client may do.

## Wireless security: WPA3 and PMF

WPA3 replaces the pre-shared-key handshake with SAE (Simultaneous Authentication of Equals), which
adds forward secrecy (a captured session cannot be decrypted later) and resists offline dictionary
attacks. WPA3 also requires Protected Management Frames (PMF), which blocks deauthentication and
disassociation attacks that spoof management frames. Set PMF to Required on a WPA3-only network and
Optional on a WPA2/WPA3 transitional network so older clients can still associate.

## RADIUS for per-user authentication

When you need individual user identity rather than a shared passphrase (enterprise networks, or
integration with Active Directory/LDAP), configure a RADIUS profile under Settings > Profiles >
RADIUS, then set the WLAN security to WPA Enterprise and point it at that profile. Each user then
authenticates with their own credentials.

## Threat management and GeoIP

UniFi's Threat Management provides intrusion detection (IDS) and prevention (IPS), known-malicious
IP blocking, and GeoIP country filtering. Sensitivity runs from Level 1 (fewest alerts, least
blocking) to Level 5 (most aggressive, more false positives); Level 3 is a reasonable starting
point. IDS/IPS inspects traffic in software and can cut gateway throughput, so on gigabit-plus
links weigh the sensitivity level against the bandwidth you need.

## Guest isolation

Two separate controls keep guests contained. Client isolation stops guest clients from seeing each
other on the same WLAN. Network isolation blocks the guest segment from reaching other VLANs and is
the default for a UniFi guest network. A captive portal adds a terms-of-service gate, optional
vouchers, and usage tracking on top.

## Management hardening

Treat the control plane as sensitive: change default credentials right after setup, enable SSH only
while troubleshooting, prefer SSH keys over passwords, restrict management access to the management
VLAN, and turn on two-factor authentication for the UniFi application. UniFi OS devices (UDM, UDR)
take `ssh root@<device-ip>` with the controller password; legacy devices (UAP, USW) take
`ssh ubnt@<device-ip>` with the default password `ubnt` until you change it.
