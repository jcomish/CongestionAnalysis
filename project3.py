from mininet.net import Mininet
from mininet.node import UserSwitch, OVSKernelSwitch, Controller
from mininet.topo import Topo
from mininet.log import lg, info
from mininet.util import irange, quietRun
from mininet.link import TCLink
from functools import partial
from mininet.cli import CLI
import re
import os
import sys
import subprocess
import threading
import time
flush = sys.stdout.flush

class POXcontroller1(Controller):
  def start(self):
    self.pox='%s/pox/pox.py' %os.environ['HOME']
    self.cmd(self.pox, "log --file=log openflow.discovery forwarding.l2_multi > /tmp/mycontroller &")
  def stop(self):
    self.cmd('kill %'+self.pox)

controllers={'poxcontroller':POXcontroller1}

class MyTopo(Topo):
  def __init__(self, p_delay, n=2, **opts):
    Topo.__init__(self, **opts)
    
    ar1 = self.addSwitch('ar1')
    ar2 = self.addSwitch('ar2')
    br1 = self.addSwitch('br1')
    br2 = self.addSwitch('br2')

    s1 = self.addHost('s1')
    s2 = self.addHost('s2')
    r1 = self.addHost('r1')
    r2 = self.addHost('r2')

    #self.addLink('s1', 'ar1', bw=80)
    #self.addLink('s2', 'ar1', bw=80)
    #self.addLink('r1', 'ar2', bw=80)
    #self.addLink('r2', 'ar2', bw=80)

    self.addLink('s1', 'ar1', bw=960)
    self.addLink('s2', 'ar1', bw=960)
    self.addLink('r1', 'ar2', bw=960)
    self.addLink('r2', 'ar2', bw=960)
    
    #self.addLink('ar1', 'br1', bw=21, max_queue_size=int(.2 * 21 * int(p_delay[:-2])))
    #self.addLink('ar2', 'br2', bw=21, max_queue_size=int(.2 * 21 * int(p_delay[:-2])))
    #self.addLink('br1', 'br2', bw=82, delay=p_delay) # add max queue size?
    self.addLink('ar1', 'br1', bw=252, max_queue_size=int(.2 * 21 * int(p_delay[:-2])))
    self.addLink('ar2', 'br2', bw=252, max_queue_size=int(.2 * 21 * int(p_delay[:-2])))
    self.addLink('br1', 'br2', bw=984, delay=p_delay)

def myIperf(net, hosts, seconds, port, filename):
   info( "nohup iperf start with " + str(hosts), '\n')
   hosts = hosts# or [ self.hosts[ 0 ], self.hosts[ -1 ] ]
   assert len( hosts ) == 2
   client, server = hosts
   info( '*** Iperf: testing TCP bandwidth between',
           client, 'and', server, '\n' )
   iperfArgs = 'nohup iperf -p %d ' % port
   server_cmd = iperfArgs + '-s -i 0.1 -f \'m\' > ' + filename
   info( "server command: " + server_cmd , '\n' )
   server.sendCmd( server_cmd )
   client_cmd = iperfArgs + '-t %d -c ' % seconds + server.IP() + ' -mss 1500' 
   info( "client command: " + client_cmd, '\n' )
   cliout = client.cmd( client_cmd )
   servout = ''
   # We want the last *b/sec from the iperf server output
   # for TCP, there are two fo them because of waitListening
   count = 2
   while len( re.findall( '/sec', servout ) ) < count:
       servout += server.monitor( timeoutms=5000 )
   server.sendInt()
   servout += server.waitOutput()
   info( 'Server output: %s\n' % servout, '\n' )
   info( "iperf end with " + str(hosts), '\n')

def bandwidthTest(algorithm, delay):

    "Check bandwidth at various lengths along a switch chain."

    results = {}

    switches = { 'reference user': UserSwitch,
                 'Open vSwitch kernel': OVSKernelSwitch }
    del switches[ 'reference user' ]

    topo = MyTopo(delay, n=3)
    
    output = quietRun("sysctl -w net.ipv4.tcp_congestion_control=" + algorithm)
    assert algorithm in output

    for datapath in switches.keys():
        info( "*** testing", datapath, "datapath\n" )
        Switch = switches[ datapath ]
        results[ datapath ] = []
        link = partial( TCLink, delay='2ms', bw=10 )
        net = Mininet( topo=topo, switch=Switch,
                       controller=Controller, waitConnected=True,
                       link=link )
        net.start()
        info( "*** testing basic connectivity\n" )
        for n in range(0, 4):
            net.ping( [ net.hosts[ 0 ], net.hosts[ n ] ] )
        info( "*** testing bandwidth\n" )
        for n in range(2, 4):
            src, dst = net.hosts[ 0 ], net.hosts[ n ]
            # Try to prime the pump to reduce PACKET_INs during test
            # since the reference controller is reactive
            src.cmd( 'telnet', dst.IP(), '5001' )
            info( "testing", src.name, "<->", dst.name, '\n' )
	
	t1 = threading.Thread(target=myIperf, args=(net, (net.hosts[2], net.hosts[0]), 1000, 5001, "/home/mininet/projects/modlogs/" + algorithm + delay + "1.modlog" ))
        t2 = threading.Thread(target=myIperf, args=(net, (net.hosts[3], net.hosts[1]), 750, 5001, "/home/mininet/projects/modlogs/" + algorithm + delay + "2.modlog"))
        t1.start()
        time.sleep(250)
        t2.start()
        time.sleep(780)

        #net.stop()
        info( '\n')
    info( '\n' )

if __name__ == '__main__':
    lg.setLogLevel( 'info' )
    delays = ["21ms", "81ms", "162ms"]
    algorithms = ["reno", 
                  "cubic", 
                  "prr", 
                  "pbr"]
    #algorithms = ["reno"]
    # Setup tcpprobe
    subprocess.call("sudo modprobe tcp_probe port=5001", shell=True)
    for algorithm in algorithms:
	for delay in delays:
            subprocess.call("sudo mn -c", shell=True)
	    subprocess.call("sudo pkill -f iperf -9", shell=True)
            subprocess.call("sudo pkill -f tcpprobe -9", shell=True)
            # Cat the logs
	    subprocess.call("sudo cat /proc/net/tcpprobe > /home/mininet/projects/logs/" + algorithm + delay + ".log  &", shell=True)
            
            # Clean the environment
            info( "*** Running bandwidthTest " + algorithm + " " + delay + '\n' )
            bandwidthTest(algorithm, delay)

            # Kill all iperf and tcpprobe to start fresh
