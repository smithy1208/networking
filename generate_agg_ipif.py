'''
Generate new ipif for agg (DGS-3627G or DGS-3620-28)
params:
src txt file like this:
10.39.3.57      ipoe-1751       10.162.89.1/24
10.39.3.57      ipoe-1752       10.162.90.1/24
'''

from pprint import pprint

import click

from generate_config import generate_config


def convert_table_to_dict(vlantable):
    vlanlist = []
    with open(vlantable) as f:
        for line in f:
            _, vlanname, ip = line.split()
            id = vlanname.split('-')[-1]
            vlanlist.append({'id': id, 'name': vlanname, 'ip': ip})
    resultdict = {}
    resultdict['vlans'] = vlanlist

    resultdict['dhcps'] = ['217.107.196.48', '217.107.196.75', '217.107.196.76']

    return resultdict


@click.command()
@click.option('--vlantable', '-t', required=True, help='Table with vlans and ip_addresses (file)')
def cli(vlantable):
    print(generate_config('templates/agg_ipif.j2', convert_table_to_dict(vlantable)))

if __name__ == '__main__':
    cli()
