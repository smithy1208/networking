#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys
from time import sleep
from concurrent.futures import ThreadPoolExecutor, as_completed
from pprint import pprint

import yaml
import telnetlib
import click


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


def send_command_to_devices(devices, command, outfile='out.txt', limit=10, **kwargs):
    with ThreadPoolExecutor(max_workers=limit) as executor:
        future_list = []
        for dev in devices:
            future = executor.submit(send_command_telnetlib, dev, command, **kwargs)
            future_list.append(future)

        with open(outfile, 'w') as dst:
            for f in as_completed(future_list):
                dst.write('#' * 50 + '\n')
                dst.write(f.result())


@click.command()
@click.option('--username', '-u', default='admin', help='UserName')
@click.option('--password', '-p', default='YouPass', help='PassWord')
@click.option('--command', '-c', required=True, help='Command for devices')
@click.option('--outfile', '-o', default='out.txt', help='Output filename')
@click.option('--switch_lst_file', '-s', required=True, help='Switches list (YAML file)')
@click.option('--limit', '-l', default=10, help='Limit of parrallel threads')
def cli(switch_lst_file, command, **kwargs):
    with open(switch_lst_file) as f:
        switches = yaml.safe_load(f)
    pprint(switches)
    send_command_to_devices(switches, command, **kwargs)


if __name__ == '__main__':
    cli()
