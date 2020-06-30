#!/usr/bin/env python
# -*- coding: utf-8 -*-

import telnetlib
import re
from time import sleep
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

from pysnmp.hlapi import *
import yaml
import nmap
import textfsm
import click
from tabulate import tabulate


def bulk(self, cmd, opt):
    '''
    Функция заглушка, связа с реализацией telnet на D-Link
    telnetlib не будет отвечать на всякие DO SGA, WILL SGA... И свитч станет адекватней
    https://forum.dlink.ru/viewtopic.php?f=2&t=143853&hilit=telnetlib#p764356
    '''
    pass


def send_command_telnetlib(ipaddress, command, username='admin', password=''):
    '''
    Функция для отправки одной команды на коммутатор D-Link
    Возвращает результат команды в виде строки
    '''
    com = command.encode('ascii')
    user = username.encode('ascii')
    passwd = password.encode('ascii')

    prompt = b'\S+:.*#'

    print(f'Подключение к {ipaddress}...')
    try:
        with telnetlib.Telnet(ipaddress) as t:
            t.set_option_negotiation_callback(bulk)

            t.expect([b'[Uu]ser[Nn]ame:'])
            t.write(user + b'\n')
            t.expect([b'[Pp]ass[Ww]ord:'])
            t.write(passwd + b'\n')
            t.expect([prompt])
            sleep(1)
            t.write(b'disable clipaging' + b'\n')
            t.expect([prompt])
            t.write(com + b'\n')

            sleep(3)

            output = t.read_very_eager().decode('ascii')
            # print(output)

            sleep(1)

            t.write(b'\n')
            t.expect([prompt])
            t.write(b'enable clipaging' + b'\n')

            sleep(1)
    except (ConnectionRefusedError, OSError) as err:
        output = str(err)

    return ipaddress + '\n' + output + '\n'


def send_command_to_devices(devices, limit=10, **kwargs):
    with ProcessPoolExecutor(max_workers=limit) as executor:
        future_list = []
        for dev in devices:
            ip, descr = list(dev.items())[0]
            command = gen_lldp_command(descr)
            if command:
                future = executor.submit(send_command_telnetlib, ip, command, **kwargs)
                future_list.append(future)
        result = []
        for f in as_completed(future_list):
            result.append(parse_lldp_out(f.result()))
        return result


def snmpget_from_devices(devices, oid, limit=10):
    with ThreadPoolExecutor(max_workers=limit) as executor:
        future_list = []
        for dev in devices:
            future = executor.submit(snmp_get, dev, oid)
            future_list.append(future)

        devices = []
        for f in as_completed(future_list):
            dev = f.result()
            if dev:
                devices.append(f.result())
        return devices


def nmap_avalible(network):
    '''
    Check ip with nmap.

    return list avalible ip from network
    '''
    nm = nmap.PortScanner()
    nm.scan(network, arguments='-sP')
    return nm.all_hosts()


# sysDescr
# oid = .1.3.6.1.2.1.1.1.0
def snmp_get(host, oid, community='public'):
    errorIndication, errorStatus, errorIndex, varBinds = next(
        getCmd(SnmpEngine(),
               CommunityData(community),
               UdpTransportTarget((host, 161)),
               ContextData(),
               ObjectType(ObjectIdentity(oid)))
    )

    if errorIndication:
        print(errorIndication)
    elif errorStatus:
        print('%s at %s' % (errorStatus.prettyPrint(),
                            errorIndex and varBinds[int(errorIndex) - 1][0] or '?'))
    else:
        for varBind in varBinds:
            # print(' = '.join([x.prettyPrint() for x in varBind]))
            r = [x.prettyPrint() for x in varBind]
            # return r[-1]
            return {host: r[-1]}


def parce_models(models_yml, out):
    regex = re.compile(r'(D[EG]S-\d{4}(?:-\d{2})?)')
    with open(models_yml) as f:
        models_src = yaml.safe_load(f)
    mods = []
    for line in models_src:
        match = regex.search(line)
        if match:
            mods.append(match.group(1))

    model_ports = {model: model[-2:]
                   for model in mods}
    with open(out, 'w') as dst:
        yaml.dump(model_ports, dst)


def gen_lldp_command(description, models_file='data/models.yml'):
    with open(models_file) as f:
        models_dict = yaml.safe_load(f)
    templ = 'sh lldp rem {} m d'

    for mod, ports in models_dict.items():
        if mod in description:
            return templ.format(ports)


def parse_lldp_out(command_output, template='templates/dlink_lldp.fsm'):
    with open(template) as tmpl:
        parser = textfsm.TextFSM(tmpl)
        return parser.ParseTextToDicts(command_output)


@click.command()
@click.option('--username', '-u', default='admin', help='UserName')
@click.option('--password', '-p', default='YouPass', help='PassWord')
@click.option('--network', '-n', required=True, help='mngt network')
@click.option('--limit', '-l', default=10, help='Limit of parrallel threads')
def cli(network, **kwargs):
    ring = nmap_avalible(network)

    oid = '.1.3.6.1.2.1.1.1.0'
    devices = snmpget_from_devices(ring, oid)
    print(devices)

    res = send_command_to_devices(devices, **kwargs)

    all_data = [portid for host in res for portid in host]
    print(tabulate(all_data, headers='keys'))


if __name__ == '__main__':
    cli()
