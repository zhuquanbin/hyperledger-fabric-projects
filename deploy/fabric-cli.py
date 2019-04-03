#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Time:   2019/2/26 11:00
@Author: quanbin_zhu
@Email:  quanbin@parcelx.io
"""

import click


def print_help():
    ctx = click.get_current_context()
    click.echo(ctx.get_help())
    ctx.exit()


@click.group()
@click.option('--debug/--no-debug', default=False)
def common(ctx, debug):
    # ensure that ctx.obj exists and is a dict (in case `cli()` is called
    # by means other than the `if` block below
    ctx.ensure_object(dict)

    ctx.obj['DEBUG'] = debug

@click.group()
def cli1():
    pass

@click.group()
def cli2():
    pass

@cli1.command()
@click.option('--install-channel', '-j', "install_channel", is_flag=False, default=False, help='Number of greetings.')
@click.option('--organization', '-o', "organization",  default='')
def compose(install_channel, organization):
    """Command on cli1"""
    print(f"do {install_channel}")
    print(f"tow {organization}")
    print_help()


@cli2.command()
def cmd2():
    """Command on cli2"""


cli = click.CommandCollection(sources=[common, cli1, cli2])

if __name__ == '__main__':
    cli()
