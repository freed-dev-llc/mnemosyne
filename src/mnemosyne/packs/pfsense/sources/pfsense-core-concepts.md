# pfSense: core concepts

## What pfSense is

pfSense is an open-source firewall and router built on FreeBSD. It filters traffic with the
pf packet filter, the stateful packet filter FreeBSD ships, and layers a web interface, VPNs,
and add-on packages on top. A single pfSense box commonly serves as the edge router, firewall,
DHCP server, and VPN endpoint for a home or lab network.

## Interfaces: WAN and LAN

A minimal pfSense install has two interfaces. WAN faces the upstream network or ISP and is
treated as untrusted. LAN faces the internal network and is trusted. You add more interfaces
(OPT1, OPT2, and so on) for extra segments or VLANs.

## Default LAN address and first login

On a fresh install the LAN interface uses the default IP address 192.168.1.1 with a /24 subnet,
and pfSense runs a DHCP server on LAN so a client gets an address immediately. You manage pfSense
through its web interface, the webConfigurator, reached over HTTPS at the LAN IP. The first login
opens a setup wizard for the hostname, the WAN, and the admin password.

## Staying reachable: the anti-lockout rule

pfSense adds a default anti-lockout rule on the LAN so a mistaken firewall rule cannot lock an
administrator out of the webConfigurator and SSH. The rule permits management traffic from the
LAN to the firewall itself, and it stays enabled until you deliberately turn it off.

## Default posture: trust the LAN, distrust the WAN

Out of the box the LAN lets hosts reach anything outbound, while the WAN starts from a default
deny posture that blocks all unsolicited inbound traffic. You open specific inbound access on the
WAN only by adding firewall rules and NAT entries.
