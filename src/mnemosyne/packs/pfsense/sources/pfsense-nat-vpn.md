# pfSense: NAT and VPN

## Outbound NAT

Outbound NAT rewrites the private source address of internal hosts to a WAN address as their
traffic leaves the firewall. pfSense offers four outbound NAT modes: Automatic, Hybrid, Manual,
and Disabled. Automatic is the default and builds the rules for you from the connected networks.
Hybrid keeps the automatic rules and lets you add your own on top. Manual honors only the rules
you write. Disabled turns outbound NAT off entirely, which suits a network that already uses
routable addresses.

## Port forwards and 1:1 NAT

To reach an internal server from the WAN, create a port forward, a destination NAT rule that
sends a chosen WAN port to an internal host and port. pfSense can add the matching firewall rule
for the forward at the same time. For a server that needs a whole public address of its own, 1:1
NAT maps one external address to one internal address in both directions.

## Built-in VPNs

pfSense includes OpenVPN and IPsec VPNs in the base system, so you can build remote-access or
site-to-site tunnels without installing anything extra. WireGuard is available as an add-on
package. OpenVPN is flexible and firewall-friendly; IPsec interoperates well with other vendors'
gateways.
