# pfSense: high availability

## An active/passive HA cluster

pfSense runs high availability as a two-node cluster: one firewall is the master and the other is
the backup. If the master stops answering, the backup takes over automatically, so the network
keeps running through a hardware failure or a reboot.

## CARP virtual IPs

pfSense shares a virtual IP between the two firewalls using CARP, the
Common Address Redundancy Protocol. The master owns the CARP virtual IP (VIP) and answers for it;
if the master fails, the backup claims the same address. Each CARP VIP carries a VHID, a virtual
host ID, that must be unique for every CARP group on a network segment.

## pfsync state synchronization

The two nodes run pfsync to copy the firewall state table between them continuously. Because the
backup already holds the master's states, established connections survive the failover instead of
being reset and having to reconnect.

## XMLRPC configuration synchronization

XMLRPC configuration synchronization keeps the two firewalls' settings in step. It copies the
configuration from the primary node to the secondary, and it is enabled on the primary node only;
the secondary never pushes changes back. A dedicated Sync interface carries the pfsync and XMLRPC
traffic between the nodes.
