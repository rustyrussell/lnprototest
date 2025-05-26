import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import necessary libraries
from flask import Flask, request, jsonify
import uuid
import time
import sqlite3
from lnprototest.dummyrunner import DummyRunner
from lnprototest.event import Msg, ExpectMsg
from lnprototest.runner import Conn
import re

# Create a mock config class to satisfy Runner's expectations
class MockConfig:
    def getoption(self, name):
        if name == "verbose":
            return False
        raise AttributeError(f"Unknown option: {name}")

# Create a Flask app
app = Flask(__name__)

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('lnprototest.db')
    c = conn.cursor()
    # Create tables
    c.execute('''
        CREATE TABLE IF NOT EXISTS nodes (
            id TEXT PRIMARY KEY,
            pubkey TEXT,
            privkey TEXT,  -- Added privkey column
            type TEXT,
            state TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS connections (
            id TEXT PRIMARY KEY,
            sourceNodeId TEXT,
            targetNodeId TEXT,
            state TEXT,
            FOREIGN KEY(sourceNodeId) REFERENCES nodes(id),
            FOREIGN KEY(targetNodeId) REFERENCES nodes(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            connectionId TEXT,
            type TEXT,
            direction TEXT,
            content TEXT,
            timestamp INTEGER,
            status TEXT,
            FOREIGN KEY(connectionId) REFERENCES connections(id)
        )
    ''')
    conn.commit()
    conn.close()

# Initialize the database
init_db()

# Initialize DummyRunner with the mock config
mock_config = MockConfig()
runner = DummyRunner(config=mock_config)

# In-memory storage for connection objects
connection_objs = {}  # {conn_id: Conn object}

# Helper functions
def is_valid_hex(s):
    if not isinstance(s, str):
        return False
    return bool(re.match(r'^[0-9a-fA-F]*$', s))

def message_fields_to_dict(fields):
    return {
        'globalfeatures': fields.get('globalfeatures', ''),
        'features': fields.get('features', '')
    }

# Health check
@app.route('/health', methods=['GET'])
def health_check():
    # Use IST timezone (UTC+5:30)
    ist_time = time.strftime('%Y-%m-%d %H:%M:%S IST', time.localtime(time.time() + 19800))
    return jsonify({
        'status': 'healthy',
        'time': ist_time,
        'message': 'API is running'
    }), 200

# Create a node
@app.route('/nodes', methods=['POST'])
def create_node():
    try:
        privkey = runner.get_node_privkey()
        node_id = str(uuid.uuid4())
        node = {
            'id': node_id,
            'pubkey': privkey,  # In DummyRunner, pubkey and privkey are the same ("01")
            'privkey': privkey,  # Store the privkey
            'type': 'dummy',
            'state': 'initialized'
        }
        conn = sqlite3.connect('lnprototest.db')
        c = conn.cursor()
        c.execute('INSERT INTO nodes (id, pubkey, privkey, type, state) VALUES (?, ?, ?, ?, ?)',
                  (node['id'], node['pubkey'], node['privkey'], node['type'], node['state']))
        conn.commit()
        conn.close()
        return jsonify(node), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# List nodes
@app.route('/nodes', methods=['GET'])
def list_nodes():
    try:
        conn = sqlite3.connect('lnprototest.db')
        c = conn.cursor()
        c.execute('SELECT * FROM nodes')
        nodes = [{'id': row[0], 'pubkey': row[1], 'privkey': row[2], 'type': row[3], 'state': row[4]} for row in c.fetchall()]
        conn.close()
        return jsonify(nodes), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Get a node
@app.route('/nodes/<node_id>', methods=['GET'])
def get_node(node_id):
    try:
        conn = sqlite3.connect('lnprototest.db')
        c = conn.cursor()
        c.execute('SELECT * FROM nodes WHERE id = ?', (node_id,))
        row = c.fetchone()
        conn.close()
        if row:
            node = {'id': row[0], 'pubkey': row[1], 'privkey': row[2], 'type': row[3], 'state': row[4]}
            return jsonify(node), 200
        return jsonify({'error': 'Node not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Delete a node
@app.route('/nodes/<node_id>', methods=['DELETE'])
def delete_node(node_id):
    try:
        conn = sqlite3.connect('lnprototest.db')
        c = conn.cursor()
        c.execute('SELECT id FROM nodes WHERE id = ?', (node_id,))
        if not c.fetchone():
            conn.close()
            return jsonify({'error': 'Node not found'}), 404
        # Delete associated connections and messages
        c.execute('SELECT id FROM connections WHERE sourceNodeId = ? OR targetNodeId = ?', (node_id, node_id))
        conn_ids = [row[0] for row in c.fetchall()]
        for conn_id in conn_ids:
            c.execute('DELETE FROM messages WHERE connectionId = ?', (conn_id,))
            if conn_id in connection_objs:
                del connection_objs[conn_id]
        c.execute('DELETE FROM connections WHERE sourceNodeId = ? OR targetNodeId = ?', (node_id, node_id))
        c.execute('DELETE FROM nodes WHERE id = ?', (node_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Node deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Create a connection
@app.route('/connections', methods=['POST'])
def create_connection():
    try:
        data = request.json
        source_id = data.get('sourceNodeId')
        target_id = data.get('targetNodeId')
        conn = sqlite3.connect('lnprototest.db')
        c = conn.cursor()
        c.execute('SELECT id, privkey FROM nodes WHERE id IN (?, ?)', (source_id, target_id))
        nodes = c.fetchall()
        if len(nodes) != 2:
            conn.close()
            return jsonify({'error': 'Invalid node IDs'}), 400
        # Get the privkey of the source node
        source_privkey = next(node[1] for node in nodes if node[0] == source_id)
        conn_id = str(uuid.uuid4())
        conn_obj = Conn(source_privkey)  # Use the privkey instead of the UUID
        runner.add_conn(conn_obj)
        connection = {
            'id': conn_id,
            'sourceNodeId': source_id,
            'targetNodeId': target_id,
            'state': 'connected'
        }
        c.execute('INSERT INTO connections (id, sourceNodeId, targetNodeId, state) VALUES (?, ?, ?, ?)',
                  (conn_id, source_id, target_id, 'connected'))
        conn.commit()
        conn.close()
        connection_objs[conn_id] = conn_obj
        return jsonify(connection), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# List connections
@app.route('/connections', methods=['GET'])
def list_connections():
    try:
        conn = sqlite3.connect('lnprototest.db')
        c = conn.cursor()
        c.execute('SELECT * FROM connections')
        connections = [
            {'id': row[0], 'sourceNodeId': row[1], 'targetNodeId': row[2], 'state': row[3]}
            for row in c.fetchall()
        ]
        conn.close()
        return jsonify(connections), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Get a connection
@app.route('/connections/<conn_id>', methods=['GET'])
def get_connection(conn_id):
    try:
        conn = sqlite3.connect('lnprototest.db')
        c = conn.cursor()
        c.execute('SELECT * FROM connections WHERE id = ?', (conn_id,))
        row = c.fetchone()
        conn.close()
        if row:
            connection = {'id': row[0], 'sourceNodeId': row[1], 'targetNodeId': row[2], 'state': row[3]}
            return jsonify(connection), 200
        return jsonify({'error': 'Connection not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Delete a connection
@app.route('/connections/<conn_id>', methods=['DELETE'])
def delete_connection(conn_id):
    try:
        conn = sqlite3.connect('lnprototest.db')
        c = conn.cursor()
        c.execute('SELECT id FROM connections WHERE id = ?', (conn_id,))
        if not c.fetchone():
            conn.close()
            return jsonify({'error': 'Connection not found'}), 404
        c.execute('DELETE FROM messages WHERE connectionId = ?', (conn_id,))
        c.execute('DELETE FROM connections WHERE id = ?', (conn_id,))
        conn.commit()
        conn.close()
        if conn_id in connection_objs:
            del connection_objs[conn_id]
        return jsonify({'message': 'Connection deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Send an init message
@app.route('/send-init', methods=['POST'])
def send_init():
    try:
        data = request.json
        conn_id = data.get('connectionId')
        conn = sqlite3.connect('lnprototest.db')
        c = conn.cursor()
        c.execute('SELECT id FROM connections WHERE id = ?', (conn_id,))
        if not c.fetchone():
            conn.close()
            return jsonify({'error': 'Connection not found'}), 404
        conn.close()

        globalfeatures = data.get('globalfeatures', '')
        features = data.get('features', '')
        if not is_valid_hex(globalfeatures) or not is_valid_hex(features):
            return jsonify({'error': 'globalfeatures and features must be valid hex strings'}), 400

        conn_obj = connection_objs[conn_id]
        msg_event = Msg('init', connprivkey=conn_obj.name, globalfeatures=globalfeatures, features=features)
        msg_event.action(runner)

        sent_msgs = runner.get_stash(msg_event, "Msg", [])
        if not sent_msgs:
            return jsonify({'error': 'Failed to send init message'}), 500
        sent_msg = sent_msgs[-1]
        sent_message = {
            'id': str(uuid.uuid4()),
            'connectionId': conn_id,
            'type': sent_msg[0],
            'direction': 'sent',
            'content': message_fields_to_dict(sent_msg[1]),
            'timestamp': int(time.time() * 1000),
            'status': 'delivered'
        }

        # Save sent message to database
        conn = sqlite3.connect('lnprototest.db')
        c = conn.cursor()
        c.execute('INSERT INTO messages (id, connectionId, type, direction, content, timestamp, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
                  (sent_message['id'], conn_id, sent_message['type'], sent_message['direction'],
                   str(sent_message['content']), sent_message['timestamp'], sent_message['status']))
        conn.commit()

        # Expect a response
        expect_msg = ExpectMsg('init', connprivkey=conn_obj.name)
        expect_msg.action(runner)

        received_msgs = runner.get_stash(expect_msg, "ExpectMsg", [])
        if not received_msgs:
            received_message = {
                'id': str(uuid.uuid4()),
                'connectionId': conn_id,
                'type': 'init',
                'direction': 'received',
                'content': {'globalfeatures': '', 'features': ''},
                'timestamp': int(time.time() * 1000),
                'status': 'delivered'
            }
        else:
            received_msg = received_msgs[-1]
            received_message = {
                'id': str(uuid.uuid4()),
                'connectionId': conn_id,
                'type': received_msg[0],
                'direction': 'received',
                'content': message_fields_to_dict(received_msg[1]),
                'timestamp': int(time.time() * 1000),
                'status': 'delivered'
            }

        # Save received message to database
        c.execute('INSERT INTO messages (id, connectionId, type, direction, content, timestamp, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
                  (received_message['id'], conn_id, received_message['type'], received_message['direction'],
                   str(received_message['content']), received_message['timestamp'], received_message['status']))
        conn.commit()
        conn.close()

        return jsonify(sent_message), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Get message history
@app.route('/message-flow/<conn_id>', methods=['GET'])
def get_message_flow(conn_id):
    try:
        conn = sqlite3.connect('lnprototest.db')
        c = conn.cursor()
        c.execute('SELECT id FROM connections WHERE id = ?', (conn_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return jsonify({'error': 'Connection not found'}), 404
        
        c.execute('SELECT * FROM messages WHERE connectionId = ? ORDER BY timestamp', (conn_id,))
        messages = [
            {
                'id': row[0],
                'connectionId': row[1],
                'type': row[2],
                'direction': row[3],
                'content': eval(row[4]),  # Convert string back to dict
                'timestamp': row[5],
                'status': row[6]
            }
            for row in c.fetchall()
        ]
        conn.close()
        return jsonify(messages), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Clear message history for a connection
@app.route('/message-flow/<conn_id>', methods=['DELETE'])
def clear_message_flow(conn_id):
    try:
        conn = sqlite3.connect('lnprototest.db')
        c = conn.cursor()
        c.execute('SELECT id FROM connections WHERE id = ?', (conn_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return jsonify({'error': 'Connection not found'}), 404
        
        c.execute('DELETE FROM messages WHERE connectionId = ?', (conn_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Message history cleared'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)