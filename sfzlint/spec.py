# -*- coding: utf-8 -*-

import yaml
from pathlib import Path
from collections import ChainMap
from numbers import Real  # int or float
from .validators import Any, Min, Range, Choice, Alias, VersionValidator


ver_mapping = {
    'SFZ v1': 'v1',
    'SFZ v2': 'v2',
    'ARIA': 'aria',
    'LinuxSampler': 'linuxsampler',
    'Cakewalk': 'cakewalk',
    'Cakewalk SFZ v2': 'v2',  # good enough? anyone use cakewalk as a target?
}


version_hierarchy = {
    'v1': {'v1'},
    'v2': {'v1', 'v2'},
    'aria': {'v1', 'v2', 'aria'},
    'linuxsampler': {'v1', 'v2', 'linuxsampler'},
    'cakewalk': {'v1', 'cakewalk'},  # is this correct?
}


type_mapping = {
    'integer': int,
    'float': Real,
    'string': str,
}


overrides = {
    'tune':
        {'ver': 'v1', 'type': int,
         'validator': VersionValidator(
             default=Range(-100, 100),
             aria=Range(-2400, 2400))},
    'type':
        {'ver': 'aria', 'type': str, 'header': 'effect',
         'validator': Any()},
}


def _import(cache=[]):
    if not cache:
        with (Path(__file__).parent / 'syntax.yml').open() as syn_yml:
            syntax = yaml.load(syn_yml, Loader=yaml.SafeLoader)
        cache.append(syntax)
    return cache[-1]


def _extract():
    syn = _import()
    cat = syn['categories']
    ops = {o['name']: o for o in _extract_op(cat)}
    return ops


def opcodes(key=None, cache=[]):
    if not cache:
        ops = _extract()
        cache.append(ChainMap(overrides, ops))
    return cache[-1]


def _extract_op(categories):
    for category in categories:
        op = category.get('opcodes')
        if op:
            yield from _iter_ops(op)
        types = category.get('types')
        if types:
            yield from _extract_op(types)


def _iter_ops(opcodes):
    for opcode in opcodes:
        yield from op_to_validator(opcode)


def op_to_validator(op_data, **kwargs):
    valid_meta = dict(
        name=op_data['name'],
        ver=ver_mapping[op_data['version']],
        **kwargs)
    vv = op_data.get('value')
    if vv:
        if 'type_name' in vv:
            valid_meta['type'] = type_mapping[vv['type_name']]
        if 'min' in vv:
            if not isinstance(vv['min'], Real):
                raise TypeError(f'{op_data["name"]} bad value: {vv}')
            if 'max' in vv:
                if not isinstance(vv['max'], Real):
                    # bad value, eg "SampleRate / 2"
                    valid_meta['validator'] = Min(vv['min'])
                else:
                    valid_meta['validator'] = Range(vv['min'], vv['max'])
            else:
                valid_meta['validator'] = Min(vv['min'])
        elif 'options' in vv:
            valid_meta['validator'] = Choice([o['name'] for o in vv['options']])
        else:
            valid_meta['validator'] = Any()
    else:
        valid_meta['validator'] = Any()
    yield valid_meta
    for alias in op_data.get('alias', []):
        alias_meta = {
            'ver': ver_mapping[alias['version']],
            'validator': Alias(op_data['name']),
            'name': alias['name']}
        yield alias_meta
    if 'modulation' in op_data:
        for mod_type, modulations in op_data['modulation'].items():
            if isinstance(modulations, list):  # some are just checkmarks
                for mod in modulations:
                    yield from op_to_validator(
                        mod, modulates=op_data['name'], mod_type=mod_type)


def print_codes(printer=print):
    syn = _import()
    cat = syn['categories']
    for o in _extract_op(cat):
        printer(', '.join(f'{k}={v}' for k, v in sorted(o.items())))
