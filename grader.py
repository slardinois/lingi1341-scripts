import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../ipmininet'))

import ipmininet
from ipmininet.cli import IPCLI
from ipmininet.ipnet import IPNet
from ipmininet.iptopo import IPTopo
from mininet.log import lg as log
from ipmininet.clean import cleanup

import time

############################# Only for testing ############################
from ipmininet.router.config import RouterConfig


from ipmininet.router.config import BGP, iBGPFullMesh, AS,\
                                    ebgp_session, OSPF6, RouterConfig,\
                                    peer_connection, provider_customer_connection
import ipmininet.router.config.bgp as _bgp


class EBGPExample(IPTopo):
    def build(self, *args, **kwargs):
        # Add all routers
        as1r1 = self.addRouter_v6('as1r1', config=(RouterConfig, {
            'daemons': [(BGP, {'address_families': (
                                    _bgp.AF_INET6(networks=('1:1:1::/48',)),),
                               'advertisement_timer': 1})]}))
                               
        as2r1 = self.addRouter_v6('as2r1', config=(RouterConfig, {
            'daemons': [(BGP, {'address_families': (
                                    _bgp.AF_INET6(networks=('1:1:2::/48',)),),
                               'advertisement_timer': 1})]}))

        as3r1 = self.addRouter_v6('as3r1', config=(RouterConfig, {
            'daemons': [(BGP, {'address_families': (
                                    _bgp.AF_INET6(networks=('1:1:3::/48',)),), 
                               'advertisement_timer': 1})]}))

        as4r1 = self.addRouter_v6('as4r1', config=(RouterConfig, {
            'daemons': [(BGP, {'address_families': (
                                    _bgp.AF_INET6(networks=('1:1:4::/48',)),),
                               'advertisement_timer': 1})]}))

        self.addLink(as1r1, as2r1, igp_metric=1)
        self.addLink(as2r1, as3r1, igp_metric=1)
        self.addLink(as3r1, as4r1, igp_metric=1)
        self.addLink(as1r1, as4r1, igp_metric=1)
        # Set AS-ownerships
        as1 = AS(1, (as1r1,))
        as2 = AS(2, (as2r1,))
        as3 = AS(3, (as3r1,))
        as4 = AS(4, (as4r1,))
        self.addOverlay(as1)
        self.addOverlay(as2)
        self.addOverlay(as3)
        self.addOverlay(as4)
        # Add eBGP peering
        ebgp_session(self, as1r1, as2r1)
        ebgp_session(self, as2r1, as3r1)
        ebgp_session(self, as3r1, as4r1)
        ebgp_session(self, as1r1, as4r1)


        provider_customer_connection(self, as1, as2)
        super(EBGPExample, self).build(*args, **kwargs)

    def addRouter_v6(self, name, **kwargs):
        return self.addRouter(name, use_v4=False, use_v6=True, **kwargs)


class IBGPExample(IPTopo):
    def build(self, *args, **kwargs):
        # Add all routers
        as1r1 = self.addRouter_v6('as1r1', config=(RouterConfig, {
            'daemons': [(BGP, {'address_families': (
                                    _bgp.AF_INET6(networks=('1:1:1::/48',)),),
                               'advertisement_timer': 1})]}))
                               
        as2r1 = self.addRouter_v6('as2r1', config=(RouterConfig, {
            'daemons': [(BGP, {'address_families': (
                                    _bgp.AF_INET6(networks=('1:1:2::/48',)),),
                               'routerid': '1.1.1.1',
                               'advertisement_timer': 1}), OSPF6]}))
        as2r2 = self.addRouter_v6('as2r2', config=(RouterConfig, {
            'daemons': [(BGP, {'address_families': (
                                    _bgp.AF_INET6(networks=('1:1:2::/48',)),),
                               'routerid': '1.1.1.2',
                               'advertisement_timer': 1}), OSPF6]}))
        as2r3 = self.addRouter('as2r3', config=(RouterConfig, {
            'daemons': [OSPF6, (BGP, {'advertisement_timer': 1})]}))
        x = self.addRouter('x', config=(RouterConfig, {
            'daemons': [OSPF6]}))
        y = self.addRouter('y', config=(RouterConfig, {
            'daemons': [OSPF6]}))

        as3r1 = self.addRouter_v6('as3r1', config=(RouterConfig, {
            'daemons': [(BGP, {'address_families': (
                                    _bgp.AF_INET6(networks=('1:1:3::/48',)),), 
                               'advertisement_timer': 1})]}))

        as4r1 = self.addRouter_v6('as4r1', config=(RouterConfig, {
            'daemons': [(BGP, {'address_families': (
                                    _bgp.AF_INET6(networks=('1:1:4::/48',)),),
                               'advertisement_timer': 1})]}))

        self.addLink(as1r1, as2r1, igp_metric=1)
        self.addLink(as2r1, x, igp_metric=1)
        self.addLink(x, as2r3, igp_metric=1)
        self.addLink(as2r3, y, igp_metric=1)
        self.addLink(y, as2r2, igp_metric=1)
        self.addLink(as2r2, as3r1, igp_metric=1)
        self.addLink(as3r1, as4r1, igp_metric=1)
        # Set AS-ownerships
        self.addOverlay(AS(1, (as1r1,)))
        self.addOverlay(iBGPFullMesh(2, (as2r1, as2r2, as2r3)))
        self.addOverlay(AS(3, (as3r1,)))
        self.addOverlay(AS(4, (as4r1,)))
        # Add eBGP peering
        ebgp_session(self, as1r1, as2r1)
        ebgp_session(self, as2r2, as3r1)
        ebgp_session(self, as3r1, as4r1)

        super(IBGPExample, self).build(*args, **kwargs)

    def addRouter_v6(self, name, **kwargs):
        return self.addRouter(name, use_v4=False, use_v6=True, **kwargs)

###########################################################################


class Grader:

    def __init__(self, topo=EBGPExample(), use_v4=False, use_v6=True, *args, **kwargs):
        self.RIBCommand = '(echo zebra; echo "show bgp"; sleep 1; exit;) | telnet localhost bgpd'
        self.topo = topo
        self.net = IPNet(topo=topo, use_v4=use_v4, use_v6=use_v6)

    def start_network(self):
        try:
            self.net.start()
        except:
            print('Cannot start the network.')
            self.stop_network()
            return -1

    def stop_network(self):
        self.net.stop()
        cleanup()

    def get_all_ribs(self):
        ribs = {}
        for r in self.net.routers:
            ribs[r.name] = self.get_rib(r)
        return ribs

    def get_rib(self, node):
        if node not in self.net.routers:
            return None
        out = node.cmd(self.RIBCommand)
        if 'Connection refused' not in out:
            return self._parse_rib(out)
        else:
            return None

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

if __name__ == '__main__':
    g = Grader()
    g.start_network()
    print("Waiting for bgp to converge...")
    time.sleep(0)
    print(g.get_all_ribs())
    IPCLI(g.net)
    g.stop_network()
