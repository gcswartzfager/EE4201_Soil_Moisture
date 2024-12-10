const express = require('express');
const bodyParser = require('body-parser');

const app = express();
const PORT = 3000;

// Variables to store data
let temperature = null;
let moisture = null;
let disease = null;
let probability = null;

// Middleware to parse JSON payloads
app.use(bodyParser.json());

// Endpoint to receive data from AWS IoT
app.post('/data', (req, res) => {
  const payload = req.body;

  // Check for temperature and moisture
  if ('temp' in payload && 'moisture' in payload) {
    temperature = payload.temp;
    moisture = payload.moisture;
    console.log(`Updated sensor data: Temperature=${temperature}, Moisture=${moisture}`);
  }

  // Check for disease data
  if ('disease' in payload && 'probability' in payload) {
    disease = payload.disease;
    probability = payload.probability;
    console.log(`Updated disease data: Disease=${disease}, Probability=${probability}`);
  }

  res.status(200).send('Data received and processed');
});

// Endpoint to display data
app.get('/', (req, res) => {
  res.send(`
    <h1>Plant Monitoring Data</h1>
    <h2>Sensor Data</h2>
    <p>Temperature: ${temperature !== null ? temperature : 'N/A'}</p>
    <p>Moisture: ${moisture !== null ? moisture : 'N/A'}</p>
    <h2>Disease Data</h2>
    <p>Disease Name: ${disease !== null ? disease : 'N/A'}</p>
    <p>Probability: ${probability !== null ? probability : 'N/A'}</p>
  `);
});

// Start the server
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});
