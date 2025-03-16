import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
import random
import json
import logging
import asyncio
from PIL import Image, ImageDraw, ImageFont
import io
import math
from datetime import datetime, time
import pytz
from keep_alive import keep_alive

keep_alive()

SAUDI_TZ = pytz.timezone("Asia/Riyadh")

CHANNEL_ID = 1350526969309036574

# إعداد تسجيل الأخطاء
logging.basicConfig(filename='error.log', level=logging.ERROR)

TOKEN = "MTM1MDQ5NDA3MzcxODMwODkyNg.GhbMn1.jXbfgJLmya_b_7EJ_3X9FOORYGdwxWP-2aTEQE"

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix="!", intents=intents)

players = {}
daily_activity = {}


def load_data():
    global players, daily_activity
    try:
        with open("players.json", "r", encoding="utf-8") as file:
            players = json.load(file)
    except FileNotFoundError:
        players = {}

    try:
        with open("daily_activity.json", "r", encoding="utf-8") as file:
            daily_activity = json.load(file)
    except FileNotFoundError:
        daily_activity = {}


def save_data():
    with open("players.json", "w", encoding="utf-8") as file:
        json.dump(players, file, ensure_ascii=False, indent=4)

    with open("daily_activity.json", "w", encoding="utf-8") as file:
        json.dump(daily_activity, file, ensure_ascii=False, indent=4)


async def is_admin(ctx):
    return ctx.author.guild_permissions.administrator


def create_roulette_image(participants, winner=None):
    size = 500
    img = Image.new("RGB", (size, size), "white")
    draw = ImageDraw.Draw(img)

    num_segments = len(participants)
    angle = 360 / num_segments
    colors = [
        "red", "blue", "green", "yellow", "purple", "orange", "cyan", "magenta"
    ]

    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()

    center = (size // 2, size // 2)
    radius = size // 2 - 10

    for i, name in enumerate(participants):
        start_angle = i * angle
        end_angle = (i + 1) * angle
        draw.pieslice([0, 0, size, size],
                      start=start_angle,
                      end=end_angle,
                      fill=colors[i % len(colors)])

        mid_angle = math.radians((start_angle + end_angle) / 2)
        text_x = center[0] + int(radius * 0.6 * math.cos(mid_angle))
        text_y = center[1] + int(radius * 0.6 * math.sin(mid_angle))
        draw.text((text_x, text_y), name, fill="black", font=font, anchor="mm")

    if winner:
        draw.text(center, f"🎯 {winner} 🎯", fill="gold", font=font, anchor="mm")

    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)
    return img_bytes


daily_message = None  # لتخزين الرسالة الثابتة

from discord.ext import tasks


@tasks.loop(hours=1)
async def auto_update():
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send("🔄 **يتم تحديث قائمة النشاط اليومي...**")

        # إنشاء Embed جديد لقائمة النشاط اليومي
        if not daily_activity:
            await channel.send("❌ لا يوجد نشاط يومي لعرضه.")
            return

        sorted_activity = sorted(daily_activity.items(),
                                 key=lambda x: x[1],
                                 reverse=True)
        embed = discord.Embed(
            title="🏆 النشاط اليومي",
            description="ترتيب الأشخاص حسب النقاط من اليوم السابق",
            color=discord.Color.green())
        embed.set_thumbnail(
            url="https://cdn-icons-png.flaticon.com/512/3135/3135715.png")
        medals = ["🥇", "🥈", "🥉"]

        for index, (name, points) in enumerate(sorted_activity):
            medal = medals[index] if index < len(medals) else "🔹"
            embed.add_field(name=f"{medal} {name}",
                            value=f"**النقاط:** `{points}`",
                            inline=False)

        embed.set_footer(
            text=
            f"🔄 يتم تحديث القائمة كل ساعة | عدد اللاعبين: {len(daily_activity)}"
        )

        await channel.send(embed=embed)
    else:
        print("❌ خطأ: القناة غير موجودة!")


@bot.event
async def on_ready():
    print(f"✅ {bot.user} جاهز!")
    reset_daily_activity.start(
    )  # تشغيل مهمة تصفير النشاط اليومي الساعة 4 فجراً
    bot.loop.create_task(
        update_daily_activity())  # تحديث النشاط اليومي كل ساعة


async def update_daily_activity():
    """ تحديث قائمة النشاط اليومي كل ساعة """
    global daily_message
    await bot.wait_until_ready()

    channel = bot.get_channel(CHANNEL_ID)

    if not channel:
        print("❌ لم يتم العثور على القناة!")
        return

    while True:
        if not daily_activity:
            content = "❌ لا يوجد نشاط يومي لعرضه."
            embed = None
        else:
            sorted_activity = sorted(daily_activity.items(),
                                     key=lambda x: x[1],
                                     reverse=True)
            embed = discord.Embed(
                title="🏆 النشاط اليومي",
                description="ترتيب الأشخاص حسب النقاط من اليوم السابق",
                color=discord.Color.green())
            embed.set_thumbnail(
                url="https://cdn-icons-png.flaticon.com/512/3135/3135715.png")
            medals = ["🥇", "🥈", "🥉"]

            for index, (name, points) in enumerate(sorted_activity):
                medal = medals[index] if index < len(medals) else "🔹"
                embed.add_field(name=f"{medal} {name}",
                                value=f"**النقاط:** `{points}`",
                                inline=False)

            embed.set_footer(
                text=
                f"🔄 يتم التحديث تلقائيًا كل ساعة | عدد اللاعبين: {len(daily_activity)}"
            )

        try:
            if daily_message and await channel.fetch_message(daily_message.id):
                await daily_message.edit(content=content, embed=embed)
            else:
                daily_message = await channel.send(content=content,
                                                   embed=embed)
        except discord.NotFound:
            daily_message = await channel.send(content=content, embed=embed)

        await asyncio.sleep(3600)  # تحديث كل ساعة


@tasks.loop(minutes=1)
async def reset_daily_activity():
    """ تصفير النشاط اليومي يوميًا عند الساعة 4 فجراً بتوقيت السعودية """
    now = datetime.now(SAUDI_TZ).time()
    reset_time = time(4, 0)  # 4:00 فجراً بتوقيت السعودية

    if now.hour == reset_time.hour and now.minute == reset_time.minute:
        global daily_activity
        daily_activity = {}  # تصفير قائمة النشاط اليومي
        print("🔄 تم تصفير قائمة النشاط اليومي في الساعة 4 فجراً!")


bot.command()


async def نقاط(ctx, name: str, points: int):
    """ إضافة نقاط للاعب في النشاط اليومي، ولكن فقط بين 11 صباحًا و3:59 فجرًا بتوقيت السعودية """
    now = datetime.now(SAUDI_TZ).time()

    # فترة جمع النقاط (11 صباحًا - 3:59 فجرًا)
    start_time = time(11, 0)  # 11:00 صباحًا
    end_time = time(3, 59)  # 3:59 فجرًا

    if start_time <= now or now <= end_time:  # التحقق إذا كان الوقت داخل النطاق
        if name in daily_activity:
            daily_activity[name] += points
        else:
            daily_activity[name] = points

        await ctx.send(f"✅ تم إضافة {points} نقاط إلى {name}!")
    else:
        await ctx.send(
            "🚫 لا يمكن إضافة النقاط الآن! التوقيت المسموح هو من 11 صباحًا إلى 3:59 فجرًا فقط."
        )


@bot.event
async def on_ready():
    print(f"✅ تم تسجيل الدخول باسم {bot.user}")

    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        print(
            "❌ خطأ: لم يتم العثور على القناة! تأكد أن المعرف صحيح وأن البوت لديه صلاحيات الوصول."
        )
    else:
        print(f"📢 سيتم إرسال النشاط اليومي في: {channel.name}")

    auto_update.start()


@bot.command()
async def النشاط_اليومي(ctx):
    await ctx.send(
        "🔄 يتم تحديث قائمة النشاط اليومي تلقائيًا كل ساعة في القناة المحددة!")


@bot.command()
async def add(ctx, name: str):
    if name not in players:
        await ctx.send(f"❌ الاسم **{name}** غير موجود. استخدم `!اضف {name}`.")
        return

    embed = discord.Embed(title=f"🏆 نقاط {name}",
                          description="اضغط على الإيموجي لإضافة أو خصم النقاط",
                          color=discord.Color.blue())
    embed.add_field(name="النقاط الحالية",
                    value=f"**{players[name]}**",
                    inline=False)

    message = await ctx.send(embed=embed)

    await message.add_reaction("1️⃣")  # إضافة 1 نقطة
    await message.add_reaction("2️⃣")  # إضافة 2 نقطة
    await message.add_reaction("3️⃣")  # إضافة 3 نقاط
    await message.add_reaction("🔢")  # إدخال عدد مخصص من النقاط للإضافة
    await message.add_reaction("🗑️")  # إدخال عدد مخصص من النقاط للخصم


@bot.command()
async def addname(ctx, name: str):
    if not await is_admin(ctx):
        await ctx.send("🚫 ليس لديك الصلاحية لاستخدام هذا الأمر.")
        return

    if name in players:
        await ctx.send(f"⚠️ الاسم **{name}** موجود بالفعل.")
        return

    players[name] = 0
    save_data()
    await ctx.send(f"✅ تمت إضافة الاسم **{name}**!")


@bot.command()
async def delname(ctx, name: str):
    if not await is_admin(ctx):
        await ctx.send("🚫 ليس لديك الصلاحية لاستخدام هذا الأمر.")
        return

    if name not in players:
        await ctx.send(f"❌ الاسم **{name}** غير موجود.")
        return

    del players[name]
    save_data()
    await ctx.send(f"🗑️ تم حذف الاسم **{name}**.")


@bot.command()
async def روليت(ctx):
    if not daily_activity:
        await ctx.send("❌ لا يوجد نشاط يومي لعمل روليت.")
        return

    spinning_message = await ctx.send("🎡 جاري تدوير العجلة...")
    participants = list(daily_activity.keys())

    for _ in range(10):
        random.shuffle(participants)
        img_bytes = create_roulette_image(participants)
        file = discord.File(img_bytes, filename="roulette.png")
        await spinning_message.edit(content="🎡 العجلة تدور...",
                                    attachments=[file])
        await asyncio.sleep(1)

    winner = random.choice(participants)
    img_bytes = create_roulette_image(participants, winner)
    file = discord.File(img_bytes, filename="winner.png")

    embed = discord.Embed(title="🎉 الفائز في الروليت! 🎉",
                          description=f"✨ الفائز هو: **{winner}**! ✨",
                          color=discord.Color.gold())
    embed.set_image(url="attachment://winner.png")

    await spinning_message.edit(content="", embed=embed, attachments=[file])


@bot.command()
async def leaderboard(ctx):
    if not await is_admin(ctx):
        await ctx.send("🚫 ليس لديك الصلاحية لاستخدام هذا الأمر.")
        return

    if not players:
        await ctx.send("❌ لا يوجد لاعبون في القائمة.")
        return

    sorted_players = sorted(players.items(), key=lambda x: x[1], reverse=True)

    embed = discord.Embed(title="🏆 قائمة المتصدرين",
                          description="ترتيب اللاعبين حسب النقاط",
                          color=discord.Color.gold())
    embed.set_thumbnail(
        url="https://cdn-icons-png.flaticon.com/512/3135/3135715.png")
    medals = ["🥇", "🥈", "🥉"]

    for index, (name, points) in enumerate(sorted_players):
        medal = medals[index] if index < len(medals) else "🔹"
        embed.add_field(name=f"{medal} {name}",
                        value=f"**النقاط:** `{points}`",
                        inline=False)

    embed.set_footer(
        text=f"🔄 استخدم 'ترتيب' لتحديث القائمة | عدد اللاعبين: {len(players)}")
    await ctx.send(embed=embed)


@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    message = reaction.message
    embed = message.embeds[0] if message.embeds else None

    if not embed:
        return

    name = embed.title.replace("🏆 نقاط ", "").strip()
    if name not in players:
        return

    if reaction.emoji in ["1️⃣", "2️⃣", "3️⃣"]:
        points = int(reaction.emoji[0])  # استخراج الرقم من الإيموجي مباشرة
        players[name] += points
        daily_activity[name] = daily_activity.get(name, 0) + points
        action = "إضافة"

    elif reaction.emoji == "🔢":
        await message.channel.send(
            f"✍️ {user.mention}، اكتب عدد النقاط التي تريد إضافتها لـ **{name}**."
        )

        def check(m):
            return m.author == user and m.channel == message.channel and m.content.isdigit(
            )

        try:
            msg = await bot.wait_for("message", check=check, timeout=30.0)
            points = int(msg.content)
            players[name] += points
            daily_activity[name] = daily_activity.get(name, 0) + points
            action = "إضافة"
        except asyncio.TimeoutError:
            await message.channel.send("⏳ انتهى الوقت، لم يتم إضافة نقاط.")
            return

    elif reaction.emoji == "🗑️":
        await message.channel.send(
            f"✍️ {user.mention}، اكتب عدد النقاط التي تريد خصمها من **{name}**."
        )

        def check(m):
            return m.author == user and m.channel == message.channel and m.content.isdigit(
            )

        try:
            msg = await bot.wait_for("message", check=check, timeout=30.0)
            points = int(msg.content)

            if players[name] < points:
                await message.channel.send(
                    f"⚠️ لا يمكن خصم {points} نقاط لأن رصيد {name} هو {players[name]} فقط!"
                )
                return

            players[name] -= points
            action = "خصم"
        except asyncio.TimeoutError:
            await message.channel.send("⏳ انتهى الوقت، لم يتم خصم النقاط.")
            return
    else:
        return

    save_data()

    await message.channel.send(
        f"✅ {user.mention} قام بـ **{action}** {points} نقاط لـ **{name}**! المجموع الآن: **{players[name]}** 🎉"
    )
    await message.clear_reactions()

    confirmation_embed = discord.Embed(
        title=f"✅ تم {action} النقاط بنجاح!",
        description=
        f"تم **{action}** **{points}** نقاط لـ **{name}**. المجموع الحالي: **{players[name]}**.",
        color=discord.Color.red()
        if action == "خصم" else discord.Color.green())
    confirmation_embed.set_footer(text="🎉 شكراً لمساهمتك!")
    await message.channel.send(embed=confirmation_embed)


load_data()


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.strip().lower()
    ctx = await bot.get_context(message)

    if content.startswith("اضافة "):
        if not await is_admin(ctx):
            await ctx.send("🚫 ليس لديك الصلاحية لاستخدام هذا الأمر.")
            return
        name = content.replace("اضافة ", "").strip()
        await add(ctx, name)

    elif content.startswith("اضف "):
        if not await is_admin(ctx):
            await ctx.send("🚫 ليس لديك الصلاحية لاستخدام هذا الأمر.")
            return
        name = content.replace("اضف ", "").strip()
        await addname(ctx, name)

    elif content.startswith("حذف "):
        if not await is_admin(ctx):
            await ctx.send("🚫 ليس لديك الصلاحية لاستخدام هذا الأمر.")
            return
        name = content.replace("حذف ", "").strip()
        await delname(ctx, name)

    elif content == "ترتيب":
        if not await is_admin(ctx):
            await ctx.send("🚫 ليس لديك الصلاحية لاستخدام هذا الأمر.")
            return
        await leaderboard(ctx)

    elif content == "نقاط":
        if not await is_admin(ctx):
            await ctx.send("🚫 ليس لديك الصلاحية لاستخدام هذا الأمر.")
            return
        await النشاط_اليومي(ctx)

    await bot.process_commands(message)


app = Flask(__name__)


@app.route('/')
def home():
    return "Bot is running!"


def run():
    app.run(host="0.0.0.0", port=8080)


Thread(target=run).start()

load_data()

try:
    bot.run(TOKEN)
except Exception as e:
    logging.error(f"Error starting bot: {e}")
    print(f"Error starting bot: {e}")


from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()
