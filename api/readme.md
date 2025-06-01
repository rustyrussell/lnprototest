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

<<<<<<< HEAD
The frontend polls this endpoint every 2 seconds to keep the UI in sync with backend events.
=======
### 6. Clear Message History
```bash
curl -X DELETE http://localhost:5000/message-flow/conn-uuid
```

## API Endpoints
- GET /health: Check API status
- POST /nodes: Create a new node
- GET /nodes: List all nodes
- GET /nodes/<node_id>: Get a specific node
- DELETE /nodes/<node_id>: Delete a node
- POST /connections: Create a connection
- GET /connections: List all connections
- GET /connections/<conn_id>: Get a specific connection
- DELETE /connections/<conn_id>: Delete a connection
- POST /send-init: Send an init message
- GET /message-flow/<conn_id>: Get message history for a connection
- DELETE /message-flow/<conn_id>: Clear message history for a connection
>>>>>>> f111e839b202716ecbfc188b983929c4ea37b7e4
