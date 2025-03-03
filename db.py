import psycopg
from config_reader import config


async def get_connection():
    return await psycopg.AsyncConnection.connect(config.pg_link.get_secret_value())


async def register_user(tg_id: str, name: str, photo: str) -> None:
    async with await get_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                'INSERT INTO users (tg_id, name, photo) VALUES (%s, %s, %s)',
                (tg_id, name, photo))
            await conn.commit()


async def get_data() -> list:
    async with await get_connection() as conn:  
        async with conn.cursor() as cursor:  
            await cursor.execute('SELECT * FROM users')
            data = await cursor.fetchall()
            await conn.commit()  
    return data

async def get_tg_ids() -> list:
    async with await get_connection() as conn:
        async with conn.cursor() as cursor:  
            await cursor.execute('SELECT tg_id FROM users')
            data = await cursor.fetchall()
            await conn.commit()  
    return data


async def get_user_ids() -> list:
    async with await get_connection() as conn:
        async with conn.cursor() as cursor:  
            await cursor.execute('SELECT user_id FROM users')
            data = await cursor.fetchall()
            await conn.commit()  
    return data


async def get_user(tg_id: str) -> tuple:
    async with await get_connection() as conn:
        async with conn.cursor() as cursor:  
            await cursor.execute('SELECT * FROM users WHERE tg_id=%s', (tg_id,))
            data = await cursor.fetchall()
            await conn.commit()  
    return None if len(data) == 0 else data[0]


async def delete_user(tg_id : str) -> None:
    async with await get_connection() as conn: 
        async with conn.cursor() as cursor:
            await cursor.execute(
                'DELETE FROM users WHERE tg_id=%s', (tg_id,))
            await conn.commit()


async def is_admin(tg_id: str):
    async with await get_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute('SELECT admin FROM users WHERE tg_id=%s', (tg_id,))
            data = await cursor.fetchall()
            await conn.commit()
    return True if data[0][0] else False


async def make_admin(tg_id: str):
    async with await get_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute('UPDATE users SET admin=%s WHERE tg_id=%s', (True, tg_id))
            await conn.commit()

