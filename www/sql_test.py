#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import orm
from models import User, Blog, Comment

async def test(loop):
    await orm.create_pool(loop=loop, user='lee', password='lee', db='python_webapp')

    u = User(name='Test', email='test@example.com', password='1234567890', image='about:blank')

    await u.save()

    orm.__pool.close()
    await orm.__pool.wait_closed()
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test(loop))
    loop.close()