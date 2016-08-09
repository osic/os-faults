# -*- coding: utf-8 -*-

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import pbr.version

from os_failures.drivers import fuel
from os_failures.drivers import kvm

__version__ = pbr.version.VersionInfo(
    'os_failures').version_string()


def build_client(cloud_config):
    cloud_management = None
    cloud_management_params = cloud_config.get('cloud_management') or {}

    if 'fuel' in cloud_management_params:
        cloud_management = fuel.FuelManagement(cloud_management_params['fuel'])

    power_management = None
    power_management_params = cloud_config.get('power_management') or {}

    if 'kvm' in power_management_params:
        power_management = kvm.KVM(power_management_params['kvm'])

    cloud_management.set_power_management(power_management)

    return cloud_management