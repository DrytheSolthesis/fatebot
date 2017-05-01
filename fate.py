import discord
import asyncio
from funcs import *

messages = []
simming = None
client = discord.Client()
messages_to_generate = 20


def sim_char(incoming_data):
    global simming
    print("RUNNING SIM")
    character = ','.join(incoming_data.split('-')[::-1])
    command = '/home/autumn/simcraft/simc/engine/simc'
    arg1 = 'armory=us,' + character
    arg2 = 'settings.simc'
    arg3 = 'html=/home/www/simc.aki.fyi/' + incoming_data + '.html'
    try:
        fd = open(arg3[5:], "w")
        fd.write("<h3>SIM IN PROGRESS</h3>")
        fd.close()
    except OSError:
        pass
    print(command, arg1, arg2, arg3)
    call([command, arg1, arg2, arg3])
    print("DONE")
    simming = None


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
    global simming
    incoming_mes.content = profanity_filter(incoming_mes.content)
    if (incoming_mes.author.id != "169962512194732034" and
            incoming_mes.channel.id not in [
                "219895037608198144", "199287746743894016",
                "162643560582086657", "163536032002736128"
            ]):
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
            if (random.randint(1, 80) == 32):
                yield from client.send_message(incoming_mes.channel,
                                               random.choice(messages))
            if (random.randint(1, 100) == 42):
                yield from client.send_message(incoming_mes.channel,
                                               ':thinking:')

    if (incoming_mes.content.startswith("RIP")):
        yield from client.send_message(incoming_mes.channel, 'Ya, RIP')

    if (incoming_mes.content.startswith("~logs")):
        em = discord.Embed(
            title="CogDis\'s WCL Calendar",
            url="https://www.warcraftlogs.com/guilds/17287",
            colour=0xDEADBF)
        yield from client.send_message(incoming_mes.channel, embed=em)

    if (incoming_mes.content.startswith("~pug")):
        target_region = default_region
        try:
            i = str(incoming_mes.content[5:]).split('-', 1)
            print(i)
            name = i[0]
            if (len(i) > 1): server = i[1]
            if (len(i) == 1): server = "sargeras"
            character_info = get_char(name, server, target_region)
            em = discord.Embed(
                title="", description=character_info, colour=0xDEADBF)
            yield from client.send_message(incoming_mes.channel, embed=em)
        except Exception as e:
            yield from client.send_message(
                incoming_mes.channel, e +
                "\nError With Name or Server\nUse: ~pug <name> <server>\nHyphenate Two Word Servers (Ex: Twisting-Nether)"
            )

    if (incoming_mes.content.startswith("~simc")):
        if simming:
            yield from client.send_message(
                incoming_mes.channel,
                'A sim is currently running, please wait.')
        if not simming:
            characterinc = incoming_mes.content[6:]
            if '-' not in characterinc: characterinc += "-sargeras"
            em = discord.Embed(
                title="Running Sim for " + characterinc,
                url='https://simc.aki.fyi/' + characterinc + '.html',
                description='Your sim will show up at the link above when it completes shortly.',
                colour=0xDEADBF)
            yield from client.send_message(incoming_mes.channel, embed=em)
            simming = True
            incoming_data = characterinc
            thread = threading.Thread(target=sim_char, args=(incoming_data, ))
            thread.start()
    
    if (incoming_mes.content.lower() == ":kassia:"):
        reply = random_emoji(6) + random_emoji(6) + "Kassia" + random_emoji(6) + random_emoji(6)
        yield from client.send_message(incoming_mes.channel, reply)


    if (incoming_mes.content.startswith(":")):
        if (incoming_mes.content.endswith(":")):
            yield from client.send_file(
                incoming_mes.channel,
                "saemotes/" + incoming_mes.content,
                filename="emote" +
                (".gif" if (incoming_mes.content == ":bookie:") else ".png"))



    adjectives = ["bad", "shit", "worst", "horrible"]
    nouns = ["leggo", "legendary", "leggos", "legendaries"]
    if any(x in incoming_mes.content for x in adjectives):
        if any(x in incoming_mes.content for x in nouns):
            yield from client.send_message(incoming_mes.channel, ':thinking:')

    if (incoming_mes.content.lower() == "mother of god"):
        yield from client.send_file(
            incoming_mes.channel,
            "motherofgod.gif",
            filename="motherofgod.gif")

    if (incoming_mes.author.id != "169962512194732034" and
            incoming_mes.channel.id == "162770083993616385" and
            random.randint(1, 2) == 2):
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
            yield from client.send_message(incoming_mes.channel,
                                           random.choice(messages))


client.run('MTY5OTYyNTEyMTk0NzMyMDM0.CgPsHA.bM5Nw9fyj0YrvsVMEKAZLFSsC84')
