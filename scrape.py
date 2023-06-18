import requests
import json
import time
import boto3
from shapely.geometry import Point, Polygon
from decimal import Decimal
import discord
from discord import Embed
import os
from datetime import datetime
from pytz import timezone

# Define the coordinates of your polygon
polygon = Polygon([
    (44.47984078392659, -77.30731051927751),
    (44.49551610233738, -80.62518161302752),
    (43.35612986160339, -82.07537692552752),
    (42.14608621729842, -82.53680270677752),
    (42.38998433799022, -80.97674411302752),
    (42.72985557217411, -79.52654880052752),
    (42.84273447508291, -78.86187594896501),
    (43.455899767226875, -79.17498630052751),
    (43.7542233321237, -78.71356051927752),
    (44.47984078392659, -77.30731051927751)
])


DISCORD_TOKEN = os.environ['DISCORD_TOKEN']
AWS_ACCESS_KEY_ID = os.environ['AWS_DB_KEY']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_DB_SECRET_ACCESS_KEY']
CHANNEL_ID = '1120047133802897408'

# Create a DynamoDB resource object
dynamodb = boto3.resource('dynamodb',
    region_name='us-east-1',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )

# Specify the name of your DynamoDB table
table = dynamodb.Table('ON511-ClosureDB')


# Function to convert the float values in the event data to Decimal, as DynamoDB doesn't support float type
def float_to_decimal(event):
    for key, value in event.items():
        if isinstance(value, float):
            event[key] = Decimal(str(value))
        elif isinstance(value, dict):
            event[key] = float_to_decimal(value)
    return event

def unix_to_readable(unix_timestamp):
    utc_time = datetime.utcfromtimestamp(unix_timestamp)
    eastern = timezone('US/Eastern')
    eastern_time = utc_time.replace(tzinfo=timezone('UTC')).astimezone(eastern)
    return eastern_time.strftime('%Y-%b-%d %I:%M %p')

def post_to_discord(event):
    # Create a Discord bot client
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        # Find the target channel by ID
        channel = client.get_channel(int(CHANNEL_ID))
        if channel:
            embed = Embed(title=f"ON511 Closure Update", color=discord.Color.red())
            embed.add_field(name="Road", value=event['RoadwayName'], inline=False)
            embed.add_field(name="Event Type", value=event['EventType'], inline=False)
            embed.add_field(name="Information", value=event['Description'], inline=False)
            embed.add_field(name="Start Time", value=unix_to_readable(event['StartDate']), inline=False)
            embed.add_field(name="Details", value=event['Comment'], inline=False)
            embed.add_field(name="511 Link", value="https://511on.ca/map#Closures-" + event['ID'], inline=False)
            # Send the closure notification
            await channel.send(embed=embed)
        else:
            print(f'Failed to find the Discord channel with ID: {CHANNEL_ID}')
        await client.close()

    client.run(DISCORD_TOKEN)

def check_and_post_events():
    # Perform API call to ON511 API
    response = requests.get("https://511on.ca/api/v2/get/event")

    # Parse the response
    data = json.loads(response.text)

    # Iterate over the events
    for event in data:
        # Check if the event is a full closure
        if event['IsFullClosure']:
            # Create a point from the event's coordinates
            point = Point(event['Latitude'], event['Longitude'])
            # Check if the point is within the polygon
            if polygon.contains(point) | True:
                # Check if the event ID is already in the DynamoDB table
                if table.get_item(Key={'EventID': event['ID']}).get('Item') is None:
                    # If the event is within the specified area and has not been posted before, post it to Discord
                    post_to_discord(event)
                    # Set the EventID key in the event data
                    event['EventID'] = event['ID']
                    # Convert float values in the event to Decimal
                    event = float_to_decimal(event)
                    # Add the event ID to the DynamoDB table
                    #table.put_item(Item=event)

def lambda_handler(event, context):
    check_and_post_events()

check_and_post_events()
