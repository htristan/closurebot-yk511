import requests
import json
import time
import boto3
from shapely.geometry import Point, Polygon

# Define the coordinates of your polygon
polygon = Polygon([ (lat1, lon1), (lat2, lon2), (lat3, lon3), ..., (latN, lonN)])

# Create a DynamoDB resource object
dynamodb = boto3.resource('dynamodb')

# Specify the name of your DynamoDB table
table = dynamodb.Table('EventIDs')

def post_to_discord(event):
    # Here you can define your function to post to discord
    pass

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
            if polygon.contains(point):
                # Check if the event ID is already in the DynamoDB table
                if table.get_item(Key={'EventID': event['ID']}).get('Item') is None:
                    # If the event is within the specified area and has not been posted before, post it to Discord
                    post_to_discord(event)
                    # Add the event ID to the DynamoDB table
                    table.put_item(Item={'EventID': event['ID']})

def lambda_handler(event, context):
    check_and_post_events()
