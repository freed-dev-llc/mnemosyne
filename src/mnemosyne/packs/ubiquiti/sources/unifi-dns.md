# UniFi DNS, resolution, and multicast

> **About this file:** a self-authored primer for this repo: original prose on UniFi networking
> practices. It is illustrative guidance, not official Ubiquiti documentation; verify specifics
> against current UniFi docs before acting.

## The gateway as DNS resolver

By default the UniFi gateway is the network's **DNS** resolver and forwarder. DHCP hands each
client the gateway's address as its DNS server; the gateway answers what it can from cache and its
local records and forwards the rest to an upstream resolver. **DNS** runs on **port 53** over both
UDP and TCP — UDP for ordinary lookups, TCP for large answers and zone transfers — so a firewall
rule that blocks **port 53** breaks name resolution for every client behind it.

## Local DNS records for internal names

You can create local DNS records on the gateway so internal names resolve without an external
service. The types you can create are an **A record** and an AAAA record (a name to an address), a
**CNAME** (an alias that points one name at another), and an **SRV** record (which advertises a
service's host and port), plus TXT and MX where you need them. In practice you set an **A record**
for a server's fixed name and a **CNAME** to give that server friendly aliases.

## Forwarding a domain upstream

Conditional forwarding sends queries for one domain to a specific upstream resolver instead of the
default. Point an internal domain at a directory server, or a sensitive zone at a filtering
resolver, while everything else uses your normal upstream. To protect the upstream hop itself,
**DNS over HTTPS (DoH)** and DNS over TLS (DoT) encrypt the gateway's queries so they cannot be
read or tampered with in transit.

## mDNS across VLANs

Service discovery for AirPlay, Chromecast, and network printers uses **mDNS** (multicast DNS) on
UDP port **5353**, and multicast traffic does not cross a routed **VLAN** boundary on its own. Once
you segment a network — media devices on one **VLAN**, laptops on another — those services vanish
from each other's view. UniFi's **mDNS** reflector (an mDNS repeater) relays the announcements
between the VLANs you choose, so discovery works across segments without collapsing them back into
one flat network.
