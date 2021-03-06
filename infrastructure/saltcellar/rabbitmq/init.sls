# ----------------------------------------------------------------------
# Numenta Platform for Intelligent Computing (NuPIC)
# Copyright (C) 2015, Numenta, Inc.  Unless you have purchased from
# Numenta, Inc. a separate commercial license for this software code, the
# following terms and conditions apply:
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses.
#
# http://numenta.org/licenses/
# ----------------------------------------------------------------------
# Formula: rabbitmq
#
# Installs rabbitmq server on an instance

# Ensure we have the directories we need with the permissions required.
/etc/rabbitmq:
  file.directory:
    - user: root
    - group: root
    - mode: 0755

# rabbitmqadmin is not included in the CentOS rabbitmq rpms, so install it
# ourselves.
/usr/local/bin/rabbitmqadmin:
  file.managed:
    - source: salt://rabbitmq/files/rabbitmqadmin
    - user: root
    - group: root
    - mode: 0755

rabbitmq-server:
  pkg.installed: []
  service.running:
    - enable: true
    - require:
      - file: /etc/rabbitmq
      - pkg: rabbitmq-server

enable-rabbitmq-management:
  cmd.run:
    - name: /usr/lib/rabbitmq/bin/rabbitmq-plugins enable rabbitmq_management
    - require:
      - service: rabbitmq-server
    - unless: grep rabbitmq_management /etc/rabbitmq/enabled_plugins
    - watch_in:
      - cmd: restart-rabbit-service

restart-rabbit-service:
  cmd.wait:
    - name: service rabbitmq-server restart
    - require:
      - pkg: rabbitmq-server
      - service: rabbitmq-server
