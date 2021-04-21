#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import asyncio, logging

import aiomysql

def log(sql, args=()):
    logging.info('SQL: %s' % sql)

# 创建全局的连接池，存储在全局对象__pool中，复用数据库连接
async def create_pool(loop, **kw):
    logging.info('create database connection pool...')
    global __pool
    __pool = await aiomysql.create_pool(
        host=kw.get('host', 'localhost'),  # 'localhost'为 host没有传值时的默认值
        port=kw.get('port', 3306),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw.get('charset', 'utf-8'),
        autocommit=kw.get('autocommit', True),  # 自动提交事务
        maxsize=kw.get('maxsize', 10),
        minisize=kw.get('minisize', 1),
        loop=loop
    )


# select函数
async def select(sql, args, size=None):
    log(sql, args)
    global __pool
    async with __pool.get() as conn:    # 获取数据库连接
        async with conn.cursor(aiomysql.DictCursor) as cur:     # 创建游标cursor,通过游标执行sql语句;  使用aiomysql.DictCursor标记cursor, 则查找的返回结果为list包裹的dict, 否则默认为tuple包裹的tuple
            await cur.execute(sql.replace('?', '%s'), args or ())       # mysql的占位符是 %s
            if size:
                rs = await cur.fetchmany(size)      # 获取指定数量的记录
            else:
                rs = await cur.fetchall()
        logging.info('rows returned: %s' % len(rs))
        return rs

# INSERT、UPDATE、DELETE接受同样的参数，都返回影响的行数，所以定义一个通用的execute函数
async def execute(sql, args, autocommit=True):
    log(sql)
    global __pool
    async with __pool.get() as conn:
        if not autocommit:
            await conn.begin()      # 开始事务
        try:
            await with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql,.replace('?', '%s'), args)
                affected = cur.rowcount
            if not autocommit:
                await conn.commit()
        execpt BaseExecption as e:
            if not autocommit:
                await conn.rollback()
            raise
        return affected
            