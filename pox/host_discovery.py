from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.packet import ethernet, arp

log = core.getLogger()

BLOCKED_MAC = "00:00:00:00:00:01"

class HostDiscovery(object):
    def __init__(self):
        self.mac_to_port = {}
        self.hosts = {}

        core.openflow.addListeners(self)

    def _handle_ConnectionUp(self, event):
        log.info("Switch connected: %s", event.connection)

    def _handle_PacketIn(self, event):
        packet = event.parsed
        if not packet.parsed:
            return

        src_mac = str(packet.src)   # convert to string for comparison
        dst_mac = packet.dst
        in_port = event.port
        dpid = event.connection.dpid

        # FIREWALL: block specific MAC
        if src_mac == BLOCKED_MAC:
            log.info("BLOCKED traffic from MAC=%s", src_mac)
            return

        # Learn MAC → port
        self.mac_to_port[packet.src] = in_port

        # Extract IP if ARP
        ip = None
        if packet.type == ethernet.ARP_TYPE:
            arp_packet = packet.payload
            ip = arp_packet.protosrc
            log.info("ARP: %s -> %s",
                     arp_packet.protosrc, arp_packet.protodst)

        # Host discovery
        if packet.src not in self.hosts:
            self.hosts[packet.src] = (ip, dpid, in_port)

            log.info("New host: MAC=%s IP=%s Switch=%s Port=%s",
                     src_mac, ip, dpid, in_port)

            log.info("Current Host Table: %s", self.hosts)

        # Forwarding logic
        if dst_mac in self.mac_to_port:
            out_port = self.mac_to_port[dst_mac]
        else:
            out_port = of.OFPP_FLOOD

        msg = of.ofp_packet_out()
        msg.data = event.ofp
        msg.actions.append(of.ofp_action_output(port=out_port))
        event.connection.send(msg)


def launch():
    core.registerNew(HostDiscovery)
