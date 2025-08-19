import discord
from discord import app_commands
from discord.ext import commands
import random
from datetime import datetime, timedelta
from typing import Literal

from database.economy.functions import Database
from database.economy.connection import create_tables
from database.economy.models import User

# --- НАСТРОЙКИ ---
LOG_CHANNEL_ID = 1407290317069357057
ADMIN_ROLE_ID = 1399711308676595785
BANK_FEE = 0.02
BUSINESS_SELL_PERCENTAGE = 0.75
STARTING_BALANCE = 500

DAILY_REWARD_NAME = "Дар иллюминатов"

# --- ПЕРЕМЕННЫЕ КУЛДАУНОВ ---
DAILY_COOLDOWN = timedelta(hours=24)
WORK_COOLDOWN = timedelta(hours=3)
STEAL_COOLDOWN = timedelta(hours=6)
COLLECT_COOLDOWN = timedelta(hours=3)


class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = Database()
        self.log_channel = None

    async def cog_load(self):
        await create_tables()
        self.log_channel = self.bot.get_channel(LOG_CHANNEL_ID)

    async def send_log(self, embed: discord.Embed):
        if self.log_channel:
            await self.log_channel.send(embed=embed)

    @app_commands.command(name="баланс", description="💎 Показывает ваш текущий баланс.")
    @app_commands.describe(user="Пользователь, чей баланс вы хотите посмотреть (необязательно)")
    async def balance(self, inter: discord.Interaction, user: discord.Member = None):
        target_user = user or inter.user
        db_user = await self.db.get_user(target_user.id)
        if not db_user:
            db_user = User(user_id=target_user.id, cash=STARTING_BALANCE, bank=0)
        embed = discord.Embed(title=f"💰 Баланс {target_user.display_name}", color=discord.Color.gold())
        embed.set_thumbnail(url=target_user.display_avatar.url)
        embed.add_field(name="💵 Наличные", value=f"`{db_user.cash:,}` 🪙", inline=True)
        embed.add_field(name="🏦 В банке", value=f"`{db_user.bank:,}` 🪙", inline=True)
        embed.add_field(name="📊 Всего", value=f"`{db_user.total:,}` 🪙", inline=False)
        await inter.response.send_message(embed=embed)

    @app_commands.command(name="топ", description="🏆 Показывает топ-10 самых богатых пользователей.")
    async def top(self, inter: discord.Interaction):
        top_users_db = await self.db.get_top_users(10)
        embed = discord.Embed(title="👑 Зал славы богачей", description="Топ-10 пользователей сервера по общему балансу.", color=discord.Color.blurple())
        description = [f"`{i + 1}.` **{(self.bot.get_user(user_db.user_id) or f'ID: {user_db.user_id}').display_name}** — `{user_db.total:,}` 🪙" for i, user_db in enumerate(top_users_db)]
        embed.description = "\n".join(description) if description else "Пока что здесь пусто..."
        await inter.response.send_message(embed=embed)

    @app_commands.command(name="ежедневка", description=f"🎁 Получить ежедневный {DAILY_REWARD_NAME}.")
    async def daily(self, inter: discord.Interaction):
        user = await self.db.get_user(inter.user.id)
        now = datetime.utcnow()
        if user and user.last_daily and now - user.last_daily < DAILY_COOLDOWN:
            remaining = (user.last_daily + DAILY_COOLDOWN) - now
            return await inter.response.send_message(f"⏳ {DAILY_REWARD_NAME} будет доступен через: {str(remaining).split('.')[0]}.", ephemeral=True)

        reward = random.randint(1500, 3000)
        await self.db.update_balance(inter.user.id, cash_delta=reward)
        await self.db.update_cooldown(inter.user.id, 'last_daily')
        embed = discord.Embed(title=f"✨ {DAILY_REWARD_NAME}", description=f"Вы получили свой ежедневный дар в размере **{reward:,}** 🪙!", color=discord.Color.green())
        await inter.response.send_message(embed=embed)
        log_embed = discord.Embed(title="📝 Лог: Ежедневная награда", color=discord.Color.blue())
        log_embed.add_field(name="Пользователь", value=inter.user.mention, inline=False)
        log_embed.add_field(name="Сумма", value=f"`{reward:,}` 🪙", inline=False)
        await self.send_log(log_embed)

    @app_commands.command(name="работа", description="🛠️ Поработать и получить немного монет.")
    async def work(self, inter: discord.Interaction):
        user = await self.db.get_user(inter.user.id)
        now = datetime.utcnow()
        if user and user.last_work and now - user.last_work < WORK_COOLDOWN:
            remaining = (user.last_work + WORK_COOLDOWN) - now
            return await inter.response.send_message(f"⏳ Вы сможете снова работать через: {str(remaining).split('.')[0]}.", ephemeral=True)

        earnings = random.randint(300, 800)
        await self.db.update_balance(inter.user.id, cash_delta=earnings)
        await self.db.update_cooldown(inter.user.id, 'last_work')
        embed = discord.Embed(title="💪 Тяжкий труд", description=f"Вы усердно поработали и заработали **{earnings:,}** 🪙!", color=discord.Color.green())
        await inter.response.send_message(embed=embed)
        log_embed = discord.Embed(title="📝 Лог: Работа", color=discord.Color.blue())
        log_embed.add_field(name="Пользователь", value=inter.user.mention, inline=False)
        log_embed.add_field(name="Заработок", value=f"`{earnings:,}` 🪙", inline=False)
        await self.send_log(log_embed)

    @app_commands.command(name="украсть", description="🎭 Попытаться украсть монеты у другого пользователя.")
    @app_commands.describe(жертва="Пользователь, которого вы хотите ограбить.")
    async def steal(self, inter: discord.Interaction, жертва: discord.Member):
        user = await self.db.get_user(inter.user.id)
        now = datetime.utcnow()
        if user and user.last_steal and now - user.last_steal < STEAL_COOLDOWN:
            remaining = (user.last_steal + STEAL_COOLDOWN) - now
            return await inter.response.send_message(f"⏳ Вы сможете снова воровать через: {str(remaining).split('.')[0]}.", ephemeral=True)

        if жертва.id == inter.user.id:
            return await inter.response.send_message("Вы не можете ограбить самого себя!", ephemeral=True)
        if жертва.bot:
            return await inter.response.send_message("Боты - несокрушимые создания, их не ограбить.", ephemeral=True)

        victim_db = await self.db.get_user(жертва.id)
        if not victim_db or victim_db.cash < 100:
            return await inter.response.send_message(f"У {жертва.display_name} почти нет наличных, красть нечего.", ephemeral=True)

        await self.db.update_cooldown(inter.user.id, 'last_steal')
        success_chance = random.randint(10, 15)
        if random.randint(1, 100) <= success_chance:
            stolen_amount = int(victim_db.cash * 0.20)
            await self.db.update_balance(inter.user.id, cash_delta=stolen_amount)
            await self.db.update_balance(жертва.id, cash_delta=-stolen_amount)
            embed = discord.Embed(title="✅ Удачное ограбление", description=f"Вам удалось незаметно вытащить **{stolen_amount:,}** 🪙 из карманов {жертва.mention}!", color=discord.Color.green())
            await inter.response.send_message(embed=embed)
            log_embed = discord.Embed(title="📝 Лог: Ограбление (Успех)", color=0xf2ac52)
            log_embed.add_field(name="Вор", value=inter.user.mention).add_field(name="Жертва", value=жертва.mention).add_field(name="Украдено", value=f"`{stolen_amount:,}` 🪙")
            await self.send_log(log_embed)
        else:
            embed = discord.Embed(title="❌ Провал", description=f"{жертва.mention} заметил(а) вас! Вам пришлось спешно ретироваться с пустыми руками.", color=discord.Color.red())
            await inter.response.send_message(embed=embed)
            log_embed = discord.Embed(title="📝 Лог: Ограбление (Провал)", color=0x5c5c5c)
            log_embed.add_field(name="Вор", value=inter.user.mention).add_field(name="Жертва", value=жертва.mention)
            await self.send_log(log_embed)

    @app_commands.command(name="собрать_прибыль", description="💼 Собрать доход со всех ваших бизнесов.")
    async def collect_income(self, inter: discord.Interaction):
        user = await self.db.get_user(inter.user.id)
        now = datetime.utcnow()
        if user and user.last_collect and now - user.last_collect < COLLECT_COOLDOWN:
            remaining = (user.last_collect + COLLECT_COOLDOWN) - now
            return await inter.response.send_message(f"⏳ Вы сможете собрать прибыль снова через: {str(remaining).split('.')[0]}.", ephemeral=True)

        user_businesses = await self.db.get_user_businesses(inter.user.id)
        if not user_businesses:
            return await inter.response.send_message("У вас нет бизнесов для сбора прибыли.", ephemeral=True)

        total_income = sum(ub.business_info.income for ub in user_businesses)
        await self.db.update_balance(inter.user.id, cash_delta=total_income)
        await self.db.update_cooldown(inter.user.id, 'last_collect')
        embed = discord.Embed(title="🤑 Прибыль собрана!", description=f"Ваши бизнесы принесли вам доход в размере **{total_income:,}** 🪙.", color=discord.Color.green())
        await inter.response.send_message(embed=embed)
        log_embed = discord.Embed(title="📝 Лог: Сбор прибыли", color=0x9b59b6)
        log_embed.add_field(name="Пользователь", value=inter.user.mention).add_field(name="Прибыль", value=f"`{total_income:,}` 🪙")
        await self.send_log(log_embed)

    @app_commands.command(name="перевести", description="💸 Перевести деньги другому пользователю.")
    @app_commands.describe(получатель="Пользователь, которому вы переводите деньги.", сумма="Сумма перевода.")
    async def pay(self, inter: discord.Interaction, получатель: discord.Member, сумма: app_commands.Range[int, 1]):
        if получатель.id == inter.user.id or получатель.bot:
            return await inter.response.send_message("Неверная цель для перевода.", ephemeral=True)
        sender_db = await self.db.get_user(inter.user.id)
        if not sender_db or sender_db.cash < сумма:
            return await inter.response.send_message("У вас недостаточно наличных для такого перевода.", ephemeral=True)
        await self.db.update_balance(inter.user.id, cash_delta=-сумма)
        await self.db.update_balance(получатель.id, cash_delta=сумма)
        embed = discord.Embed(title="✅ Перевод выполнен", description=f"Вы успешно перевели **{сумма:,}** 🪙 пользователю {получатель.mention}.", color=discord.Color.green())
        await inter.response.send_message(embed=embed)
        log_embed = discord.Embed(title="📝 Лог: Перевод", color=discord.Color.light_grey())
        log_embed.add_field(name="Отправитель", value=inter.user.mention).add_field(name="Получатель", value=получатель.mention).add_field(name="Сумма", value=f"`{сумма:,}` 🪙")
        await self.send_log(log_embed)

    @app_commands.command(name="положить", description="📥 Положить деньги в банк (комиссия 2%).")
    @app_commands.describe(сумма="Сумма для внесения. Введите 'все' чтобы положить всё.")
    async def deposit(self, inter: discord.Interaction, сумма: str):
        user_db = await self.db.get_user(inter.user.id)
        user_cash = user_db.cash if user_db else 0
        try: amount = int(сумма) if сумма.lower() != 'все' else user_cash
        except ValueError: return await inter.response.send_message("Пожалуйста, введите число или слово 'все'.", ephemeral=True)
        if amount <= 0: return await inter.response.send_message("Сумма должна быть положительной.", ephemeral=True)
        if user_cash < amount: return await inter.response.send_message("У вас недостаточно наличных.", ephemeral=True)
        fee = int(amount * BANK_FEE)
        final_amount = amount - fee
        await self.db.update_balance(inter.user.id, cash_delta=-amount, bank_delta=final_amount)
        embed = discord.Embed(title="🏦 Банковская операция", description=f"Вы положили на счет **{final_amount:,}** 🪙.\nКомиссия составила: `{fee:,}` 🪙.", color=discord.Color.blue())
        await inter.response.send_message(embed=embed)

    @app_commands.command(name="снять", description="📤 Снять деньги с банковского счета (комиссия 2%).")
    @app_commands.describe(сумма="Сумма для снятия. Введите 'все' чтобы снять всё.")
    async def withdraw(self, inter: discord.Interaction, сумма: str):
        user_db = await self.db.get_user(inter.user.id)
        user_bank = user_db.bank if user_db else 0
        try: amount = int(сумма) if сумма.lower() != 'все' else user_bank
        except ValueError: return await inter.response.send_message("Пожалуйста, введите число или слово 'все'.", ephemeral=True)
        if amount <= 0: return await inter.response.send_message("Сумма должна быть положительной.", ephemeral=True)
        if user_bank < amount: return await inter.response.send_message("У вас недостаточно средств в банке.", ephemeral=True)
        fee = int(amount * BANK_FEE)
        final_amount = amount - fee
        await self.db.update_balance(inter.user.id, cash_delta=final_amount, bank_delta=-amount)
        embed = discord.Embed(title="🏦 Банковская операция", description=f"Вы сняли со счета **{final_amount:,}** 🪙.\nКомиссия составила: `{fee:,}` 🪙.", color=discord.Color.blue())
        await inter.response.send_message(embed=embed)

    @app_commands.command(name="бизнес", description="🏪 Посмотреть список доступных бизнесов.")
    async def business_list(self, inter: discord.Interaction):
        all_businesses = await self.db.get_all_businesses()
        embed = discord.Embed(title="📈 Каталог бизнесов", color=0x3498db)
        if not all_businesses:
            embed.description = "В данный момент нет доступных бизнесов. Загляните позже!"
        else:
            for business in all_businesses:
                owned_count = await self.db.count_owned_businesses(business.id)
                remaining = business.limit - owned_count
                embed.add_field(name=f"{business.name} (ID: {business.id})", value=f"**Цена:** `{business.price:,}` 🪙\n**Доход:** `{business.income:,}` 🪙\n**Осталось:** `{remaining}/{business.limit}` шт.", inline=True)
        await inter.response.send_message(embed=embed)

    @app_commands.command(name="мои_бизнесы", description="🏢 Посмотреть список ваших бизнесов.")
    async def my_businesses(self, inter: discord.Interaction):
        user_businesses = await self.db.get_user_businesses(inter.user.id)
        embed = discord.Embed(title=f"🏭 Бизнесы {inter.user.display_name}", color=0xe67e22)
        if not user_businesses:
            embed.description = "У вас пока нет ни одного бизнеса. Время это исправить!"
        else:
            total_income = sum(ub.business_info.income for ub in user_businesses)
            desc_lines = [f"• **{ub.business_info.name}** (ID: `{ub.id}`) - Доход: `{ub.business_info.income:,}` 🪙" for ub in user_businesses]
            embed.description = "\n".join(desc_lines)
            embed.set_footer(text=f"Общий доход с бизнесов: {total_income:,} 🪙")
        await inter.response.send_message(embed=embed)

    @app_commands.command(name="бизинфо", description="ℹ️ Показывает детальную информацию о вашем бизнесе.")
    @app_commands.describe(id="ID вашего бизнеса из команды /мои_бизнесы")
    async def business_info(self, inter: discord.Interaction, id: int):
        user_business = await self.db.get_user_business_by_id(id)
        if not user_business or user_business.user_id != inter.user.id:
            return await inter.response.send_message("🚫 У вас нет бизнеса с таким ID.", ephemeral=True)
        business_info = user_business.business_info
        sell_price = int(business_info.price * BUSINESS_SELL_PERCENTAGE)
        embed = discord.Embed(title=f"ℹ️ Информация о бизнесе «{business_info.name}»", color=0x3498db)
        embed.add_field(name="💵 Доход", value=f"`{business_info.income:,}` 🪙", inline=True).add_field(name="💰 Цена покупки", value=f"`{business_info.price:,}` 🪙", inline=True).add_field(name="📉 Цена продажи", value=f"`{sell_price:,}` 🪙 ({int(BUSINESS_SELL_PERCENTAGE * 100)}%)", inline=True)
        await inter.response.send_message(embed=embed)

    @app_commands.command(name="купить_бизнес", description="💰 Купить бизнес по его ID.")
    @app_commands.describe(id="ID бизнеса из команды /бизнес")
    async def buy_business(self, inter: discord.Interaction, id: int):
        business = await self.db.get_business_by_id(id)
        if not business:
            return await inter.response.send_message("🚫 Бизнес с таким ID не найден.", ephemeral=True)
        user_db = await self.db.get_user(inter.user.id)
        user_cash = user_db.cash if user_db else 0
        if user_cash < business.price:
            return await inter.response.send_message("💸 У вас недостаточно наличных для покупки.", ephemeral=True)
        owned_count = await self.db.count_owned_businesses(business.id)
        if owned_count >= business.limit:
            return await inter.response.send_message("📉 Этот тип бизнеса уже распродан.", ephemeral=True)
        await self.db.update_balance(inter.user.id, cash_delta=-business.price)
        await self.db.purchase_business(inter.user.id, business.id)
        embed = discord.Embed(title="🤝 Сделка совершена!", description=f"Поздравляем! Вы приобрели бизнес **«{business.name}»** за `{business.price:,}` 🪙.", color=discord.Color.green())
        await inter.response.send_message(embed=embed)
        log_embed = discord.Embed(title="📝 Лог: Покупка бизнеса", color=0x2ecc71)
        log_embed.add_field(name="Покупатель", value=inter.user.mention).add_field(name="Бизнес", value=business.name).add_field(name="Цена", value=f"`{business.price:,}` 🪙")
        await self.send_log(log_embed)

    @app_commands.command(name="продать_бизнес", description="📉 Продать ваш бизнес по его ID.")
    @app_commands.describe(id="ID вашего бизнеса из команды /мои_бизнесы")
    async def sell_business(self, inter: discord.Interaction, id: int):
        user_business = await self.db.get_user_business_by_id(id)
        if not user_business or user_business.user_id != inter.user.id:
            return await inter.response.send_message("🚫 У вас нет бизнеса с таким ID.", ephemeral=True)
        business_info = user_business.business_info
        sell_price = int(business_info.price * BUSINESS_SELL_PERCENTAGE)
        await self.db.sell_business(user_business.id)
        await self.db.update_balance(inter.user.id, cash_delta=sell_price)
        embed = discord.Embed(title="🤝 Бизнес продан", description=f"Вы продали **«{business_info.name}»** и получили **{sell_price:,}** 🪙.", color=0xe74c3c)
        await inter.response.send_message(embed=embed)
        log_embed = discord.Embed(title="📝 Лог: Продажа бизнеса", color=0xc27c0e)
        log_embed.add_field(name="Продавец", value=inter.user.mention).add_field(name="Бизнес", value=business_info.name).add_field(name="Выручка", value=f"`{sell_price:,}` 🪙")
        await self.send_log(log_embed)

    # ---------- Админ-команды ----------

    @app_commands.command(name="выдать_деньги", description="👑 (Админ) Выдать деньги пользователю.")
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    @app_commands.describe(пользователь="Кому выдать деньги.", сумма="Сколько денег выдать.", куда="Куда зачислить средства: на руки или в банк.")
    async def give_money(self, inter: discord.Interaction, пользователь: discord.Member, сумма: app_commands.Range[int, 1], куда: Literal['наличные', 'банк']):
        cash_delta = сумма if куда == 'наличные' else 0
        bank_delta = сумма if куда == 'банк' else 0
        await self.db.update_balance(пользователь.id, cash_delta=cash_delta, bank_delta=bank_delta)
        await inter.response.send_message(f"✅ Вы успешно выдали `{сумма:,}` 🪙 пользователю {пользователь.mention} на счет «{куда}».", ephemeral=True)
        log_embed = discord.Embed(title="📝 Лог: Админ | Выдача средств", color=0x2ecc71)
        log_embed.add_field(name="Администратор", value=inter.user.mention).add_field(name="Получатель", value=пользователь.mention).add_field(name="Сумма", value=f"`{сумма:,}` 🪙").add_field(name="Счет", value=куда.capitalize())
        await self.send_log(log_embed)

    @app_commands.command(name="отобрать_деньги", description="👑 (Админ) Отобрать деньги у пользователя.")
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    @app_commands.describe(пользователь="У кого отобрать деньги.", сумма="Сколько денег отобрать.", откуда="Откуда списать средства: с наличных или из банка.")
    async def take_money(self, inter: discord.Interaction, пользователь: discord.Member, сумма: app_commands.Range[int, 1], откуда: Literal['наличные', 'банк']):
        user_db = await self.db.get_user(пользователь.id)
        if откуда == 'наличные':
            user_cash = user_db.cash if user_db else 0
            if user_cash < сумма:
                return await inter.response.send_message(f"🚫 Недостаточно наличных у пользователя ({user_cash:,} 🪙).", ephemeral=True)
        if откуда == 'банк':
            user_bank = user_db.bank if user_db else 0
            if user_bank < сумма:
                return await inter.response.send_message(f"🚫 Недостаточно средств в банке у пользователя ({user_bank:,} 🪙).", ephemeral=True)
        cash_delta = -сумма if откуда == 'наличные' else 0
        bank_delta = -сумма if откуда == 'банк' else 0
        await self.db.update_balance(пользователь.id, cash_delta=cash_delta, bank_delta=bank_delta)
        await inter.response.send_message(f"✅ Вы успешно отобрали `{сумма:,}` 🪙 у пользователя {пользователь.mention} со счета «{откуда}».", ephemeral=True)
        log_embed = discord.Embed(title="📝 Лог: Админ | Изъятие средств", color=0xe74c3c)
        log_embed.add_field(name="Администратор", value=inter.user.mention).add_field(name="Пользователь", value=пользователь.mention).add_field(name="Сумма", value=f"`{сумма:,}` 🪙").add_field(name="Счет", value=откуда.capitalize())
        await self.send_log(log_embed)

    @app_commands.command(name="добавить_бизнес", description="👑 (Админ) Добавить новый тип бизнеса в магазин.")
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    @app_commands.describe(название="Название бизнеса (напр., 'IT-стартап')", цена="Стоимость покупки", доход="Прибыль за один сбор", количество="Сколько всего таких бизнесов может быть на сервере")
    async def add_business(self, inter: discord.Interaction, название: str, цена: int, доход: int, количество: int):
        success = await self.db.add_business(название, цена, доход, количество)
        if not success:
            return await inter.response.send_message(f"🚫 Бизнес с названием «{название}» уже существует.", ephemeral=True)
        embed = discord.Embed(title="✅ Бизнес добавлен", description=f"Новый бизнес **«{название}»** успешно добавлен в магазин.", color=discord.Color.dark_green())
        await inter.response.send_message(embed=embed, ephemeral=True)
        log_embed = discord.Embed(title="📝 Лог: Админ | Добавлен бизнес", color=0x71368a)
        log_embed.add_field(name="Администратор", value=inter.user.mention).add_field(name="Название", value=название).add_field(name="Цена", value=f"`{цена:,}` 🪙").add_field(name="Доход", value=f"`{доход:,}` 🪙").add_field(name="Лимит", value=str(количество))
        await self.send_log(log_embed)

    @app_commands.command(name="удалить_бизнес", description="👑 (Админ) Полностью удаляет тип бизнеса из магазина.")
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    @app_commands.describe(id="ID бизнеса, который нужно удалить из команды /бизнес")
    async def delete_business(self, inter: discord.Interaction, id: int):
        business = await self.db.get_business_by_id(id)
        business_name = business.name if business else f"ID: {id}"

        result = await self.db.delete_business_type(id)

        if result == 'not_found':
            return await inter.response.send_message(f"🚫 Бизнес с ID `{id}` не найден.", ephemeral=True)

        if result == 'is_owned':
            return await inter.response.send_message(
                f"🚫 Нельзя удалить этот бизнес, так как им уже владеют пользователи. Сначала они должны его продать.",
                ephemeral=True)

        if result == 'success':
            await inter.response.send_message(f"✅ Бизнес «{business_name}» был успешно удален из магазина.",
                                              ephemeral=True)

            log_embed = discord.Embed(title="📝 Лог: Админ | Бизнес удален", color=0x992d22)
            log_embed.add_field(name="Администратор", value=inter.user.mention)
            log_embed.add_field(name="Удаленный бизнес", value=business_name)
            await self.send_log(log_embed)

    @commands.Cog.listener()
    async def on_app_command_error(self, inter: discord.Interaction, error):
        if isinstance(error, app_commands.CommandOnCooldown):
            delta = timedelta(seconds=error.retry_after)
            await inter.response.send_message(f"⏳ Эта команда на перезарядке. Попробуйте снова через {str(delta).split('.')[0]}.", ephemeral=True)
        elif isinstance(error, app_commands.MissingRole):
            await inter.response.send_message("⛔ У вас нет прав для использования этой команды.", ephemeral=True)
        else:
            print(error)
            if not inter.response.is_done():
                await inter.response.send_message("❌ Произошла непредвиденная ошибка.", ephemeral=True)
            else:
                await inter.followup.send("❌ Произошла непредвиденная ошибка.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Economy(bot))