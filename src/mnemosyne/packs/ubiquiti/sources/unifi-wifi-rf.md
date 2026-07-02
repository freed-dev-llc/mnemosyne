# UniFi wireless RF and roaming

> **About this file:** a self-authored primer for this repo: original prose on UniFi networking
> practices. It is illustrative guidance, not official Ubiquiti documentation; verify specifics
> against current UniFi docs before acting.

## Channel planning by band

Good wireless starts with channel planning, and the right choice differs per band.

**2.4 GHz** has only three non-overlapping channels: 1, 6, and 11 (North America). Stay on those,
keep the channel width at 20 MHz (40 MHz doubles the footprint and collides with neighbors in dense
areas), and run transmit power at medium or lower. Lower power shrinks cell overlap, which actually
helps clients roam to a closer AP instead of clinging to a distant one.

**5 GHz** has far more room. The DFS channels (52, 56, 60, 64 in UNII-2A and 100 through 144 in
UNII-2C) are usually less congested, so prefer them where radar is not a concern; the trade-off is
that a radar event can force the AP to change channel. Use 40 MHz width for a balance of throughput
and reuse, and reserve 80 MHz for deployments with only a few APs. Enable band steering to move
dual-band clients up to 5 GHz.

**6 GHz** (WiFi 6E/7) offers clean spectrum because no legacy devices are allowed there. It supports
160 MHz and 320 MHz channels for maximum throughput but requires WPA3 (there is no WPA2 fallback),
and its range is shorter than 5 GHz, so it suits high-bandwidth use near the AP.

## Hidden SSIDs are not security

Hiding an SSID provides no real protection (it is security by obscurity), makes client devices probe
for the network and leak its name, and causes connection problems on some clients. Leave SSIDs
broadcast and rely on WPA3 for security.

## Roaming optimization

Three amendments make clients move between APs cleanly:

- **802.11r (Fast BSS Transition)** speeds the re-authentication handshake during a roam, which
  matters most for VoIP and video on enterprise WPA2/WPA3 networks. Some older clients are
  incompatible, so test before enabling in production.
- **802.11k (Neighbor Reports)** hands clients a list of nearby APs so they spend less time scanning
  when they decide to roam.
- **802.11v (BSS Transition Management)** lets an AP suggest a better AP to a client, which also
  helps load balancing.

Enable 802.11k and 802.11v broadly on modern networks; gate 802.11r on a compatibility test.

## Band steering and minimum RSSI

Band steering pushes dual-band-capable clients onto 5 GHz. "Prefer 5G" steers gently and falls back
to 2.4 GHz, which suits most sites; a strict mode forces capable devices to 5 GHz only. Minimum RSSI
disconnects a client whose signal drops below a floor so it reassociates with a closer AP: roughly
-75 dBm is aggressive, -80 dBm moderate, and -85 dBm conservative. Set it too high and marginal
clients drop repeatedly, so tune it against real client behavior.

## AP placement

Physical placement sets the ceiling on everything above. Mount APs on the ceiling for a clean
downward coverage pattern, keep them out of enclosures and away from metal, and maintain line of
sight to the area they serve. In offices, 30 to 50 feet between APs is a reasonable spacing, and
wall material matters (drywall attenuates far less than concrete or glass). In high-density spaces,
use more APs at lower power, favor 5 GHz with 20/40 MHz channels, and steer aggressively.
