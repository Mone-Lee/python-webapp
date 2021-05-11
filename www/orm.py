#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import asyncio, logging

import aiomysql

def log(sql, args=()):
    logging.info('SQL: %s' % sql)

# 创建全局的连接池，存储在全局对象__pool中，复用数据库连接
async def create_pool(loop, **kw):
    logging.info('create database connection pool...')
    global __pool   # 初始化并设置__pool为全局变量
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
    async with __pool.get() as conn:
        if not autocommit:
            await conn.begin()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql.replace('?', '%s'), args)
                affected = cur.rowcount
            if not autocommit:
                await conn.commit()
        except BaseException as e:
            if not autocommit:
                await conn.rollback()
            raise
        return affected


# 在编写ORM之前，需要根据上层调用者（即最终最简洁的使用者）的角度设计, 类似于先编写一个实例，再根据实例抽象化一个类
# 例： 定义一个User对象，对应的是mysql中的一个表users，表中包含字段id和name
# from orm import Model, StringField, IntegerField

# # User类仅需定义属性和属性的类型，类的具体方法在Model中定义(inser、findAll等)
# class User(Model):

#     __table__ = 'users'     # 表名

#     id = IntegerField(primary_key=True)
#     name = StringField()

# # 创建实例
# user = User(id=123, name='Lee')
# # 存入数据库
# user.insert()
# # 查询所有User对象
# users = User.findAll()

# 定义Field，与各种子Field
class Field(object):
    
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default
    
    # 格式化， 打印实例时的字符串
    def __str__(self):
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)

class StringField(Field):
    
    def __init__(self, name=None, primary_key=False, default=None):
        super().__init__(name, 'varchar(100)', primary_key, default)

class BooleanField(Field):

    def __init__(self, name=None, default=False):
        super().__init__(name, 'Boolean', False, default)

class IntegerField(Field):

    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)

class FloatField(Field):

    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)

class TextField(Field):

    def __init__(Self, name=None, default=None):
        super().__init__(name, 'text', False, default)



# 创建一个包含num个?的字符串， num=3  返回"?,?,?"
def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
    return ', '.join(L)

# 定义metaClass, 将具体之类如User的映射信息读取出来， 即收集子类的数据信息，并抽象确实的操作Mysql语句的方法，把这些方法绑定到Model
# 元类metaClass用于创建类，控制类的创建行为
class ModelMetaclass(type):

    # 确定 __new__与__init__的区别:
    # __init__用于创建实例时的调用(例： user = User(id=123, name='Lee'))
    # __new__用于创建类时的调用(例：class User(Model):  或 class Model(dict, metaclass=ModelMetaclass) 继承时)
    # 参数：cls: 当前准备创建的类的对象   name: 类的名字   bases: 类继承的父类集合   attrs: 类的方法集合（attrs对象的属性会被绑定到类中，包括变量，方法）
    def __new__(cls, name, bases, attrs):
        # 排除Model类本身
        if name=='Model':
            return type.__new__(cls, name, bases, attrs)

        # 获取table名称
        tableName = attrs.get('__table__', None) or name
        logging.info('found model: %s (table: %s)' % (name, tableName))     # found model: User (table: users)

        # 获取所有的Field和主键名
        mappings = dict()
        fields = []
        primaryKey = None
        for k, v in attrs.items():
            if isinstance(v, Field):
                logging.info('found mappings: %s ==> %s' % (k, v))      # Found mapping: id ==> <IntegerField:id>    <IntegerField:id>包括IntegerField的属性 name, column_type, primary_key, default
                mappings[k] = v
                if v.primary_key:
                    # 找到主键
                    if primaryKey:
                        raise RuntimeError('Duplicate primary key for field: %s' % k)
                    primaryKey = k
                else:
                    fields.append(k)
        if not primaryKey:
            raise RuntimeError('Primary key not found.')
        
        # 把attrs原有的属性值都删除后，可以确保访问实例的属性时通过__getattr__
        # 在创建子类User时, 调用了metaClass的__new__方法, 此时把原有的attrs(id = IntegerField(primary_key=True)、name = StringField())存储到mappings中，然后清空相关属性
        # 之后到创建实例user时(user = User(id=123, name='Lee'))，需要调用__init__()方法， 由于User没有__init__方法，通过继承链，最后调用的是dict的__init__方法
        # 当传入参数(id=123, name='Lee')时, 使用__setattr__进行初始化，得到user['id']=123, user['name']='Lee'
        # 当我们需要访问实例的属性时，例如user.name, 查找顺序为: 实例属性(user.id) -> 类的属性(User类里的属性) ->  __getattr__方法,  由于初始化时__setattr__设置的是self[key]的格式，这不是user的实例属性，而User类的属性已经被attrs.pop(k)删除掉了，所以最后只能使用__getattr__方法的返回值，即'Lee'
        for k in mappings.keys():
            attrs.pop(k)
        
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))
        attrs['__mappings__'] = mappings    # 保存属性和列的映射关系
        attrs['__table__'] = tableName
        attrs['__primaty_key__'] = primaryKey  # 主键属性名
        
        # 构造默认的SELECT, INSERT, UPDATE和DELETE语句
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ','.join(escaped_fields), tableName)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ','.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName, ','.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)
        


# 定义Model
class Model(dict, metaclass=ModelMetaclass):

    # 类的初始化函数，当创建实例（user = User(id=123, name='Lee')）时调用，因为继承了dict，所以实际上调用的是dict的__init__方法
    def __init__(self, **kw):
        super().__init__(**kw)
    
    # 格式化， 当找不到对应的属性时，调用的方法
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)
    
    def __setattr__(self, key, value):
        self[key] = value
    
    def getValue(self, key):
        return getattr(self, key, None)     # getattr是python自省的核心函数，如果找到属性key，则返回对应的值，否则返回None（可设置）
    
    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]      # __mappings__是在元类ModelMetaclass中定义的，存储的是id = IntegerField(primary_key=True)等对应的类型值，其default值在对应的IntegerField中定义
            if field.default is not None:
                value = field.default if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' % (key, str(value)))
                setattr(self, key, value)
        return value

    # 添加class方法，使所有子类可以调用class方法， 返回的是0到多个实例  User.findAll()
    @classmethod
    async def findAll(cls, where=None, args=None, **kw):
        sql = [cls.__select__]
        # 如果where有值，就在sql加上字符串 'where' 和 变量where
        if where:
            sql.append('where')
            sql.append(where)
        # 如果findAll函数未传入有效的where参数，则将'[]'传入args
        if args is None:
            args = []
        
        # orderBy 有值时给 sql 加上它，为空值时什么也不干
        orderBy = kw.get('orderBy', None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)

        limit = kw.get('limit', None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit, int):
                # 如果 limit 为整数
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                # 如果 limit 是元组且里面只有两个元素
                sql.append('?, ?')
                # extend 把 limit 加到末尾
                args.extend(limit)
            else:
                # 不行就报错
                raise ValueError('Invalid limit value: %s' % str(limit))
        
        rs = await select(' '.join(sql), args)      # 调用上面的select函数
        return [cls(**r) for r in rs]

    @classmethod
    async def findNumber(cls, selectField, where=None, args=None):
        # 找到选中的数及其位置
        sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)
        rs = await select(' '.join(sql), args, 1)
        if len(rs) == 0:
            # 如果 rs 内无元素，返回 None ；有元素就返回某个数
            return None
        return rs[0]['_num_']
    
    @classmethod
    async def find(cls, pk):
        ## find object by primary key
        # 通过主键找对象
        rs = await select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
        if len(rs) == 0:
            return None
        return cls(**rs[0])
    

    # 给Model 类添加实例方法，使所有实例可以调用该方法  实例方法只影响调用的那个实例   user.save()
    async def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = await execute(self.__insert, args)
        if rows != 1:
            logging.warning('failed to insert record: affected rows: %s' % rows)

    async def update(self):
        args = list(map(self.getValue, self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = await execute(self.__update__, args)
        if rows != 1:
            logging.warning('failed to update by primary key: affected rows: %s' % rows)
    
    async def remove(self):
        args = [self.getValue(self.__primary_key__)]
        rows = await execute(self.__delete__, args)
        if rows != 1:
            logging.warning('failed to remove by primary key: affected rows: %s' % rows)