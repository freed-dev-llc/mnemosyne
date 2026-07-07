# OPNsense: core concepts

## What OPNsense is

OPNsense is an open-source firewall and router built on FreeBSD. It filters traffic with the
pf packet filter, the stateful packet filter FreeBSD ships, and layers a web GUI, VPNs, and a
plugin system on top. A single OPNsense box commonly serves as the edge router, firewall, DHCP
server, and VPN endpoint for a home or lab network.

## A fork of pfSense

OPNsense began in 2015 as a fork of pfSense, started by the Dutch company Deciso. It keeps the
FreeBSD and pf foundation but has diverged in the parts a user touches: a rewritten web GUI, its
own plugin system, a fixed twice-a-year release cadence, and features such as built-in Suricata
and the Zenarmor plugin that pfSense handles differently. Early OPNsense releases used a
HardenedBSD-based kernel; the base was rebased on stock FreeBSD with the 22.1 release. Treat the
two products as separate, with a common ancestor rather than drop-in equivalents.

## The web GUI

You manage OPNsense through its web GUI, reached over HTTPS at the LAN address, which defaults to
192.168.1.1 on a fresh install. The GUI is an MVC application built on the Phalcon PHP framework,
a full rewrite rather than pfSense's webConfigurator. The first login uses the user root with the
password set during installation, and a setup wizard walks through the hostname, the WAN, and the
admin password.

## Editions

OPNsense ships in two editions. The free Community Edition carries the latest features and
receives frequent updates. The commercial Business Edition, sold by Deciso, moves more slowly,
bundles a few commercial plugins, and targets production deployments that want a stabilized
release train. Both run the same core.

## Release cadence

OPNsense uses a year.month version scheme and ships two major releases a year, one in January and
one in July, so 24.1 is the January 2024 release and 24.7 the July 2024 one. Smaller point
releases land between them. The predictable twice-a-year cadence is a deliberate choice for
planning upgrades.

## Configuration in one file

The entire OPNsense configuration lives in a single XML file at /conf/config.xml. Backing up that
one file captures the whole system, and restoring it on fresh hardware rebuilds the box. The GUI
exposes backup and restore under System > Configuration > Backups.
