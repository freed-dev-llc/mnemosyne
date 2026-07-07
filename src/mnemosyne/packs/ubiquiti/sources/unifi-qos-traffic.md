# UniFi QoS and traffic management

> **About this file:** a self-authored primer for this repo: original prose on UniFi networking
> practices. It is illustrative guidance, not official Ubiquiti documentation; verify specifics
> against current UniFi docs before acting.

## Smart Queues tame bufferbloat

**Smart Queues** is UniFi's answer to **bufferbloat** — the latency spike that appears when a
saturated link fills its buffers and time-sensitive traffic waits behind a bulk transfer. It runs
an **fq_codel** (fair-queuing controlled-delay) scheduler on the gateway that keeps the queue short
so interactive traffic stays responsive under load. Set the download and upload limits just below
your measured ISP line rate, so the queue forms on the gateway where **fq_codel** controls it
rather than in the ISP's own buffers. The trade is a little peak throughput for far lower latency;
enable it on gateways whose CPU can shape at your line rate.

## Marking traffic priority with DSCP

Quality of Service prioritizes classes of traffic when the link is congested. UniFi marks priority
with a **DSCP** value (a Differentiated Services Code Point) in the IP header, and it can honor an
existing **DSCP** or **IP Precedence** marking already set by an application or an upstream device.
Traffic rules apply the marking per application or per client, so voice and video win the queue
over bulk downloads. Marks only matter under contention — an uncongested link forwards everything
regardless.

## WMM prioritizes traffic over WiFi

Over the air, wireless QoS is **WMM** (WiFi Multimedia), the Wi-Fi Alliance profile of the
**802.11e** standard. It sorts frames into four access categories — voice, video, best effort, and
background — and gives voice and video shorter wait times so a call is not stalled by a backup.
**WMM** is also required for the higher data rates of 802.11n and later, so leave it enabled; it is
what carries the DSCP priority above through to the wireless hop.

## Rate limiting and identification

To cap traffic rather than prioritize it, a bandwidth profile (a per-user or per-network rate
limit) sets a hard ceiling — the usual way to keep a guest network from starving everything else.
**DPI** (Deep Packet Inspection) classifies traffic by application so you can see and shape it by
category. A rate limit bounds how much a client may use; QoS decides who goes first when the link
is full.
