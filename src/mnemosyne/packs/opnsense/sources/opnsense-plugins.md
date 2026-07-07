# OPNsense: plugins and extensibility

## The plugin system

OPNsense keeps a lean core and moves optional features into plugins. Every plugin carries an os-
name prefix, and you install, update, and remove them from the web GUI under System > Firmware >
Plugins. Installing a plugin adds its menu items and services without rebuilding the base system,
and removing one leaves the core untouched. Plugins are the main way an OPNsense box grows past
its built-in features.

## Plugins are FreeBSD packages

Under the hood each plugin is a FreeBSD pkg package published in the OPNsense repositories, so
installing a plugin is really a pkg install of an os- package. Common examples are os-wireguard
for the WireGuard VPN, os-acme-client for automatic Let's Encrypt certificates, and os-haproxy
for the HAProxy load balancer. Because they are ordinary packages, the firmware updater upgrades
them alongside the base system.

## Zenarmor and other security plugins

Zenarmor, formerly named Sensei, is a next-generation firewall and deep-packet-inspection engine
from Sunny Valley Networks. It installs as the os-sensei plugin, pulled from the vendor's
os-sunnyvalley repository, and adds application-aware filtering, reporting, and web controls that
the base firewall does not provide. It is the clearest example of the plugin model extending
OPNsense well beyond stock functionality.

## Themes and the plugin catalog

Beyond security, plugins cover interface themes (the os-theme- family), dynamic DNS, monitoring,
and reverse proxies. The full catalog is browsable in the GUI, and a plugin appears only after you
add any vendor repository it needs. Keeping features as plugins is what lets the core stay small
and auditable.
