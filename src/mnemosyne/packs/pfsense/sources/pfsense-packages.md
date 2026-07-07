# pfSense: packages

## IDS and IPS: Snort and Suricata

pfSense adds intrusion detection and prevention through two add-on packages, Snort and Suricata.
IDS stands for Intrusion Detection System, which alerts on suspicious traffic; IPS stands for
Intrusion Prevention System, which also blocks it. Suricata is multithreaded and can use NETMAP to
run as an inline IPS.

## pfBlockerNG: DNSBL and GeoIP

The pfBlockerNG package blocks unwanted traffic by address and by domain. Its DNSBL feature is a DNS
blocklist that sinks lookups for known-bad domains, and its GeoIP feature blocks whole countries
using the MaxMind GeoLite2 database.

## Installing packages

Packages are installed from System > Package Manager and each one is maintained separately from the
base pfSense system, so the core stays lean and you add only what you need.
