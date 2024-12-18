const express = require('express');
const net = require('net');
const cors = require('cors');
const bodyParser = require('body-parser');

const app = express();
const PORT = 3000;

// Middleware
app.use(cors());
app.use(bodyParser.json());

// TCP Socket Client Function
function sendTCPRequest(requestData) {
    return new Promise((resolve, reject) => {
        const client = new net.Socket();
        client.connect(65432, '127.0.0.1', () => {
            // Send request
            client.write(JSON.stringify(requestData));
        });

        // Collect response data
        let responseData = '';
        client.on('data', (chunk) => {
            responseData += chunk.toString();
        });

        // Close connection and resolve
        client.on('close', () => {
            try {
                const parsedResponse = JSON.parse(responseData);
                resolve(parsedResponse);
            } catch (error) {
                reject(error);
            }
        });

        // Handle errors
        client.on('error', (error) => {
            reject(error);
        });
    });
}

// Recipe Ingredients Endpoint
app.post('/get-recipe', async (req, res) => {
    try {
        const requestData = req.body;
        const response = await sendTCPRequest(requestData);
        res.json(response);
    } catch (error) {
        res.status(500).json({
            success: false,
            message: error.message
        });
    }
});

// Start server
app.listen(PORT, () => {
    console.log(`Proxy server running on port ${PORT}`);
});