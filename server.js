const express = require('express');
const app = express();

const PORT = process.env.PORT || 3000;

// Define a simple route
app.get('/', (req, res) => {
    res.send('FastClose Backend Running!');
});

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({ status: 'UP' });
});

// Start the server
app.listen(PORT, () => {
    console.log(`Server running at http://localhost:${PORT}`);
});
