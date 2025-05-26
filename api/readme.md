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

### 1. Check API Health
```bash
curl http://localhost:5000/health
```

### 2. Create Nodes
- **First Node**:
  ```bash
  curl -X POST http://localhost:5000/nodes -H "Content-Type: application/json"
  ```
- **Second Node**:
  ```bash
  curl -X POST http://localhost:5000/nodes -H "Content-Type: application/json"
  ```

### 3. Create a Connection
```bash
curl -X POST http://localhost:5000/connections -H "Content-Type: application/json" -d '{"sourceNodeId": "node-uuid-1", "targetNodeId": "node-uuid-2"}'
```

### 4. Send an Init Message
```bash
curl -X POST http://localhost:5000/send-init -H "Content-Type: application/json" -d '{"connectionId": "conn-uuid", "globalfeatures": "00", "features": "01"}'
```

### 5. Retrieve Message History
```bash
curl http://localhost:5000/message-flow/conn-uuid
```

### 6. Clear Message History
```bash
curl -X DELETE http://localhost:5000/message-flow/conn-uuid
```