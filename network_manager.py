import sys
import os
import ipaddr

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../ipmininet'))

import ipmininet
from ipmininet.ipnet import IPNet
from ipmininet.iptopo import IPTopo
from mininet.log import lg as log
from ipmininet.clean import cleanup
from ipmininet.router import Router
from ipmininet.router.config import BGP, AS,\
                                    ebgp_session, RouterConfig,\
                                    set_community
import ipmininet.router.config.bgp as _bgp


def error(msg):
    print("Error => " + msg)
    exit(1)


class ASTopo(IPTopo):

    def build_topo(self):
        super(ASTopo, self).build()

    def build(self, *args, **kwargs):
        """Do not use this method, it is only needed for compatibility"""
        return

    def add_AS(self, asn, prefix):
        try:
            n = int(asn)
        except:
            error("Invalid AS number: " + str(asn))
        self._check_prefix(prefix)
        tmp = self._addRouter_v6('as'+str(n)+'r1', config=(RouterConfig, {
                'daemons': [(BGP, {'address_families': (
                                    _bgp.AF_INET6(networks=(prefix,)),),
                                    'advertisement_timer': 1})]}))
        new_as = AS(n, (tmp,))
        self.addOverlay(new_as)
        return new_as

    def provider_customer_connection(self, provider, customer):
        self._connect_ases(provider, customer)
        set_community(self, provider, customer.asn, str(provider.asn) + ':1')
        set_community(self, customer, provider.asn, str(customer.asn) + ':2')

    def peer_connection(self, as1, as2):
        self._connect_ases(as1, as2)
        set_community(self, as1, as2.asn, str(as1.asn) + ':0')
        set_community(self, as2, as1.asn, str(as2.asn) + ':0')
    
    def _addRouter_v6(self, name, **kwargs):
        return self.addRouter(name, use_v4=False, use_v6=True, **kwargs)

    def _connect_ases(self, as1, as2):
        if as1 == None or as2 == None:
            error("You are trying to make a connection with an inexisting AS!")
        if as1.nodes.count == 0 or as2.nodes.count == 0:
            error("You are trying to connect to an AS without any router.")
        self.addLink(as1.nodes[0], as2.nodes[0])
        ebgp_session(self, as1.nodes[0], as2.nodes[0])

    def _check_prefix(self, prefix):
        try:
            l = int(prefix[prefix.find("/")+1:])
            ipaddr.IPAddress(prefix[:prefix.find("/")])
            if l <= 0 or l >= 128:
                raise Error()
        except:
            error("Invalid prefix: " + prefix)


class NetworkManager:

    def __init__(self, *args, **kwargs):
        self.RIBCommand = '(echo zebra; echo "show bgp"; sleep 1; exit;) | telnet localhost bgpd'
        self.topo = ASTopo()

    def add_AS(self, asn, prefix):
        return self.topo.add_AS(asn, prefix)

    def peer_connection(self, as1, as2):
        self.topo.peer_connection(as1, as2)

    def provider_customer_connection(self, provider, customer):
        self.topo.provider_customer_connection(provider, customer)

    def start_network(self):
        try:
            self.topo.build_topo()
            self.net = IPNet(topo=self.topo, use_v4=False, use_v6=True)
            self.net.start()
        except:
            self.stop_network()
            error('Cannot start the network.')

    def stop_network(self):
        self.net.stop()
        cleanup()

    def get_all_ribs_per_router(self):
        if not self.net.is_running:
            error("The network is not running.")
        ribs = {}
        for r in self.net.routers:
            ribs[r.name] = self.get_rib(r)
        return ribs

    def get_all_ribs_per_as(self):  
        if not self.net.is_running:
            error("The network is not running.")
        ribs = {}
        for r in self.net.routers:
            ribs['as'+str(r.asn)] = self.get_rib(r)
        return ribs

    def get_rib(self, node):
        if not self.net.is_running:
            error("The network is not running.")
        r = self._get_node(node)
        if r not in self.net.routers:
            return None
        out = r.cmd(self.RIBCommand)
        if 'Connection refused' not in out:
            return self._parse_rib(out)
        else:
            return None

    def _get_node(self, node):
        if type(node) is Router:
            return node
        elif type(node) is AS:
            return next(r for r in self.net.routers if r.name == node.nodes[0])
        error("The node is neither a router nor an AS.")

    def _parse_rib(self, out):
        lines = out.split('\n')[19:-5]
        rib = {}
        dest = ''
        m = 0
        for l in lines:
            param = l.split()
            if l[3] is not ' ':
                dest = param[1]
                rib[dest] = {'primary': '', 'secondary': []}
                m = 0
            else:
                m = -1
            if param[4+m] is not '0' and param[4+m] != '32768':
                m = m-1
            if '>' in param[0]:
                rib[dest]['primary'] = ','.join(param[5+m:])
            else:
                rib[dest]['secondary'].append(','.join(param[5+m:]))
        return rib