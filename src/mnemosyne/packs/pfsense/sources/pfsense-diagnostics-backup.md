# pfSense: diagnostics and backup

## Packet Capture

pfSense can capture traffic straight from the web interface under Diagnostics > Packet
Capture, a front end to the tcpdump packet capture tool. You choose an interface, optionally
filter by host, protocol, or port, and download the result as a .pcap file to open in
Wireshark. The same capture is available from the console by running tcpdump directly.

## Inspecting states and rules

The firewall's live state table is visible under Diagnostics > States, one entry per tracked
connection. From the console, pfTop gives a running view of the busiest states, and pfctl is
the command-line control tool for the pf packet filter — it can show the loaded rules, dump
the state table, and flush states.

## Configuration backup and restore

The entire pfSense configuration lives in a single file, config.xml. Under Diagnostics >
Backup & Restore you download that file as a backup and restore it later, which makes
rebuilding or migrating a firewall fast. A restore returns every setting — interfaces,
rules, NAT, VPNs, and installed packages — to the state saved in the file. Resetting to
factory defaults instead discards config.xml and returns pfSense to its initial 192.168.1.1
LAN configuration.
