# pfSense: DNS services

## The DNS Resolver runs Unbound

pfSense answers DNS for the network with the DNS Resolver, which runs Unbound. Unbound is a
validating, caching, recursive resolver: it resolves names directly from the authoritative servers
and can validate them with DNSSEC. It listens on the standard DNS port 53 and is the resolver
enabled by default on a fresh install.

## The DNS Forwarder runs dnsmasq

pfSense can instead run the DNS Forwarder, which uses dnsmasq. Rather than resolving from the root
servers itself, dnsmasq forwards queries to the upstream DNS servers that pfSense learned from the
WAN. Only one of the DNS Resolver and the DNS Forwarder runs at a time, because both bind DNS
port 53.
