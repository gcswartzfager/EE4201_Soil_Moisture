import requests
import base64
import json

api_key = 'sR5sb865py7fwzwjBNKq8HxXwJi9jqxAIVX9vH6aSXcmYQv85M'
url = "https://plant.id/api/v3/health_assessment"

with open("test_plant.jpg", "rb") as image_file:
    image_data = image_file.read()
    encoded_img = base64.b64encode(image_data).decode('utf-8')


headers = {
    "Api-Key": api_key,
    "Content-Type": "application/json"
}

data = {
    "images": [encoded_img]  # Send as a list of images
}

response = requests.post(url, headers=headers, json=data)
response_data = response.json()
disease_suggestions = response_data['result']['disease']['suggestions']
most_likely = disease_suggestions[0]
print(f"Most likely disease: {most_likely['name']}")
print(f"Probability: {most_likely['probability']}")
#print(response.json())
