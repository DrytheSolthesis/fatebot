import discord
import asyncio
import re
import time
import random
import redis


client = discord.Client()
chain_length = 2
max_words = 30
messages_to_generate = 20
separator = '\x01'
stop_word = '\x02'
redis_conn = redis.Redis()
prefix = 'discord'
messages = []

    
def make_key(k):
    return '-'.join((prefix, k))
    
def sanitize_message(message):
    return re.sub('[\"\']', '', message.lower())

def split_message(message):
    words = message.split()
    if len(words) > chain_length:
        words.append(stop_word)
        for i in range(len(words) - chain_length):
            yield words[i:i + chain_length + 1]
    
def generate_message(seed):
    key = seed
    gen_words = []
    for i in range(max_words):
        words = key.split(separator)
        gen_words.append(words[0])
        next_word = redis_conn.srandmember(make_key(key))
        if not next_word:
            break
        key = separator.join(words[1:] + [next_word.decode("utf=8")])
    return ' '.join(gen_words)

@client.event
@asyncio.coroutine
def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

@client.event
@asyncio.coroutine
def on_message(incoming_mes):
    if (incoming_mes.author.id != "169962512194732034" and incoming_mes.channel.id not in ["219895037608198144", "199287746743894016", "162643560582086657"]):
        for words in split_message(sanitize_message(incoming_mes.content)):
            key = separator.join(words[:-1])
            redis_conn.sadd(make_key(key), words[-1])
            best_message = ''
            for i in range(messages_to_generate):
                generated = generate_message(seed=key)
                if len(generated) > len(best_message):
                    best_message = generated            
            if best_message:
                messages.append(best_message)      
        if len(messages):
            if (random.randint(1,40) == 32):
                yield from client.send_message(incoming_mes.channel, random.choice(messages))
            
    if (incoming_mes.content.startswith("RIP")):
        yield from client.send_message(incoming_mes.channel, 'Ya, RIP')

    if (incoming_mes.content.startswith(":")):
        if (incoming_mes.content.endswith(":")):
            yield from client.send_file(incoming_mes.channel, "saemotes/" + incoming_mes.content, filename = "emote.png") 
            
    if (incoming_mes.author.id != "169962512194732034" and incoming_mes.channel.id == "162770083993616385" and random.randint(1,2) == 2):
        for words in split_message(sanitize_message(incoming_mes.content)):
            key = separator.join(words[:-1])
            redis_conn.sadd(make_key(key), words[-1])
            best_message = ''
            for i in range(messages_to_generate):
                generated = generate_message(seed=key)
                if len(generated) > len(best_message):
                    best_message = generated            
            if best_message:
                messages.append(best_message)      
        if len(messages):
            yield from client.send_message(incoming_mes.channel, random.choice(messages))
            
                                           
client.run('MTY5OTYyNTEyMTk0NzMyMDM0.CgPsHA.bM5Nw9fyj0YrvsVMEKAZLFSsC84')