import RPi.GPIO as GPIO
from adafruit_seesaw.seesaw import Seesaw
from board import SCL, SDA
import requests
import base64
import json
import time
import logging
import argparse
from picamera2 import Picamera2
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient

# Plant ID API details
API_KEY = 'sR5sb865py7fwzwjBNKq8HxXwJi9jqxAIVX9vH6aSXcmYQv85M'
API_URL = "https://plant.id/api/v3/health_assessment"

# GPIO Pin Setup
GPIO.setmode(GPIO.BCM)
GPIO_PIN = 17
GPIO.setup(GPIO_PIN, GPIO.OUT)

# Capture and encode image
def capture_and_encode_image():
    picam2 = Picamera2()
    config = picam2.create_still_configuration()
    picam2.configure(config)
    picam2.start()

    try:
        filename = "captured_image.jpg"
        picam2.capture_file(filename)
        print(f"Image saved to {filename}")

        # Encode image to Base64
        with open(filename, "rb") as image_file:
            encoded_img = base64.b64encode(image_file.read()).decode('utf-8')
        print("Image successfully encoded to Base64")
        return encoded_img
    finally:
        picam2.stop()

# Send image to Plant ID API and get disease information
def assess_plant_health(encoded_img):
    headers = {
        "Api-Key": API_KEY,
        "Content-Type": "application/json"
    }
    data = {"images": [encoded_img]}
    response = requests.post(API_URL, headers=headers, json=data)
    response_data = response.json()
    suggestions = response_data['result']['disease']['suggestions']
    most_likely = suggestions[0]
    return {
        "name": most_likely['name'],
        "probability": most_likely['probability']
    }

# AWS IoT MQTT callbacks
def custom_shadow_callback_update(payload, responseStatus, token):
    if responseStatus == "timeout":
        print("Update request timed out!")
    elif responseStatus == "accepted":
        print(f"Update request accepted: {payload}")
    elif responseStatus == "rejected":
        print("Update request rejected!")

# Configure logging for AWS IoT
def configure_logging():
    logger = logging.getLogger("AWSIoTPythonSDK.core")
    logger.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

# Parse command-line arguments
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--endpoint", required=True, help="Your device data endpoint")
    parser.add_argument("-r", "--rootCA", required=True, help="Root CA file path")
    parser.add_argument("-c", "--cert", required=True, help="Certificate file path")
    parser.add_argument("-k", "--key", required=True, help="Private key file path")
    parser.add_argument("-p", "--port", type=int, default=8883, help="Port number override (default: 8883)")
    parser.add_argument("-n", "--thingName", default="PlantMonitor", help="Targeted thing name")
    parser.add_argument("-id", "--clientId", default="PlantHealthPublisher", help="Targeted client id")
    return parser.parse_args()

# Main function
def main():
    args = parse_args()
    configure_logging()

    # Initialize AWS IoT MQTT Shadow Client
    shadow_client = AWSIoTMQTTShadowClient(args.clientId)
    shadow_client.configureEndpoint(args.endpoint, args.port)
    shadow_client.configureCredentials(args.rootCA, args.key, args.cert)
    shadow_client.configureAutoReconnectBackoffTime(1, 32, 20)
    shadow_client.configureConnectDisconnectTimeout(10)
    shadow_client.configureMQTTOperationTimeout(5)
    shadow_client.connect()

    # Create device shadow handler
    device_shadow_handler = shadow_client.createShadowHandlerWithName(args.thingName, True)
    device_shadow_handler.shadowDelete(lambda *args: print("Shadow deleted"), 5)

    # Initialize Raspberry Pi's I2C interface
    i2c_bus = busio.I2C(SCL, SDA)

    # Intialize SeeSaw, Adafruit's Circuit Python library
    ss = Seesaw(i2c_bus, addr=0x36)

    while True:
        # Capture and analyze plant health
        encoded_img = capture_and_encode_image()
        disease_info = assess_plant_health(encoded_img)

        # Create MQTT payload
        payload = {
            "state": {
                "reported": {
                    "disease": disease_info["name"],
                    "probability": str(disease_info["probability"])
                }
            }
        }

        # Publish to AWS IoT
        device_shadow_handler.shadowUpdate(json.dumps(payload), custom_shadow_callback_update, 5)
        print(f"Published: {payload}")

        # read moisture level through capacitive touch pad
        moistureLevel = ss.moisture_read()

        # read temperature from the temperature sensor
        temp = ss.get_temp()

        # Display moisture and temp readings
        print("Moisture Level: {}".format(moistureLevel))
        print("Temperature: {}".format(temp))

        if moistureLevel < 300:
            GPIO.output(GPIO_PIN, GPIO.HIGH)
            print("Moisture level is low")
        else:
            GPIO.output(GPIO_PIN, GPIO.LOW)
            print("Moisture level is sufficient")
        
        # Create message payload
        payload = {"state":{"reported":{"moisture":str(moistureLevel),"temp":str(temp)}}}

        # Update shadow
        deviceShadowHandler.shadowUpdate(json.dumps(payload), customShadowCallback_Update, 5)

        # Wait before capturing the next image
        time.sleep(10)

def cleanup_gpio():
    GPIO.cleanup()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Program interrupted.")
    finally:
        cleanup_gpio()
