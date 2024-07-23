import discord
import requests
import os
import sys
import asyncio
import aiofiles
from prettytable import PrettyTable

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Your bot token
TOKEN = ''
CHANNEL_ID =   # Replace with your channel ID


async def user_activities(wallet, number, collection_id=None):
    if number == 0:
        url = f"https://api-mainnet.magiceden.dev/v3/rtp/ethereum/users/activity/v6?users={wallet}&limit=20&sortBy=eventTimestamp&includeMetadata=true"
    else:
        url = f"https://api-mainnet.magiceden.dev/v3/rtp/ethereum/collections/v7?id={collection_id}&includeMintStages=false&includeSecurityConfigs=false&normalizeRoyalties=false&useNonFlaggedFloorAsk=false&sortBy=allTimeVolume&limit=20"

    headers = {"accept": "*/*", "Authorization": "Bearer 2cbb299b-2c1c-4d81-9fb5-6eea4131b8be"}
    while True:
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                await restart_program()
            else:
                response.raise_for_status()
        except requests.exceptions.RequestException as e:
            pass

async def get_data():
    file_path = 'data.txt'
    async with aiofiles.open(file_path, 'r') as file:
        file_contents = await file.read()

    rows = file_contents.strip().split('\n')
    table = [row.split(',') for row in rows]

    for i in range(len(table)):
        data = await user_activities(table[i][0], 0)
        for activity in data.get('activities', []):
            if activity.get('type') == 'transfer' and activity.get('toAddress').lower() == table[i][0].lower():
                collection = activity.get('collection', {})
                collection_id = collection.get('collectionId')
                collection_name = collection.get('collectionName')
                if collection.get('isSpam') == False:
                    if activity.get('createdAt') > table[i][3]:
                        table[i][1] = collection_id
                        table[i][2] = collection_name
                        table[i][3] = activity.get('createdAt')
                        ROLE_ID = int(table[i][5])  # Replace with your role ID
                        collection_data = await user_activities(table[i][0], 1, collection_id)
                        for collection in collection_data['collections']:
                            if 'floorAsk' in collection and 'price' in collection['floorAsk'] and 'amount' in collection['floorAsk']['price']:
                                raw_value = collection['floorAsk']['price']['amount']['raw']
                                decimal_value = int(raw_value) / 10 ** 18  # Assuming the raw value is in wei
                                collection['floorAsk']['price']['amount']['decimal'] = decimal_value
                                table[i][4] = decimal_value

                                name = collection.get('name', 'N/A')
                                token_count = collection.get('tokenCount', 'N/A')
                                floor_ask_price = collection.get('floorAsk', {}).get('price', {}).get('amount', {}).get('decimal', 'N/A')

                                top_bid = collection.get('topBid')
                                if top_bid and top_bid.get('price') and top_bid.get('price').get('amount'):
                                    top_bid_price = top_bid.get('price').get('amount').get('decimal', 'N/A')
                                else:
                                    top_bid_price = 'N/A'

                                volume = collection.get('volume', {})
                                volume_change = collection.get('volumeChange', {})
                                floor_sale = collection.get('floorSale', {})
                                floor_sale_change = collection.get('floorSaleChange', {})
                                owner_count = collection.get('ownerCount', 'N/A')

                                message = (f"\nAddress {table[i][0]} bought {table[i][2]} \nhttps://magiceden.io/collections/ethereum/{table[i][1]}\n<@&{ROLE_ID}> ")
                                await send_message(message, name, token_count, owner_count, floor_ask_price, top_bid_price, volume, volume_change, floor_sale, floor_sale_change)

                                break
                        break
                    else:
                        break

    modified_data = []
    for i in range(len(table)):
        wallet = table[i][0]
        id = table[i][1]
        name = table[i][2]
        time = table[i][3]
        price = str(table[i][4])
        role_id=str(table[i][5])
        modified_data.append(f"{wallet},{id},{name},{time},{price},{role_id}")

    async with aiofiles.open(file_path, 'w') as file:
        for row in modified_data:
            await file.write(row + '\n')

def format_value(value):
    try:
        return f"{float(value):.2f}"
    except (ValueError, TypeError):
        return 'N/A'

async def send_message(purchase_message, name, token_count, owner_count, floor_ask_price, top_bid_price, volume, volume_change, floor_sale, floor_sale_change):
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        # Create the multi-line code block
        info_block = (
            f"```\n"
            f"Name: {name}\n"
            f"Supply: {token_count}\n"
            f"Owner: {owner_count}\n"
            f"Floor Price: {floor_ask_price}\n"
            f"Top Bid: {top_bid_price}\n"
            f"```"
        )

        # Create the table
        table = PrettyTable()
        table.field_names = ["Period", "Volume", "Volume Change", "Floor Sale", "Floor Sale Change"]
        for period in ["1day", "7day", "30day"]:
            table.add_row([
                period,
                format_value(volume.get(period, 'N/A')),
                format_value(volume_change.get(period, 'N/A')),
                format_value(floor_sale.get(period, 'N/A')),
                format_value(floor_sale_change.get(period, 'N/A'))
            ])

        # Send the message with the purchase message, info block, and the table
        await channel.send(purchase_message)
        await channel.send(info_block)
        table_message = await channel.send(f"```\n{table}\n```")
        await table_message.add_reaction("📊")  # Add an emoji reaction to the table message

async def restart_program():
    """Restarts the current program."""
    try:
        python = sys.executable
        os.execl(python, python, *sys.argv)
    except Exception as e:
        pass

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    while True:
        await get_data()
        await asyncio.sleep(0)  # Adjust the sleep duration as needed

client.run(TOKEN)
