# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import commands
import yaml
import sys

from os_faults.ansible import executor
from os_faults.api import cloud_management
from os_faults.api import error
from os_faults.api import node_collection
from os_faults.common import service
from os_faults import utils

LOG = logging.getLogger(__name__)

class simpleObj(object):
    foo = False

def alt_execute_on_master_node(params):
    cmd = str(params['command'])
    call = cmd[:cmd.index(' ')]
    args = cmd[cmd.index(' ') + 1:]
    output  = commands.getstatusoutput(cmd)[1]
    results = []
    result = simpleObj()
    payload = {}
    payload['stdout'] = output
    result.payload = payload
    results.append(result)
    return results

class TCPCloudNodeCollection(node_collection.NodeCollection):

    def connect(self, network_name):
        LOG.info("Connect network '%s' on nodes: %s", network_name, self)
        task = {'fuel_network_mgmt': {
            'network_name': network_name,
            'operation': 'up',
        }}
        self.cloud_management.execute_on_cloud(self.get_ips(), task)

    def disconnect(self, network_name):
        LOG.info("Disconnect network '%s' on nodes: %s",
                 network_name, self)
        task = {'fuel_network_mgmt': {
            'network_name': network_name,
            'operation': 'down',
        }}
        self.cloud_management.execute_on_cloud(self.get_ips(), task)


SALT_CALL = 'salt-call --local --retcode-passthrough '
SALT_RESTART = SALT_CALL + 'service.restart {service}'
SALT_TERMINATE = SALT_CALL + 'service.stop {service}'
SALT_START = SALT_CALL + 'service.start {service}'

BASH = 'bash -c "{}"'
FIND_Q = 'ps ax | grep -q {}'
FIND_E = 'ps ax | grep -e {}'
EXCLUDE = 'ps ax | grep -qv {}'


class SaltService(service.ServiceAsProcess):

    @utils.require_variables('SALT_SERVICE')
    def __init__(self, *args, **kwargs):
        super(SaltService, self).__init__(*args, **kwargs)

        self.RESTART_CMD = SALT_RESTART.format(service=self.SALT_SERVICE)
        self.TERMINATE_CMD = SALT_TERMINATE.format(service=self.SALT_SERVICE)
        self.START_CMD = SALT_START.format(service=self.SALT_SERVICE)
        self.FIND_CMD = BASH.format(FIND_E.format(self.GREP))


class KeystoneService(SaltService):
    SERVICE_NAME = 'apache2'
    GREP = ['[k]eystone','[a]pache2']
    SALT_SERVICE = 'apache2'
    def __init__(self, *args, **kwargs):
        super(KeystoneService, self).__init__(*args, **kwargs)
        self.FIND_CMD = BASH.format(' && '.join([FIND_Q.format(g) for g in self.GREP[:-1]]) +
                                    ' && ' + FIND_E.format(self.GREP[-1]))


class HorizonService(SaltService):
    SERVICE_NAME = 'horizon'
    GREP = '[a]pache2'
    IGNORE = '[k]eystone'
    SALT_SERVICE = 'apache2'
    def __init__(self, *args, **kwargs):
        super(HorizonService, self).__init__(*args, **kwargs)
        self.FIND_CMD = BASH.format(FIND_Q.format(self.GREP) + ' && ' +
                                    FIND_E.format(self.IGNORE) + ' | ' +
                                    EXCLUDE.format(self.IGNORE))


class MemcachedService(SaltService):
    SERVICE_NAME = 'memcached'
    GREP = '[m]emcached'
    SALT_SERVICE = 'memcached'


class MySQLService(SaltService):
    SERVICE_NAME = 'mysql'
    GREP = '[m]ysqld '
    SALT_SERVICE = '\'mysqld\''
    PORT = ('tcp', 3307)
    def __init__(self, *args, **kwargs):
        super(MySQLService, self).__init__(*args, **kwargs)
        self.RESTART_CMD = SALT_RESTART.format(service=self.SERVICE_NAME)
        self.TERMINATE_CMD = SALT_TERMINATE.format(service=self.SERVICE_NAME)
        self.START_CMD = SALT_START.format(service=self.SERVICE_NAME)


class RabbitMQService(SaltService):
    SERVICE_NAME = 'rabbitmq'
    GREP = '[r]abbitmq'
    SALT_SERVICE = 'rabbitmq'


class GlanceAPIService(SaltService):
    SERVICE_NAME = 'glance-api'
    GREP = '[g]lance-api'
    SALT_SERVICE = 'glance-api'


class GlanceRegistryService(SaltService):
    SERVICE_NAME = 'glance-registry'
    GREP = '[g]lance-registry'
    SALT_SERVICE = 'glance-registry'


class NovaApiMetadataService(SaltService):
    SERVICE_NAME = 'nova-api-metadata'
    GREP = '[n]ova-api-metadata'
    SALT_SERVICE = 'nova-api-metadata'


class NovaApiOsComputeService(SaltService):
    SERVICE_NAME = 'nova-api-os-compute'
    GREP = '[n]ova-api-os-compute'
    SALT_SERVICE = 'nova-api-os-compute'


class NovaCertService(SaltService):
    SERVICE_NAME = 'nova-cert'
    GREP = '[n]ova-cert'
    SALT_SERVICE = 'nova-cert'


class NovaComputeService(SaltService):
    SERVICE_NAME = 'nova-compute'
    GREP = '[n]ova-compute'
    SALT_SERVICE = 'nova-compute'

    def __init__(self, *args, **kwargs):
        super(NovaComputeService, self).__init__(*args, **kwargs)
        self.FIND_CMD = BASH.format('initctl list | grep -e {}'.format(self.GREP))


class NovaConductorService(SaltService):
    SERVICE_NAME = 'nova-conductor'
    GREP = '[n]ova-conductor'
    SALT_SERVICE = 'nova-conductor'


class NovaConsoleAuthService(SaltService):
    SERVICE_NAME = 'nova-consoleauth'
    GREP = '[n]ova-consoleauth'
    SALT_SERVICE = 'nova-consoleauth'


class NovaSchedulerService(SaltService):
    SERVICE_NAME = 'nova-scheduler'
    GREP = '[n]ova-scheduler'
    SALT_SERVICE = 'nova-scheduler'


class NovaSpiceService(SaltService):
    SERVICE_NAME = 'nova-spicehtml5proxy'
    GREP = '[n]ova-spicehtml5proxy'
    SALT_SERVICE = 'nova-spicehtml5proxy'


class HeatAPIService(SaltService):
    SERVICE_NAME = 'heat-api'
    GREP = '[h]eat-api '
    SALT_SERVICE = 'heat-api'


class HeatEngineService(SaltService):
    SERVICE_NAME = 'heat-engine'
    GREP = '[h]eat-engine'
    SALT_SERVICE = 'heat-engine'


class CinderAPIService(SaltService):
    SERVICE_NAME = 'cinder-api'
    GREP = '[c]inder-api'
    SALT_SERVICE = 'cinder-api'


class CinderSchedulerService(SaltService):
    SERVICE_NAME = 'cinder-scheduler'
    GREP = '[c]inder-scheduler'
    SALT_SERVICE = 'cinder-scheduler'


class CinderVolumeService(SaltService):
    SERVICE_NAME = 'cinder-volume'
    GREP = '[c]inder-volume'
    SALT_SERVICE = 'cinder-volume'


class SwiftProxyService(SaltService):
    SERVICE_NAME = 'swift-proxy-server'
    GREP = '[s]wift-proxy-server'
    SALT_SERVICE = 'swift-proxy-server'


class SwiftAccountAuditorService(SaltService):
    SERVICE_NAME = 'swift-account-auditor'
    GREP = '[s]wift-account-auditor'
    SALT_SERVICE = 'swift-account-auditor'


class SwiftAccountReaperService(SaltService):
    SERVICE_NAME = 'swift-account-reaper'
    GREP = '[s]wift-account-reaper'
    SALT_SERVICE = 'swift-account-reaper'


class SwiftAccountReplicatorService(SaltService):
    SERVICE_NAME = 'swift-account-replicator'
    GREP = '[s]wift-account-replicator'
    SALT_SERVICE = 'swift-account-replicator'


class SwiftAccountServerService(SaltService):
    SERVICE_NAME = 'swift-account-server'
    GREP = '[s]wift-account-server'
    SALT_SERVICE = 'swift-account-server'


class SwiftContainerAuditorService(SaltService):
    SERVICE_NAME = 'swift-container-auditor'
    GREP = '[s]wift-container-auditor'
    SALT_SERVICE = 'swift-container-auditor'


class SwiftContainerReconcilerService(SaltService):
    SERVICE_NAME = 'swift-container-reconciler'
    GREP = '[s]wift-container-reconciler'
    SALT_SERVICE = 'swift-container-reconciler'


class SwiftContainerReplicatorService(SaltService):
    SERVICE_NAME = 'swift-container-replicator'
    GREP = '[s]wift-container-replicator'
    SALT_SERVICE = 'swift-container-replicator'


class SwiftContainerServerService(SaltService):
    SERVICE_NAME = 'swift-container-server'
    GREP = '[s]wift-container-server'
    SALT_SERVICE = 'swift-container-server'


class SwiftContainerSyncService(SaltService):
    SERVICE_NAME = 'swift-container-sync'
    GREP = '[s]wift-container-sync'
    SALT_SERVICE = 'swift-container-sync'


class SwiftContainerUpdaterService(SaltService):
    SERVICE_NAME = 'swift-container-updater'
    GREP = '[s]wift-container-updater'
    SALT_SERVICE = 'swift-container-updater'


class SwiftObjectAuditorService(SaltService):
    SERVICE_NAME = 'swift-object-auditor'
    GREP = '[s]wift-object-auditor'
    SALT_SERVICE = 'swift-object-auditor'


class SwiftObjectExpirerService(SaltService):
    SERVICE_NAME = 'swift-object-expirer'
    GREP = '[s]wift-object-expirer'
    SALT_SERVICE = 'swift-object-expirer'


class SwiftObjectReplicatorService(SaltService):
    SERVICE_NAME = 'swift-object-replicator'
    GREP = '[s]wift-object-replicator'
    SALT_SERVICE = 'swift-object-replicator'


class SwiftObjectServerService(SaltService):
    SERVICE_NAME = 'swift-object-server'
    GREP = '[s]wift-object-server'
    SALT_SERVICE = 'swift-object-server'


class SwiftObjectUpdaterService(SaltService):
    SERVICE_NAME = 'swift-object-updater'
    GREP = '[s]wift-object-updater'
    SALT_SERVICE = 'swift-object-updater'


class NeutronDHCPAgentService(SaltService):
    SERVICE_NAME = 'neutron-dhcp-agent'
    GREP = '[n]eutron-dhcp-agent'
    SALT_SERVICE = 'neutron-dhcp-agent'


class NeutronMetadataAgentService(SaltService):
    SERVICE_NAME = 'neutron-metadata-agent'
    GREP = '[n]eutron-metadata-agent'
    SALT_SERVICE = 'neutron-metadata-agent'


class NeutronL3AgentService(SaltService):
    SERVICE_NAME = 'neutron-l3-agent'
    GREP = '[n]eutron-l3-agent'
    SALT_SERVICE = 'neutron-l3-agent'


class NeutronLinuxbridgeAgentService(SaltService):
    SERVICE_NAME = 'neutron-linuxbridge-agent'
    GREP = '[n]eutron-linuxbridge-agent'
    SALT_SERVICE = 'neutron-linuxbridge-agent'


class NeutronMeteringAgentService(SaltService):
    SERVICE_NAME = 'neutron-metering-agent'
    GREP = '[n]eutron-metering-agent'
    SALT_SERVICE = 'neutron-metering-agent'

class NeutronServerService(SaltService):
    SERVICE_NAME = 'neutron-server'
    GREP = '[n]eutron-server'
    SALT_SERVICE = 'neutron-server'


class TCPCloudManagement(cloud_management.CloudManagement):
    NAME = 'tcpcloud'
    DESCRIPTION = 'TCPCloud management driver'
    NODE_CLS = TCPCloudNodeCollection
    SERVICE_NAME_TO_CLASS = {
        'keystone': KeystoneService,
        'horizon': HorizonService,
        'memcached': MemcachedService,
        'mysql': MySQLService,
        'rabbitmq': RabbitMQService,
        'glance-api': GlanceAPIService,
        'glance-registry': GlanceRegistryService,
        'nova-api-metadata': NovaApiMetadataService,
        'nova-api-os-compute': NovaApiOsComputeService,
        'nova-cert': NovaCertService,
        'nova-compute': NovaComputeService,
        'nova-conductor': NovaConductorService,
        'nova-consoleauth': NovaConsoleAuthService,
        'nova-scheduler': NovaSchedulerService,
        'nova-spicehtml5proxy': NovaSpiceService,
        'heat-api': HeatAPIService,
        'heat-engine': HeatEngineService,
        'neutron-dhcp-agent': NeutronDHCPAgentService,
        'neutron-metadata-agent': NeutronMetadataAgentService,
        'neutron-l3-agent': NeutronL3AgentService,
        'neutron-linuxbridge-agent': NeutronLinuxbridgeAgentService,
        'neutron-metering-agent': NeutronMeteringAgentService,
        'neutron-server': NeutronServerService,
        'cinder-api': CinderAPIService,
        'cinder-scheduler': CinderSchedulerService,
        'cinder-volume': CinderVolumeService,
        'swift-account-auditor': SwiftAccountAuditorService,
        'swift-account-reaper': SwiftAccountReaperService,
        'swift-account-replicator': SwiftAccountReplicatorService,
        'swift-account-server': SwiftAccountServerService,
        'swift-container-auditor': SwiftContainerAuditorService,
        'swift-container-reconciler': SwiftContainerReconcilerService,
        'swift-container-replicator': SwiftContainerReplicatorService,
        'swift-container-server': SwiftContainerServerService,
        'swift-container-sync': SwiftContainerSyncService,
        'swift-container-updater': SwiftContainerUpdaterService,
        'swift-object-auditor': SwiftObjectAuditorService,
        'swift-object-expirer': SwiftObjectExpirerService,
        'swift-object-replicator': SwiftObjectReplicatorService,
        'swift-object-server': SwiftObjectServerService,
        'swift-object-updater': SwiftObjectUpdaterService,
        'swift-proxy-server': SwiftProxyService
    }
    SUPPORTED_SERVICES = list(SERVICE_NAME_TO_CLASS.keys())
    SUPPORTED_NETWORKS = []
    CONFIG_SCHEMA = {
        'type': 'object',
        '$schema': 'http://json-schema.org/draft-04/schema#',
        'properties': {
            'address': {'type': 'string'},
            'username': {'type': 'string'},
            'private_key_file': {'type': 'string'},

        },
        'required': ['address', 'username'],
        'additionalProperties': False,
    }

    def __init__(self, cloud_management_params):
        super(TCPCloudManagement, self).__init__()

        self.master_node_address = cloud_management_params['address']
        self.username = cloud_management_params['username']
        self.private_key_file = cloud_management_params.get('private_key_file')

        self.master_node_executor = executor.AnsibleRunner(
            remote_user=self.username, private_key_file=self.private_key_file)

        self.cloud_executor = executor.AnsibleRunner(
            remote_user=self.username, private_key_file=self.private_key_file,
            jump_host=self.master_node_address)

        self.cached_cloud_hosts = list()
        self.fqdn_to_hosts = dict()

    def verify(self):
        """Verify connection to the cloud."""
        hosts = self._get_cloud_hosts()
        LOG.debug('Cloud nodes: %s', hosts)

        task = {'command': 'hostname'}
        host_addrs = [host.ip for host in hosts]
        task_result = self.execute_on_cloud(host_addrs, task)
        LOG.debug('Hostnames of cloud nodes: %s',
                  [r.payload['stdout'] for r in task_result])

        LOG.info('Connected to cloud successfully!')

    def _get_cloud_hosts(self):
        if not self.cached_cloud_hosts:
            cmd = "salt -E '(infra(-|0)[0-9](_|-).*|compute(-|0).*|network(-|0)[0-9](_|-).*|cinder(-|0)[0-9].*|swift(-|0)[0-9].*)' network.interfaces --out=yaml"
            result = self.execute_on_master_node({'command': cmd})
            stdout = result[0].payload['stdout']
            for fqdn, net_data in yaml.load(stdout).items():
                try:
                    host = node_collection.Host(
                        ip=net_data['eth1']['inet'][0]['address'],
                        mac=net_data['eth1']['hwaddr'],
                        fqdn=fqdn)
                except KeyError:
                    regex_ipaddr = '([0-9]{1,3}\.){3}[0-9]{1,3}'
                    regex_mac = '([0-9a-z]{2}\:){5}[0-9a-z]{2}'
                    fqdn_split = fqdn.split()[0]
                    ip_cmd = BASH.format(
                        'grep -w {} /etc/hosts | grep -oE \'{}\''.format(
                            fqdn_split, regex_ipaddr
                        )
                    )
                    ip_res = alt_execute_on_master_node({'command': ip_cmd})
                    ip_out = ip_res[0].payload['stdout']
                    try:
                        mac_cmd = BASH.format(
                            'arp -an {} | grep -oE \'{}\''.format(
                                ip_out, regex_mac
                            )
                        )
                        mac_res = alt_execute_on_master_node({'command': mac_cmd})
                        mac_out = mac_res[0].payload['stdout']
#                        LOG.info('mac address is: ' + str(mac_out))
                    except:
                        sys.stdout.write('.')
                        sys.stdout.flush()
                        mac_cmd = BASH.format(
                            'arping {} -i br-control -c1 -r'.format(ip_out)
                        )
                        mac_res = alt_execute_on_master_node({'command': mac_cmd})
                        mac_out = mac_res[0].payload['stdout']
 #                       LOG.info('mac address is: ' + str(mac_out))
                    host = node_collection.Host(
                        ip=ip_out,
                        mac=mac_out,
                        fqdn=fqdn_split)
                self.cached_cloud_hosts.append(host)
                self.fqdn_to_hosts[host.fqdn] = host
            self.cached_cloud_hosts = sorted(self.cached_cloud_hosts)
        return self.cached_cloud_hosts

    def execute_on_master_node(self, task):
        """Execute task on salt master node.

        :param task: Ansible task
        :return: Ansible execution result (list of records)
        """
#	LOG.info('running on master node: ' + str(task))
        return self.master_node_executor.execute(
            [self.master_node_address], task)

    def execute_on_cloud(self, hosts, task, raise_on_error=True):
        """Execute task on specified hosts within the cloud.

        :param hosts: List of host FQDNs
        :param task: Ansible task
        :param raise_on_error: throw exception in case of error
        :return: Ansible execution result (list of records)
        """
        LOG.info('executing on remote hosts %s: %s',str(hosts), str(task)) 
        if raise_on_error:
            return self.cloud_executor.execute(hosts, task)
        else:
            return self.cloud_executor.execute(hosts, task, [])

    def get_nodes(self, fqdns=None):
        """Get nodes in the cloud

        This function returns NodesCollection representing all nodes in the
        cloud or only those that were specified by FQDNs.
        :param fqdns: list of FQDNs or None to retrieve all nodes
        :return: NodesCollection
        """
        hosts = self._get_cloud_hosts()

        if fqdns:
            #LOG.debug('Trying to find nodes with FQDNs: %s', fqdns)
            #LOG.info('Value for fqdns %s:',str(fqdns))
            hosts = []
            for fqdn in fqdns:
                if fqdn in self.fqdn_to_hosts:
                    hosts.append(self.fqdn_to_hosts[fqdn])
                else:
                    raise error.NodeCollectionError(
                        'Node with FQDN \'%s\' not found!' % fqdn)
            #LOG.debug('The following nodes were found: %s', hosts)
        #LOG.info('Cloud hosts are %s',str(hosts))
        return self.NODE_CLS(cloud_management=self,
                             power_management=self.power_management,
                             hosts=hosts)
