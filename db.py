import psycopg
import random
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
            
async def set_victim(id_current, id_victim: int):
    async with await get_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute('UPDATE users SET victim=%d WHERE user_id=%d', (id_victim, id_current))
            await conn.commit()


async def shuffle_players():
    all_users = await get_data()
    players = [i for i in all_users if not i[-1] ]
    if len(players) < 2:
        return []
    random.shuffle(players)
    for i in range(1, len(players)):
        await set_victim(players[i-1], players[i])
    await set_victim(players[-1], players[0])
    

