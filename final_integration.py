import gpiod  # Import the libgpiod library
from adafruit_seesaw.seesaw import Seesaw
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
from board import SCL, SDA
import requests
import base64
import json
import time
import logging
import argparse
from picamera2 import Picamera2
import busio  # Import busio for I2C communication
from threading import Lock

# Lock to manage resource access
resource_lock = Lock()

# Plant ID API details
API_KEY = 'sR5sb865py7fwzwjBNKq8HxXwJi9jqxAIVX9vH6aSXcmYQv85M'
API_URL = "https://plant.id/api/v3/health_assessment"

# GPIO Setup
GPIO_CHIP = "gpiochip4"  # Path to GPIO chip
GPIO_LINE = 17               # GPIO line number (corresponds to GPIO17 on BCM)

# Initialize GPIO
chip = gpiod.Chip(GPIO_CHIP)
line = chip.get_line(GPIO_LINE)
line.request(consumer="PlantMonitor", type=gpiod.LINE_REQ_DIR_OUT)

# Capture and encode image
def capture_and_encode_image(picam2):
    try:
        filename = "captured_image.jpg"
        picam2.capture_file(filename)
        print(f"Image saved to {filename}")

        # Encode image to Base64
        with open(filename, "rb") as image_file:
            encoded_img = base64.b64encode(image_file.read()).decode('utf-8')
        print("Image successfully encoded to Base64")
        return encoded_img
    except Exception as e:
        print(f"Error capturing image: {e}")
        return None

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

# Read moisture and temperature
def read_moisture_and_temperature(ss):
    with resource_lock:  # Ensure exclusive access
        moisture = ss.moisture_read()
        temp = ss.get_temp()
    return moisture, temp

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

    # Initialize SeeSaw, Adafruit's Circuit Python library
    ss = Seesaw(i2c_bus, addr=0x36)

    # Initialize the camera once
    picam2 = Picamera2()
    config = picam2.create_still_configuration()
    picam2.configure(config)
    picam2.start()

    try:
        while True:
            # Lock the resource to avoid conflicts
            with resource_lock:
                # Capture and analyze plant health
                encoded_img = capture_and_encode_image(picam2)
                if encoded_img:
                    disease_info = assess_plant_health(encoded_img)

                    # Create MQTT payload for plant health
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
                    print(f"Published plant health: {payload}")

            # Read moisture level and temperature
            moisture, temp = read_moisture_and_temperature(ss)
            print("Moisture Level: {}".format(moisture))
            print("Temperature: {}".format(temp))

            # If moisture level is below 300, set GPIO pin HIGH
            if moisture < 400:
                line.set_value(1)  # Set GPIO high
                print("Moisture level is low, GPIO pin set HIGH")
                time.sleep(3)
                line.set_value(0)
            else:
                line.set_value(0)  # Set GPIO low
                print("Moisture level is sufficient, GPIO pin set LOW")

            # Create message payload for environment data
            payload = {"state": {"reported": {"moisture": str(moisture), "temp": str(temp)}}}
            device_shadow_handler.shadowUpdate(json.dumps(payload), custom_shadow_callback_update, 5)

            # Wait before next iteration
            time.sleep(10)
    finally:
        picam2.stop()
        picam2.close()

if __name__ == "__main__":
    main()
