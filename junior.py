import discord
from discord import app_commands
from discord.ext import commands
import requests
import ast
import operator
import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo

token os.getenv("TOKEN")
ltc = "LNVp174T3ChPqEZr2GHRDrybPCP1rDYtxA"

bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())
ses = requests.Session()

langs = {
    "English": "en",
    "German": "de",
    "Spanish": "es",
    "French": "fr",
    "Italian": "it",
    "Turkish": "tr",
    "Arabic": "ar",
    "Dutch": "nl",
    "Polish": "pl",
    "Russian": "ru",
    "Portuguese": "pt",
    "Romanian": "ro",
    "Greek": "el",
    "Czech": "cs",
    "Swedish": "sv",
    "Danish": "da",
    "Norwegian": "no",
    "Finnish": "fi",
    "Ukrainian": "uk",
    "Chinese": "zh",
    "Japanese": "ja",
    "Korean": "ko",
    "Hindi": "hi"
}

from_choices = [
    app_commands.Choice(name="Auto Detect", value="auto")
] + [
    app_commands.Choice(name=name, value=code)
    for name, code in langs.items()
]

to_choices = [
    app_commands.Choice(name=name, value=code)
    for name, code in langs.items()
]

coins = [
    app_commands.Choice(name="Bitcoin", value="btc"),
    app_commands.Choice(name="Litecoin", value="ltc"),
    app_commands.Choice(name="Ethereum", value="eth"),
    app_commands.Choice(name="Solana", value="sol")
]

ops = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg
}

async def from_autocomplete(interaction, current):
    x = current.lower()
    return [
        c for c in from_choices
        if x in c.name.lower() or x in c.value.lower()
    ][:25]

async def to_autocomplete(interaction, current):
    x = current.lower()
    return [
        c for c in to_choices
        if x in c.name.lower() or x in c.value.lower()
    ][:25]

def calc(s):
    def run(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value

        if isinstance(n, ast.BinOp) and type(n.op) in ops:
            return ops[type(n.op)](run(n.left), run(n.right))

        if isinstance(n, ast.UnaryOp) and type(n.op) in ops:
            return ops[type(n.op)](run(n.operand))

        raise ValueError

    return run(ast.parse(s, mode="eval").body)

def detect(text):
    try:
        r = ses.get(
            "https://api.mymemory.translated.net/get",
            params={
                "q": text,
                "langpair": "autodetect|en"
            },
            timeout=8
        )

        d = r.json()
        return d.get("responseData", {}).get("detectedLanguage")

    except:
        return None

def crypto_price(coin):
    r = ses.get(
        "https://api.coingecko.com/api/v3/simple/price",
        params={
            "ids": coin,
            "vs_currencies": "eur"
        },
        timeout=8
    )

    d = r.json()
    return d[coin]["eur"]

def btc_bal(addr):
    r = ses.get(
        f"https://api.blockcypher.com/v1/btc/main/addrs/{addr}/balance",
        timeout=8
    )

    d = r.json()

    if "error" in d:
        raise Exception()

    return (
        d["balance"] / 100000000,
        d.get("unconfirmed_balance", 0) / 100000000
    )

def ltc_bal(addr):
    r = ses.get(
        f"https://api.blockcypher.com/v1/ltc/main/addrs/{addr}/balance",
        timeout=8
    )

    d = r.json()

    if "error" in d:
        raise Exception()

    return (
        d["balance"] / 100000000,
        d.get("unconfirmed_balance", 0) / 100000000
    )

def eth_bal(addr):
    r = ses.post(
        "https://cloudflare-eth.com",
        json={
            "jsonrpc": "2.0",
            "method": "eth_getBalance",
            "params": [addr, "latest"],
            "id": 1
        },
        timeout=8
    )

    d = r.json()

    if "error" in d:
        raise Exception()

    return int(d["result"], 16) / 10**18, 0

def sol_bal(addr):
    r = ses.post(
        "https://api.mainnet-beta.solana.com",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [addr]
        },
        timeout=8
    )

    d = r.json()

    if "error" in d:
        raise Exception()

    return d["result"]["value"] / 1000000000, 0

def get_tx(x):
    x = x.strip()

    if x.startswith("http"):
        m = re.search(r"/tx/([^/?#]+)", x)

        if m:
            return m.group(1)

        m = re.search(r"/transaction/([^/?#]+)", x)

        if m:
            return m.group(1)

    return x

def tx_btc(txid):
    r = ses.get(
        f"https://api.blockcypher.com/v1/btc/main/txs/{txid}",
        timeout=8
    )

    if r.status_code != 200:
        return None

    d = r.json()

    inputs = sum(
        i.get("output_value", 0)
        for i in d.get("inputs", [])
    )

    outputs = sum(
        o.get("value", 0)
        for o in d.get("outputs", [])
    )

    fee = max(inputs - outputs, 0)

    return {
        "chain": "BTC",
        "confirmations": d.get("confirmations", 0),
        "confirmed": d.get("confirmations", 0) > 0,
        "inputs": inputs / 100000000,
        "outputs": outputs / 100000000,
        "fee": fee / 100000000
    }

def tx_ltc(txid):
    r = ses.get(
        f"https://api.blockcypher.com/v1/ltc/main/txs/{txid}",
        timeout=8
    )

    if r.status_code != 200:
        return None

    d = r.json()

    inputs = sum(
        i.get("output_value", 0)
        for i in d.get("inputs", [])
    )

    outputs = sum(
        o.get("value", 0)
        for o in d.get("outputs", [])
    )

    fee = max(inputs - outputs, 0)

    return {
        "chain": "LTC",
        "confirmations": d.get("confirmations", 0),
        "confirmed": d.get("confirmations", 0) > 0,
        "inputs": inputs / 100000000,
        "outputs": outputs / 100000000,
        "fee": fee / 100000000
    }

def tx_eth(txid):
    r = ses.post(
        "https://cloudflare-eth.com",
        json={
            "jsonrpc": "2.0",
            "method": "eth_getTransactionByHash",
            "params": [txid],
            "id": 1
        },
        timeout=8
    )

    d = r.json()
    tx = d.get("result")

    if tx is None:
        return {
            "chain": "ETH",
            "confirmed": False,
            "confirmations": 0
        }

    value = int(tx["value"], 16) / 10**18

    rr = ses.post(
        "https://cloudflare-eth.com",
        json={
            "jsonrpc": "2.0",
            "method": "eth_getTransactionReceipt",
            "params": [txid],
            "id": 2
        },
        timeout=8
    )

    receipt = rr.json().get("result")

    if receipt is None:
        return {
            "chain": "ETH",
            "confirmed": False,
            "confirmations": 0,
            "amount": value
        }

    gas = int(receipt["gasUsed"], 16)
    gas_price = int(tx["gasPrice"], 16)
    fee = gas * gas_price / 10**18

    return {
        "chain": "ETH",
        "confirmed": receipt.get("status") == "0x1",
        "confirmations": 1,
        "amount": value,
        "fee": fee
    }

def tx_sol(txid):
    r = ses.post(
        "https://api.mainnet-beta.solana.com",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [
                txid,
                {
                    "encoding": "jsonParsed",
                    "maxSupportedTransactionVersion": 0
                }
            ]
        },
        timeout=8
    )

    d = r.json()
    tx = d.get("result")

    if tx is None:
        return {
            "chain": "SOL",
            "confirmed": False,
            "confirmations": 0
        }

    meta = tx.get("meta") or {}
    fee = meta.get("fee", 0) / 1000000000

    return {
        "chain": "SOL",
        "confirmed": meta.get("err") is None,
        "confirmations": 1,
        "fee": fee
    }

@bot.event
async def on_ready():
    synced = await bot.tree.sync()

    print(f"Online as {bot.user}")
    print(f"Synced {len(synced)} commands")
    print([x.name for x in synced])

@bot.tree.command(
    name="ltc",
    description="Shows the LTC address"
)
async def ltc_cmd(interaction):
    await interaction.response.send_message(
        ltc,
        ephemeral=True
    )

@bot.tree.command(
    name="time",
    description="Shows the current time"
)
async def time_cmd(interaction):
    t = datetime.now(ZoneInfo("Europe/Berlin"))

    await interaction.response.send_message(
        t.strftime("%H:%M:%S"),
        ephemeral=True
    )

@bot.tree.command(
    name="timestamp",
    description="Creates a Discord timestamp"
)
async def timestamp_cmd(interaction):
    t = int(time.time())

    await interaction.response.send_message(
        f"<t:{t}:F>\n`<t:{t}:F>`",
        ephemeral=True
    )

@bot.tree.command(
    name="calc",
    description="Calculates an expression"
)
@app_commands.describe(
    expression="Enter a calculation"
)
async def calc_cmd(interaction, expression: str):
    try:
        result = calc(expression)

        await interaction.response.send_message(
            str(result),
            ephemeral=True
        )

    except:
        await interaction.response.send_message(
            "Invalid calculation",
            ephemeral=True
        )

@bot.tree.command(
    name="translate",
    description="Translates text"
)
@app_commands.describe(
    from_language="Source language",
    to_language="Target language",
    text="Text to translate"
)
@app_commands.autocomplete(
    from_language=from_autocomplete,
    to_language=to_autocomplete
)
async def translate_cmd(
    interaction,
    from_language: str,
    to_language: str,
    text: str
):
    await interaction.response.defer(ephemeral=True)

    try:
        source = from_language

        if source == "auto":
            source = detect(text)

        if not source:
            raise Exception()

        r = ses.get(
            "https://api.mymemory.translated.net/get",
            params={
                "q": text,
                "langpair": f"{source}|{to_language}"
            },
            timeout=10
        )

        d = r.json()
        result = d.get("responseData", {}).get("translatedText")

        if not result:
            raise Exception()

        await interaction.followup.send(
            result,
            ephemeral=True
        )

    except:
        await interaction.followup.send(
            "Translation failed",
            ephemeral=True
        )

@bot.tree.command(
    name="bal",
    description="Checks a crypto address balance"
)
@app_commands.describe(
    crypto="Cryptocurrency",
    address="Crypto address"
)
@app_commands.choices(
    crypto=coins
)
async def bal_cmd(
    interaction,
    crypto: app_commands.Choice[str],
    address: str
):
    await interaction.response.defer(ephemeral=True)

    try:
        c = crypto.value

        if c == "btc":
            confirmed, pending = btc_bal(address)
            symbol = "BTC"
            price = crypto_price("bitcoin")

        elif c == "ltc":
            confirmed, pending = ltc_bal(address)
            symbol = "LTC"
            price = crypto_price("litecoin")

        elif c == "eth":
            confirmed, pending = eth_bal(address)
            symbol = "ETH"
            price = crypto_price("ethereum")

        elif c == "sol":
            confirmed, pending = sol_bal(address)
            symbol = "SOL"
            price = crypto_price("solana")

        else:
            raise Exception()

        total = confirmed + pending

        ce = confirmed * price
        pe = pending * price
        te = total * price

        status = "Receiving" if pending > 0 else "No pending incoming balance"

        msg = (
            f"**{symbol} Balance**\n"
            f"Confirmed: `{confirmed:.8f} {symbol}` (€{ce:.2f})\n"
            f"Pending: `{pending:.8f} {symbol}` (€{pe:.2f})\n"
            f"Total: `{total:.8f} {symbol}` (€{te:.2f})\n"
            f"Status: **{status}**"
        )

        await interaction.followup.send(
            msg,
            ephemeral=True
        )

    except:
        await interaction.followup.send(
            "Could not check this address",
            ephemeral=True
        )

@bot.tree.command(
    name="txid",
    description="Checks a crypto transaction"
)
@app_commands.describe(
    txid="Transaction ID or explorer link"
)
async def txid_cmd(interaction, txid: str):
    await interaction.response.defer(ephemeral=True)

    try:
        value = get_tx(txid)
        result = None

        if value.startswith("0x") and len(value) == 66:
            result = tx_eth(value)

        elif len(value) >= 80:
            result = tx_sol(value)

        elif len(value) == 64:
            result = tx_btc(value)

            if not result:
                result = tx_ltc(value)

        if not result:
            await interaction.followup.send(
                "Transaction not found",
                ephemeral=True
            )
            return

        chain = result["chain"]
        confirmations = result.get("confirmations", 0)

        status = "Confirmed" if result.get("confirmed") else "Pending"

        msg = f"**{chain} Transaction**\n"

        if "amount" in result:
            amount = result["amount"]
            fee = result.get("fee", 0)
            after = max(amount - fee, 0)

            if chain == "ETH":
                price = crypto_price("ethereum")

                av = amount * price
                fv = fee * price
                af = after * price

                msg += (
                    f"Amount: `{amount:.8f} {chain}` (€{av:.2f})\n"
                    f"Fee: `{fee:.8f} {chain}` (€{fv:.2f})\n"
                    f"After fee: `{after:.8f} {chain}` (€{af:.2f})\n"
                )
            else:
                msg += (
                    f"Amount: `{amount:.8f} {chain}`\n"
                    f"Fee: `{fee:.8f} {chain}`\n"
                    f"After fee: `{after:.8f} {chain}`\n"
                )

        elif "inputs" in result:
            inputs = result["inputs"]
            outputs = result["outputs"]
            fee = result["fee"]
            after = max(inputs - fee, 0)

            if chain == "LTC":
                price = crypto_price("litecoin")

                ie = inputs * price
                fe = fee * price
                ae = after * price
                oe = outputs * price

                msg += (
                    f"Sent: `{inputs:.8f} {chain}` (€{ie:.2f})\n"
                    f"Fee: `{fee:.8f} {chain}` (€{fe:.2f})\n"
                    f"After fee: `{after:.8f} {chain}` (€{ae:.2f})\n"
                    f"Outputs: `{outputs:.8f} {chain}` (€{oe:.2f})\n"
                )
            else:
                msg += (
                    f"Sent: `{inputs:.8f} {chain}`\n"
                    f"Fee: `{fee:.8f} {chain}`\n"
                    f"After fee: `{after:.8f} {chain}`\n"
                    f"Outputs: `{outputs:.8f} {chain}`\n"
                )

        msg += (
            f"Status: **{status}**\n"
            f"Confirmations: `{confirmations}`"
        )

        await interaction.followup.send(
            msg,
            ephemeral=True
        )

    except:
        await interaction.followup.send(
            "Could not check this transaction",
            ephemeral=True
        )

bot.run(token)