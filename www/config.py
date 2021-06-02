#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import config_default

configs = config_default.configs

class Dict(dict):
    '''
    使配置支持使用.访问属性，例: x.y
    '''
    def __init__(self, names=(), values=(), **kw):
        super().__init__(**kw)
        # zip()生成一个数组list，每一项是一个tuple, tuple中是zip每一项参数对应的第i项, list长度为zip参数的最短一项的长度
        # 例： zip('abcd', [1, 2])  => [('a', 1), ('b', 2)]
        for k, v in zip(names, values):
            self[k] = v
    
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '%s'" % key)
    
    def __setattr__(self, key, value):
        self[key] = value

def toDict(d):
    D = Dict()
    for k, v in d.items():
        D[k] = toDict(v) if isinstance(v, dict) else v
    return D

def merge(default, override):
    r = {}
    for k, v in default.items():
        if k in override:
            if isinstance(v, dict):
                r[k] = merge(v, override[k])
            else:
                r[k] = override[k]
        else:
            r[k] = v
    return r

try:
    import config_override
    configs = merge(configs, config_override.configs)
except ImportError:
    pass

configs = toDict(configs)