# Run app.py

1. **Install Dependencies**:
   ```bash
   poetry install
   ```

2. **Run the API**:
   ```bash
   poetry run python api/app.py
   ```
   The API will start on `http://localhost:5000`.

# API Testing

### Check API Health
```bash
curl http://localhost:5000/health
```


### GET /messages
Returns the latest message logs for real-time frontend updates.

**Response:**
```json
{
  "messages": [
    {
      "id": "string",
      "from": "runner",
      "to": "ldk",
      "type": "init",
      "content": { ... },
      "timestamp": 1234567890
    },
    ...
  ]
}
```

### Example Usage

To fetch the latest messages for the visualizer:
```bash
curl http://localhost:5000/messages
```

### Real-Time Frontend Integration

The frontend polls this endpoint every 2 seconds to keep the UI in sync with backend events.