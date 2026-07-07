# pfSense: multi-WAN and traffic shaping

## Gateway groups and multi-WAN

pfSense supports multiple WAN connections for failover and load balancing. You define the
behavior with a gateway group under System > Routing > Gateway Groups, where each gateway is
assigned a tier. Gateways in the same tier share traffic for load balancing, while a
higher-numbered tier is used only when every gateway in a lower tier is down, which gives
failover. A gateway group is then selected as the gateway on a firewall rule to steer that
traffic out the chosen WAN.

## Gateway monitoring

pfSense watches each gateway with dpinger, a daemon that sends continuous pings to a monitor
IP and measures packet loss and latency. When loss or latency crosses the configured
thresholds, dpinger marks the gateway down, and that triggers failover in any gateway group
containing it. The monitor IP defaults to the gateway address but can be set to a reliable
external host.

## Traffic shaping with ALTQ

Traffic shaping prioritizes and paces traffic so latency-sensitive flows are not starved by
bulk transfers. pfSense implements shaping with ALTQ, the FreeBSD framework that attaches
queues to an interface. ALTQ supports several scheduler disciplines, including HFSC, CBQ,
PRIQ, FAIRQ, and CODELQ; the traffic shaper wizard builds a queue tree for common cases, and
firewall or floating rules then assign matching traffic to a queue.

## Limiters (dummynet)

Where ALTQ queues set priority, limiters impose hard bandwidth caps. Limiters are built on
dummynet and are configured under Firewall > Traffic Shaper > Limiters. A limiter can cap
total bandwidth or, with a source or destination mask, enforce a per-address or
per-connection ceiling — the usual way to give each user a fair share of a WAN link. A
firewall rule then assigns traffic into the limiter through its In / Out pipe settings.
