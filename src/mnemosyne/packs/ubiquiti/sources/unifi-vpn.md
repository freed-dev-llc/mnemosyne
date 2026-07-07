# UniFi VPN and remote access

> **About this file:** a self-authored primer for this repo: original prose on UniFi networking
> practices. It is illustrative guidance, not official Ubiquiti documentation; verify specifics
> against current UniFi docs before acting.

## Two kinds of VPN

A VPN on a UniFi gateway falls into one of two shapes. A **site-to-site** VPN joins two whole
networks so hosts at each location reach the other as if they were local. A **remote-access**
(client) VPN lets a single roaming device — a laptop or a phone — dial back into the network from
anywhere. Reach for site-to-site to stitch offices together; reach for remote-access to get one
person in.

## Site Magic: automatic site-to-site SD-WAN

**Site Magic** is UniFi's automatic **site-to-site** **SD-WAN**. It meshes the UniFi gateways at
two or more locations and negotiates the tunnels for you, so you do not hand-configure endpoints,
subnets, and keys at each end. It needs a UniFi gateway at every site; the controller discovers the
sites you own and links them with a few clicks, then keeps the mesh healthy as WAN addresses
change.

## WireGuard: a fast remote-access server

The **WireGuard** VPN server is the modern choice for remote access — a lean, fast tunnel built on
current cryptography. It listens on **UDP** port **51820** by default, authenticates peers with a
public/private key pair rather than a password, and hands each client a config file or QR code to
import. Choose a full tunnel to send all of a client's traffic through the network, or a split
tunnel to route only the internal subnets and leave the rest on the client's own link.

## Teleport: zero-configuration remote access

**Teleport** is UniFi's zero-configuration remote-access VPN, built on **WireGuard** under the
hood. Instead of exporting a config, you generate a one-click **invite** link and send it to the
person; opening it in the UniFi app connects them with no manual client setup, no keys to copy, and
no port forwarding to open. It is the fastest way to grant a trusted user temporary access.

## Legacy client protocols

For older devices that cannot run WireGuard, a UniFi gateway can also present an **OpenVPN** server
or an **L2TP/IPsec** server. Both are slower and more finicky than WireGuard, but they maximize
compatibility, since most operating systems ship an L2TP/IPsec client built in and OpenVPN clients
are widely available.

## Manual IPsec to a non-UniFi peer

To build a site-to-site tunnel to a firewall that is not a UniFi gateway — a pfSense box or a cloud
VPC — configure a manual **IPsec** tunnel. You match the two ends on IKE **phase 1** (the key
exchange) and **phase 2** (the traffic selectors), sharing a **pre-shared key** and identical
encryption parameters. Site Magic only automates UniFi-to-UniFi links, so a cross-vendor tunnel is
manual IPsec.
