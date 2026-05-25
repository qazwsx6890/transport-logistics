const express = require('express');
const app = express();
app.use(express.json());

app.post('/routes/build', (req, res) => {
    res.json({ route_id: "r123", distance: 42 });
});

app.listen(3000);