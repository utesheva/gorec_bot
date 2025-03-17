import psycopg
import random
from config_reader import config


new_point_system = False    #когда со множителями работаем

async def get_connection():
    return await psycopg.AsyncConnection.connect(config.pg_link.get_secret_value())


async def register_user(tg_id: str, name: str, photo: str) -> None:
    async with await get_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                'INSERT INTO users (tg_id, name, photo) VALUES (%s, %s, %s)',
                (tg_id, name, photo))
            await conn.commit()
    await add_to_daily_db(tg_id)
    
async def add_to_daily_db(tg_id: str):
    user = await get_user(tg_id)
    async with await get_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                'INSERT INTO daily (id, score) VALUES (%s, %s)',
                (user[0], 0))
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
            await cursor.execute('UPDATE users SET victim=%s WHERE user_id=%s', (id_victim, id_current))
            await conn.commit()


async def shuffle_players():
    players = await get_data()
    if len(players) < 2:
        return []
    random.shuffle(players)
    await make_alive(players[0][4])
    for i in range(1, len(players)):
        await set_victim(players[i-1][0], players[i][0])
        await make_alive(players[i][4])
    await set_victim(players[-1][0], players[0][0])
    
    
async def get_rating():
    async with await get_connection() as conn:
        async with conn.cursor() as cursor:  
            await cursor.execute('SELECT * FROM daily ORDER BY score DESC')
            data = await cursor.fetchall()
            await conn.commit()  
    return data 

async def add_point(id: str):
    rating = await get_rating()
    place, multiplier, prev_score = 0, 1, 0
    for i in range(len(rating)):
        if rating[i][0] == id:
            prev_score = rating[i][1]
            place = i+1
    if place <= len(rating)/3:
        multiplier = 0.5
    elif place > 2*len(rating)/3:
        multiplier = 1.5
    async with await get_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute('UPDATE daily SET score=%s WHERE id=%s', (prev_score+multiplier, id))
            await conn.commit()

async def is_dead(tg_id: str):
    async with await get_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute('SELECT dead FROM users WHERE tg_id=%s', (tg_id,))
            data = await cursor.fetchall()
            await conn.commit()
    return True if data[0][0] else False

async def make_dead(tg_id: str):
    async with await get_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute('UPDATE users SET dead=%s WHERE tg_id=%s', (True, tg_id))
            await conn.commit()

async def make_alive(tg_id: str):
    async with await get_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute('UPDATE users SET dead=%s WHERE tg_id=%s', (False, tg_id))
            await conn.commit()

async def get_alive():
    async with await get_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute('SELECT * FROM users WHERE dead=%s', (False,))
            data = await cursor.fetchall()
            await conn.commit()
    return data


async def get_victim(tg_id: str):
    async with await get_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute('SELECT victim FROM users WHERE tg_id=%s', (tg_id,))
            data = await cursor.fetchall()
            await conn.commit()
    return None if len(data) == 0 else data[0][0]


async def get_killer(tg_id: str):
    async with await get_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute('SELECT tg_id FROM users WHERE victim=%s', (tg_id,))
            data = await cursor.fetchall()
            await conn.commit()    
    return None if len(data) == 0 else data[0][0]

